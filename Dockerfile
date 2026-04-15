# Burraco Bot — Production Dockerfile
# Minimal Alpine-based image for cloud deployment

FROM python:3.14-alpine

# Metadata
LABEL maintainer="Burraco Bot Contributors"
LABEL description="Burraco Card Game Bot for Telegram"
LABEL version="1.0"

# Set working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    && rm -rf /var/cache/apk/*

# Copy requirements first (for better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bot.py database.py schema.sql .env.example ./

# Health check (optional, for orchestration)
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; os.environ.get('TELEGRAM_TOKEN') or exit(1)" || exit 1

# Set Python to run in unbuffered mode (for realtime logs)
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "bot.py"]
