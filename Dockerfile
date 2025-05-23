FROM python:3.9-slim

WORKDIR /app

RUN apt-get update --allow-unauthenticated && apt-get install -y iputils-ping --allow-unauthenticated

COPY . .

RUN apt-get update && apt-get install -y supervisor \
    && pip install --no-cache-dir -r requirements.txt

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]