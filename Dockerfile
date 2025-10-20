FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# (Opcional) Dependências de sistema mínimas (certificados etc.)
# RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
# Em dev você pode setar FLASK_ENV=development via .env
# ENV FLASK_ENV=production
EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 --timeout 120 wsgi:app