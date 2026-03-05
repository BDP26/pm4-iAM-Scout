FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /data /output

VOLUME ["/data", "/output"]

CMD ["python", "-c", "print('Transform container ready. Use docker exec to run ML scripts.')"]