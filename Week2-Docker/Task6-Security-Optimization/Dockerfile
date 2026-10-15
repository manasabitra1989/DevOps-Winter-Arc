# syntax=docker/dockerfile:1

# Build dependencies separately so pip tooling and temporary
# dependency files do not need to be copied into the runtime image.
FROM python:3.12-slim AS build

WORKDIR /build

COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Runtime stage: contains the application and installed dependencies.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=1.0.0

RUN useradd --system --uid 10001 --no-create-home appuser

WORKDIR /app

COPY --from=build /install /usr/local
COPY --chown=appuser:appuser app/ /app/

USER 10001:10001

EXPOSE 5000

CMD ["python", "app.py"]
