# PowerShell Deployment script for Proof of Life Authentication Backend

Write-Host "🚀 Starting deployment..." -ForegroundColor Green

# Check if Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker is not installed. Please install Docker first." -ForegroundColor Red
    exit 1
}

# Check if docker-compose is installed
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "❌ docker-compose is not installed. Please install docker-compose first." -ForegroundColor Red
    exit 1
}

# Create necessary directories
Write-Host "📁 Creating directories..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path data, keys, logs, models | Out-Null

# Generate JWT keys if they don't exist
if (-not (Test-Path "keys/private_key.pem")) {
    Write-Host "🔑 Generating JWT keys..." -ForegroundColor Cyan
    
    # Check if OpenSSL is available
    if (Get-Command openssl -ErrorAction SilentlyContinue) {
        openssl genrsa -out keys/private_key.pem 2048
        openssl rsa -in keys/private_key.pem -pubout -out keys/public_key.pem
        Write-Host "✅ JWT keys generated" -ForegroundColor Green
    } else {
        Write-Host "⚠️  OpenSSL not found. Please generate JWT keys manually:" -ForegroundColor Yellow
        Write-Host "   openssl genrsa -out keys/private_key.pem 2048" -ForegroundColor Yellow
        Write-Host "   openssl rsa -in keys/private_key.pem -pubout -out keys/public_key.pem" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "✅ JWT keys already exist" -ForegroundColor Green
}

# Build Docker image
Write-Host "🏗️  Building Docker image..." -ForegroundColor Cyan
docker-compose build

# Stop existing containers
Write-Host "🛑 Stopping existing containers..." -ForegroundColor Cyan
docker-compose down

# Start containers
Write-Host "▶️  Starting containers..." -ForegroundColor Cyan
docker-compose up -d

# Wait for health check
Write-Host "⏳ Waiting for service to be healthy..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Check health
$status = docker-compose ps
if ($status -match "healthy") {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    Write-Host "🌐 Backend is running at http://localhost:8000" -ForegroundColor Green
    Write-Host "📊 Health check: http://localhost:8000/health" -ForegroundColor Green
} else {
    Write-Host "⚠️  Service started but health check pending..." -ForegroundColor Yellow
    Write-Host "Run 'docker-compose logs' to check status" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📝 Useful commands:" -ForegroundColor Cyan
Write-Host "  View logs: docker-compose logs -f" -ForegroundColor White
Write-Host "  Stop service: docker-compose down" -ForegroundColor White
Write-Host "  Restart service: docker-compose restart" -ForegroundColor White
Write-Host "  View status: docker-compose ps" -ForegroundColor White
