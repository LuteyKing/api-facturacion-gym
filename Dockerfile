# ── Imagen base ligera ────────────────────────────────────
FROM python:3.10-slim

# Evitar prompts interactivos y buffering en logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Instalar dependencias del sistema (psycopg2, lxml) ───
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev libxml2-dev libxslt1-dev && \
    rm -rf /var/lib/apt/lists/*

# ── Instalar dependencias de Python ──────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copiar el código fuente ──────────────────────────────
COPY . .

# ── Puerto expuesto ──────────────────────────────────────
EXPOSE 8000

# ── Arrancar uvicorn ─────────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
