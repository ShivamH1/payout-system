FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py migrate && python manage.py seed || true

EXPOSE 8000

CMD /bin/sh -c "celery -A config worker -l info & celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler & gunicorn config.wsgi:application --bind 0.0.0.0:8000"