FROM python:3.11-slim

WORKDIR /opt/eta_ml

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH=/opt/eta_ml
ENV ETA_PROJECT_ROOT=/opt/eta_ml
ENV ETA_PUBLIC_BASE_URL=http://localhost:8000

EXPOSE 8000
CMD ["uvicorn", "src.serve.app:app", "--host", "0.0.0.0", "--port", "8000"]
