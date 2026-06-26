# 默认 python:3.11-slim；离线构建: --build-arg BASE_IMAGE=trendsight_01-backend:latest
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

WORKDIR /app

ARG BASE_IMAGE
RUN if [ "$BASE_IMAGE" = "python:3.11-slim" ]; then \
      apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
      && rm -rf /var/lib/apt/lists/*; \
    fi

COPY requirements-docker.txt .
COPY docker-wheels ./docker-wheels

# 离线复用本地 backend 镜像时，仅从预下载 wheel 安装缺失依赖
RUN if [ "$BASE_IMAGE" != "python:3.11-slim" ]; then \
      pip install --no-index --find-links=./docker-wheels \
        asyncmy minio python-multipart aiosqlite reportlab python-docx httpx \
        pymupdf rapidocr-onnxruntime opencv-python-headless onnxruntime && \
      pip install --no-index --find-links=./docker-wheels --force-reinstall bcrypt==4.0.1; \
    else \
      pip install --no-cache-dir -r requirements-docker.txt; \
    fi

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
