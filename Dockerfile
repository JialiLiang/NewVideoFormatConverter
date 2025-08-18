# Multi-stage Dockerfile for optimized Render.com deployments
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements-base.txt requirements-ai.txt requirements.txt ./

# Install base dependencies (always needed)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-base.txt

# Stage for full build (with AI)
FROM base as full
RUN pip install --no-cache-dir -r requirements-ai.txt

# Stage for fast build (no AI)
FROM base as fast
# Only base dependencies, no AI

# Final stage - choose based on build arg
FROM ${BUILD_MODE:-full} as final

# Copy application code
COPY . .

# Make build script executable
RUN chmod +x build.sh

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:10000/health || exit 1

# Start command
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--workers", "2", "--timeout", "300", "app:app"]
