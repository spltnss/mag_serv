FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y iputils-ping

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "start.py"]