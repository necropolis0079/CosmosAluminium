#!/bin/bash
# =============================================================================
# CV Processor Lambda Layer Builder (Docker)
# =============================================================================
# Builds the layer using Docker with Amazon Linux 2023 for Lambda compatibility.
# Run from the repo root or the lambda/cv_processor directory.
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Building CV Processor Lambda Layer ==="
echo "Using Docker with Amazon Linux 2023 (Lambda Python 3.11 runtime)"

# Build the Docker image
echo ""
echo "Step 1: Building Docker image..."
docker build -f Dockerfile.layer -t cv-processor-layer-builder .

# Run the container to extract the layer zip
echo ""
echo "Step 2: Extracting layer zip..."
docker run --rm -v "$(pwd):/output" cv-processor-layer-builder

# Verify the output
echo ""
echo "Step 3: Verifying output..."
if [ -f "cv_processor_layer.zip" ]; then
    SIZE=$(ls -lh cv_processor_layer.zip | awk '{print $5}')
    echo "SUCCESS: cv_processor_layer.zip created ($SIZE)"

    # List contents
    echo ""
    echo "Layer contents (top-level packages):"
    unzip -l cv_processor_layer.zip | grep "python/[^/]*/$" | head -20
else
    echo "ERROR: cv_processor_layer.zip not found!"
    exit 1
fi

echo ""
echo "=== Layer build complete ==="
echo "Next steps:"
echo "  1. Run 'terraform apply' to deploy the updated layer"
echo "  2. Or upload manually: aws lambda publish-layer-version ..."
