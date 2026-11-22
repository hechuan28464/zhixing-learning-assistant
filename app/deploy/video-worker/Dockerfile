FROM node:24-bookworm-slim@sha256:01d566e8d94d8c619591d78652babfccd3c6992a3dffa9ed5ab39e11cf6c70e9 AS node-runtime
FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace/app
COPY app/requirements-lock.txt app/requirements-video.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt -r requirements-video.txt
COPY app/backend ./backend
COPY scripts/check_model_api.py /workspace/scripts/check_model_api.py
CMD ["python","-m","backend.video.worker","--database","/data/learning.sqlite3"]
