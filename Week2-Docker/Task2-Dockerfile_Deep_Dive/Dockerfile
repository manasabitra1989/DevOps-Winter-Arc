# Base image
FROM python:3.12-slim

# Build-time argument
ARG APP_BUILD=local

# Working directory inside the container
WORKDIR /app

# Environment variables
ENV APP_ENV=production
ENV APP_VERSION=1.0
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy dependency manifest first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# Document the application port
EXPOSE 5000

# Default command
CMD ["python", "app/app.py"]
