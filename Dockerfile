# Wushu Workbench — Hugging Face Spaces Docker SDK
# Built for: linux/amd64, Python 3.11 (mediapipe 호환)
FROM python:3.11-slim

# System packages MediaPipe + OpenCV need
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 libxext6 libxrender1 \
        libgomp1 \
        ffmpeg \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces Docker SDK requires uid 1000 user
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Python dependencies first (layer cache)
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Project files
COPY --chown=user:user . .

# Switch to non-root user
USER user

# Environment defaults
ENV WUSHU_DATA_DIR=/data
ENV WUSHU_DEFAULT_LANG=ko
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
# Allow large video uploads (500MB)
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=500

# Download MediaPipe pose model + initialize DB on container start
# (model lives in /data/models so it survives restarts on persistent storage)
COPY --chown=user:user docker/entrypoint.sh /home/user/entrypoint.sh
RUN chmod +x /home/user/entrypoint.sh

EXPOSE 8501

# Container-level health check so HF Spaces sees us as healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["/home/user/entrypoint.sh"]
