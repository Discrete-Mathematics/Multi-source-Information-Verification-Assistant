import type { StreamEvent } from "./types";

export interface StartResult {
  job_id: string;
  input_text: string;
}

export async function startVerify(payload: {
  text?: string;
  url?: string;
  file?: File;
}): Promise<StartResult> {
  let res: Response;
  if (payload.file) {
    const fd = new FormData();
    fd.append("file", payload.file);
    res = await fetch("/api/verify", { method: "POST", body: fd });
  } else {
    res = await fetch("/api/verify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: payload.text, url: payload.url }),
    });
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "请求失败");
  }
  return res.json();
}

// Stream pipeline events via SSE (GET endpoint -> EventSource).
export function streamEvents(
  jobId: string,
  onEvent: (ev: StreamEvent) => void,
  onDone: () => void,
  onError: (e: string) => void
): () => void {
  const es = new EventSource(`/api/stream/${jobId}`);
  es.onmessage = (e) => {
    try {
      const ev: StreamEvent = JSON.parse(e.data);
      onEvent(ev);
      if (ev.stage === "done") {
        es.close();
        onDone();
      } else if (ev.stage === "error") {
        es.close();
        onError(ev.message || "核验出错");
      }
    } catch {
      /* ignore malformed frame */
    }
  };
  es.onerror = () => {
    // EventSource fires onerror when the server closes the stream after the
    // final event; only surface it if we never finished.
    es.close();
  };
  return () => es.close();
}

export async function sendFeedback(payload: {
  job_id: string;
  claim_id?: string;
  verdict_correct?: boolean;
  comment?: string;
}): Promise<void> {
  await fetch("/api/feedback", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
}
