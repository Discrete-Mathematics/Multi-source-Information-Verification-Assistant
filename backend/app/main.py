"""FastAPI app: streaming verification API + static front-end.

Flow:
  POST /api/verify        -> accepts {text|url} JSON or multipart file,
                             starts a background job, returns {job_id}
  GET  /api/stream/{id}   -> Server-Sent Events stream of pipeline progress,
                             terminating with the final report
  GET  /api/report/{id}   -> final report JSON (after completion)
  GET  /api/report/{id}.md-> markdown download
  POST /api/feedback      -> user feedback hook (stored, drives future tuning)
"""
from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .inputs import text_from_url
from .pipeline import run

app = FastAPI(title="多源信息核验助手", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (single-process demo). job_id -> Job
_END = object()


class Job:
    def __init__(self) -> None:
        self.queue: "asyncio.Queue" = asyncio.Queue()
        self.report: Optional[dict] = None
        self.error: Optional[str] = None


JOBS: Dict[str, Job] = {}
FEEDBACK: list = []


async def _drive(job: Job, text: str) -> None:
    async def emit(ev: dict) -> None:
        await job.queue.put(ev)
        if ev.get("stage") == "done":
            job.report = ev.get("report")

    try:
        await run(text, emit)
    except Exception as exc:  # noqa: BLE001
        job.error = str(exc)
        await job.queue.put({"stage": "error", "message": str(exc)})
    finally:
        await job.queue.put(_END)


async def _start(text: str) -> str:
    if not settings.llm_ready:
        raise HTTPException(500, "ANTHROPIC_API_KEY 未配置,无法运行核验。")
    text = text.strip()
    if len(text) < 8:
        raise HTTPException(400, "输入文本过短。")
    job_id = uuid.uuid4().hex[:12]
    job = Job()
    JOBS[job_id] = job
    asyncio.create_task(_drive(job, text))
    return job_id


@app.post("/api/verify")
async def verify(request: Request):
    """Accept JSON {text|url} or multipart form (text/url/file)."""
    text = url = None
    src_text = ""
    ctype = request.headers.get("content-type", "")

    if ctype.startswith("multipart/form-data"):
        form = await request.form()
        text = form.get("text")
        url = form.get("url")
        file = form.get("file")
        if file is not None and hasattr(file, "read"):
            raw = await file.read()
            src_text = raw.decode("utf-8", errors="ignore")
    else:
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(400, "请求体需为 JSON 或 multipart 表单。")
        text, url = data.get("text"), data.get("url")

    if not src_text:
        if url:
            try:
                src_text = await text_from_url(url)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(400, f"无法抓取 URL:{exc}")
            if not src_text:
                raise HTTPException(400, "URL 抓取到的正文为空。")
        elif text:
            src_text = text
        else:
            raise HTTPException(400, "请提供 text、url 或 file 之一。")

    job_id = await _start(src_text)
    return {"job_id": job_id, "input_text": src_text}


@app.get("/api/stream/{job_id}")
async def stream(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job 不存在")

    async def gen():
        while True:
            ev = await job.queue.get()
            if ev is _END:
                break
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/report/{job_id}")
async def report(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job 不存在")
    if job.error:
        raise HTTPException(500, job.error)
    if job.report is None:
        return JSONResponse({"status": "pending"}, status_code=202)
    return job.report


@app.get("/api/report/{job_id}.md")
async def report_md(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.report is None:
        raise HTTPException(404, "报告尚未就绪")
    md = job.report.get("markdown", "")
    return StreamingResponse(
        iter([md]),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="report-{job_id}.md"'},
    )


class Feedback(BaseModel):
    job_id: str
    claim_id: Optional[str] = None
    verdict_correct: Optional[bool] = None
    comment: Optional[str] = None


@app.post("/api/feedback")
async def feedback(fb: Feedback):
    # Feedback loop hook: persisted in-memory for the demo; in production this
    # would feed source-weighting / prompt tuning. Kept simple but real.
    FEEDBACK.append(fb.model_dump())
    return {"ok": True, "received": len(FEEDBACK)}


@app.get("/api/health")
async def health():
    return {"ok": True, "llm_ready": settings.llm_ready, "model": settings.model}


# --- static front-end (built SPA) ------------------------------------------
_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")
