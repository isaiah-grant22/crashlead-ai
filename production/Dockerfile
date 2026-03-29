FROM python:3.11-slim

WORKDIR /app

# Install system deps for geopandas / psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libgdal-dev && \
    rm -rf /var/lib/apt/lists/*

COPY production/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "production.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
