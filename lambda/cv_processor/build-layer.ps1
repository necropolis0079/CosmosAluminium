# =============================================================================
# CV Processor Lambda Layer Builder (Windows + Docker)
# =============================================================================
# Builds the layer using Docker with Amazon Linux 2023 for Lambda compatibility.
# Requires Docker Desktop running on Windows.
# =============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=== Building CV Processor Lambda Layer ===" -ForegroundColor Cyan
Write-Host "Using Docker with Amazon Linux 2023 (Lambda Python 3.11 runtime)"

# Check Docker is running
Write-Host ""
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
} catch {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "Docker is running" -ForegroundColor Green

# Build the Docker image
Write-Host ""
Write-Host "Step 1: Building Docker image..." -ForegroundColor Yellow
docker build -f Dockerfile.layer -t cv-processor-layer-builder .
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed" -ForegroundColor Red
    exit 1
}

# Run the container to extract the layer zip
Write-Host ""
Write-Host "Step 2: Extracting layer zip..." -ForegroundColor Yellow
# Convert Windows path to Docker-compatible format
$OutputPath = $ScriptDir -replace '\\', '/' -replace '^([A-Z]):', '/$1'.ToLower()
docker run --rm -v "${OutputPath}:/output" cv-processor-layer-builder
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker run failed" -ForegroundColor Red
    exit 1
}

# Verify the output
Write-Host ""
Write-Host "Step 3: Verifying output..." -ForegroundColor Yellow
$ZipPath = Join-Path $ScriptDir "cv_processor_layer.zip"
if (Test-Path $ZipPath) {
    $Size = (Get-Item $ZipPath).Length / 1MB
    Write-Host "SUCCESS: cv_processor_layer.zip created ($([math]::Round($Size, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "ERROR: cv_processor_layer.zip not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Layer build complete ===" -ForegroundColor Cyan
Write-Host "Next steps:"
Write-Host "  1. Run 'terraform apply' to deploy the updated layer"
