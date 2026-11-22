FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54
WORKDIR /runner
COPY app/deploy/pbl-runner/requirements.txt ./requirements.txt
COPY app/requirements-lock.txt ./constraints.txt
COPY app/deploy/wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt -c constraints.txt && rm -rf /wheels
COPY app/deploy/pbl-runner/worker.py ./worker.py
CMD ["uvicorn","worker:app","--host","0.0.0.0","--port","8890","--workers","1"]
