FROM node:24-bookworm-slim AS build
WORKDIR /build
COPY app/package*.json ./
RUN npm ci
COPY app/ ./
RUN node integrations/openmaic/build.mjs && npm run build

FROM node:24-bookworm-slim AS api
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv && rm -rf /var/lib/apt/lists/* && python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /workspace/app
COPY app/requirements-lock.txt ./requirements-lock.txt
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY app/backend ./backend
COPY --from=build /build/integrations/openmaic/bridge.mjs ./integrations/openmaic/bridge.mjs
COPY --from=build /build/integrations/openmaic/LICENSES ./integrations/openmaic/LICENSES
COPY scripts/check_model_api.py /workspace/scripts/check_model_api.py
CMD ["uvicorn","backend.main:app","--host","0.0.0.0","--port","8765"]

FROM nginx:stable-alpine AS web
COPY --from=build /build/dist /usr/share/nginx/html
COPY app/deploy/server/nginx.conf /etc/nginx/conf.d/default.conf
