FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    calibre \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the server
CMD ["python", "server.py"]
