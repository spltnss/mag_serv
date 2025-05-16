FROM python:3.9-slim

WORKDIR /app

RUN apt-get update --allow-unauthenticated && apt-get install -y iputils-ping --allow-unauthenticated

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "start.py"]