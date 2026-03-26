# PR-Sentry Dockerfile
# Multi-stage build for minimal image size

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Security: Run as non-root user
RUN useradd --create-home --shell /bin/bash sentry
USER sentry

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/sentry/.local

# Make sure scripts in .local are usable
ENV PATH=/home/sentry/.local/bin:$PATH

# Copy application code
COPY --chown=sentry:sentry *.py ./

# Environment variables (to be overridden at runtime)
ENV GITHUB_TOKEN=""
ENV GITHUB_REPOSITORY=""
ENV PR_NUMBER=""
ENV ANTHROPIC_API_KEY=""
ENV REVIEWER_PROVIDER="anthropic"
ENV ANTHROPIC_MODEL="claude-4-5-haiku-20251015"

# Health check: verify Python can import modules
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from reviewer import Reviewer; print('OK')" || exit 1

# Run the application
ENTRYPOINT ["python", "main.py"]
