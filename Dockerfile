# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .
RUN --mount=type=cache,target=/root/.cache/pip pip install .

EXPOSE 8000

CMD ["uvicorn", "fire_engine.api:app", "--host", "0.0.0.0", "--port", "8000"]
