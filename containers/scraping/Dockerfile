FROM python:3.11

# Set working directory  
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (wichtig für Playwright!)
RUN playwright install

# Copy project files from parent directories
COPY ../../ .

# Create directories for notebooks and scripts
RUN mkdir -p /app/notebooks /app/scripts

# Expose port for Jupyter notebook
EXPOSE 8888

# Default command
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--notebook-dir=/app"]