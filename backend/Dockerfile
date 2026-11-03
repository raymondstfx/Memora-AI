FROM node:22-slim AS renderer
WORKDIR /renderer
COPY backend/renderer/package*.json ./
RUN npm ci --omit=dev --ignore-scripts
COPY backend/renderer/render.mjs ./

FROM python:3.13-slim AS python_dependencies
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ARG APT_MIRROR=http://deb.debian.org
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked sed -i "s|http://deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources && apt-get -o Acquire::Retries=2 -o Acquire::https::Timeout=15 -o Acquire::http::Timeout=15 update && apt-get -o Acquire::Retries=2 -o Acquire::https::Timeout=15 -o Acquire::http::Timeout=15 install -y --no-install-recommends libreoffice-impress fonts-wqy-zenhei && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=python_dependencies /usr/local /usr/local
COPY --from=renderer /usr/local/bin/node /usr/local/bin/node
COPY --from=renderer /renderer ./renderer
COPY backend/requirements.lock ./requirements.lock
RUN useradd --create-home memora && mkdir -p /data/private && chown memora:memora /data/private
COPY --chown=memora:memora backend/ ./
USER memora
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
