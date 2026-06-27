# ---- stage 1: build the front-end ----
FROM node:22-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- stage 2: python runtime ----
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
# Bring in the built SPA so the API can serve it at "/".
COPY --from=frontend /fe/dist ./frontend/dist

ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn app.main:app --host ${HOST} --port ${PORT}"]
