# syntax=docker/dockerfile:1
FROM python:3.13-slim

# El paquete se instala en site-packages, así que de su __file__ no se deduce dónde
# están `web/` y `contract/`: FIRE_ENGINE_ROOT se lo dice.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FIRE_ENGINE_ROOT=/app

WORKDIR /app

COPY . .
RUN --mount=type=cache,target=/root/.cache/pip pip install .

EXPOSE 8000

CMD ["uvicorn", "fire_engine.api:app", "--host", "0.0.0.0", "--port", "8000"]
