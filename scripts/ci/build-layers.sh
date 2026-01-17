#!/bin/bash
# =============================================================================
# Lambda Layer Builder for CI/CD (Linux)
# =============================================================================
# Builds Lambda layers in Linux CI environment.
# Replaces Windows PowerShell scripts for cross-platform compatibility.
# =============================================================================
set -e

echo "=== Building Lambda Layers ==="
echo "Working directory: $(pwd)"

# -----------------------------------------------------------------------------
# pg8000 Layer (PostgreSQL driver)
# -----------------------------------------------------------------------------
echo ""
echo "Building pg8000 layer..."
LAYER_DIR="lambda/db_init/pg8000_layer"
rm -rf "$LAYER_DIR"
mkdir -p "$LAYER_DIR/python"
pip install pg8000 -t "$LAYER_DIR/python" --quiet --no-cache-dir
cd "$LAYER_DIR" && zip -r ../pg8000_layer.zip python && cd - > /dev/null
rm -rf "$LAYER_DIR"
echo "pg8000 layer built: lambda/db_init/pg8000_layer.zip"

# -----------------------------------------------------------------------------
# CV Processor Layer (python-docx, pdfplumber, Pillow)
# -----------------------------------------------------------------------------
echo ""
echo "Building cv_processor layer..."
LAYER_DIR="lambda/cv_processor/layer"
rm -rf "$LAYER_DIR"
mkdir -p "$LAYER_DIR/python"
pip install python-docx pdfplumber Pillow -t "$LAYER_DIR/python" --quiet --no-cache-dir
cd "$LAYER_DIR" && zip -r ../cv_processor_layer.zip python && cd - > /dev/null
rm -rf "$LAYER_DIR"
echo "cv_processor layer built: lambda/cv_processor/cv_processor_layer.zip"

# -----------------------------------------------------------------------------
# LCMGO Package Layer (source code)
# -----------------------------------------------------------------------------
echo ""
echo "Building lcmgo_package layer..."
LAYER_DIR="lambda/cv_processor/package_layer"
rm -rf "$LAYER_DIR"
mkdir -p "$LAYER_DIR/python"
cp -r src/lcmgo_cagenai "$LAYER_DIR/python/"
cd "$LAYER_DIR" && zip -r ../lcmgo_package_layer.zip python && cd - > /dev/null
rm -rf "$LAYER_DIR"
echo "lcmgo_package layer built: lambda/cv_processor/lcmgo_package_layer.zip"

# -----------------------------------------------------------------------------
# OpenSearch Layer (opensearch-py, requests-aws4auth)
# -----------------------------------------------------------------------------
echo ""
echo "Building opensearch layer..."
LAYER_DIR="lambda/opensearch_init/opensearch_layer"
rm -rf "$LAYER_DIR"
mkdir -p "$LAYER_DIR/python"
pip install opensearch-py requests-aws4auth -t "$LAYER_DIR/python" --quiet --no-cache-dir
cd "$LAYER_DIR" && zip -r ../opensearch_layer.zip python && cd - > /dev/null
rm -rf "$LAYER_DIR"
echo "opensearch layer built: lambda/opensearch_init/opensearch_layer.zip"

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo "=== All layers built successfully ==="
echo ""
echo "Built artifacts:"
ls -lh lambda/db_init/pg8000_layer.zip 2>/dev/null || echo "  - pg8000_layer.zip: NOT FOUND"
ls -lh lambda/cv_processor/cv_processor_layer.zip 2>/dev/null || echo "  - cv_processor_layer.zip: NOT FOUND"
ls -lh lambda/cv_processor/lcmgo_package_layer.zip 2>/dev/null || echo "  - lcmgo_package_layer.zip: NOT FOUND"
ls -lh lambda/opensearch_init/opensearch_layer.zip 2>/dev/null || echo "  - opensearch_layer.zip: NOT FOUND"
