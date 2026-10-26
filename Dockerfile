FROM node:20-slim AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
RUN useradd -m app && mkdir /data && chown app /data
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY --from=ui /ui/dist ./frontend_dist
ENV RO_FRONTEND_DIST=/app/frontend_dist RO_DB=/data/ro.db RO_ALLOWED_HOSTS=127.0.0.1,localhost
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s CMD python -c "import urllib.request as u;u.urlopen('http://127.0.0.1:8000/api/v1/health')"
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
