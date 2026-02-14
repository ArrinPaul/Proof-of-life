#!/bin/bash
# Deployment script for Proof of Life Authentication Backend

set -e

echo "🚀 Starting deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data keys logs models

# Generate JWT keys if they don't exist
if [ ! -f "keys/private_key.pem" ]; then
    echo "🔑 Generating JWT keys..."
    openssl genrsa -out keys/private_key.pem 2048
    openssl rsa -in keys/private_key.pem -pubout -out keys/public_key.pem
    chmod 600 keys/private_key.pem
    chmod 644 keys/public_key.pem
    echo "✅ JWT keys generated"
else
    echo "✅ JWT keys already exist"
fi

# Build Docker image
echo "🏗️  Building Docker image..."
docker-compose build

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Start containers
echo "▶️  Starting containers..."
docker-compose up -d

# Wait for health check
echo "⏳ Waiting for service to be healthy..."
sleep 10

# Check health
if docker-compose ps | grep -q "healthy"; then
    echo "✅ Deployment successful!"
    echo "🌐 Backend is running at http://localhost:8000"
    echo "📊 Health check: http://localhost:8000/health"
else
    echo "⚠️  Service started but health check pending..."
    echo "Run 'docker-compose logs' to check status"
fi

echo ""
echo "📝 Useful commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop service: docker-compose down"
echo "  Restart service: docker-compose restart"
echo "  View status: docker-compose ps"
