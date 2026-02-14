FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (glib for mediapipe)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Start command - use shell form for $PORT expansion
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
