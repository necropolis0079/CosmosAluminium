#!/bin/bash
# Build Tesseract Lambda Layer
# Run this script from the lambda/layers/tesseract directory

set -e

LAYER_NAME="tesseract-ocr"
OUTPUT_DIR="./output"

echo "Building Tesseract Lambda layer..."

# Build the Docker image
docker build -t tesseract-lambda-layer .

# Create output directory
mkdir -p $OUTPUT_DIR

# Extract the layer contents
docker run --rm -v "$(pwd)/$OUTPUT_DIR:/output" tesseract-lambda-layer \
    sh -c "cp -r /layer/* /output/"

# Create the layer zip
cd $OUTPUT_DIR
zip -r ../tesseract-layer.zip .
cd ..

echo "Layer created: tesseract-layer.zip"
echo "Upload to AWS Lambda as a layer"

# Cleanup
rm -rf $OUTPUT_DIR

echo "Done!"
