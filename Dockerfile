FROM python:3.10.13-slim-bullseye

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y torch tensorflow transformers triton && \
    rm -rf /usr/local/lib/python3.10/site-packages/nvidia*

# Copy application code
COPY ./web/dist ./web/dist
COPY ./free_one_api ./free_one_api
COPY main.py .

# Create data directory
RUN mkdir -p ./data

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Run application
CMD ["python", "main.py"]