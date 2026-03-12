FROM python:3.11-bookworm

WORKDIR /workspace

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Requirements zuerst kopieren für besseres Caching
COPY requirements.txt /workspace/requirements.txt

# Basis-Systempakete + Python-Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /workspace/requirements.txt

# Playwright Browser + nötige Linux-Dependencies
RUN python -m playwright install --with-deps chromium

# Projektdateien kopieren
COPY . /workspace
