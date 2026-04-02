FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy transformation scripts
COPY *.py ./

RUN mkdir -p /data /output

VOLUME ["/data", "/output"]

# Run the transformation pipeline
CMD ["python", "main.py"]