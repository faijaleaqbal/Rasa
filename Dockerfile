FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TF_ENABLE_ONEDNN_OPTS=0 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    PORT=7860

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    tesseract-ocr \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (Required for Hugging Face Spaces)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH="/home/user/app"

WORKDIR /home/user/app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files with proper ownership
COPY --chown=user:user . /home/user/app

# Setup storage directories and permissions
RUN mkdir -p storage/files storage/auth storage/notes /tmp/alya_image_tools_storage && \
    chown -R user:user /home/user/app /tmp/alya_image_tools_storage && \
    chmod +x start.sh

USER user

EXPOSE 7860 5055

CMD ["./start.sh"]
