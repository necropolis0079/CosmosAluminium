# Tesseract OCR Lambda Layer

This directory contains the build configuration for a Lambda layer providing Tesseract OCR 5.3.4 with Greek and English language support.

## Prerequisites

- Docker (for building the layer)
- AWS CLI (for uploading)

## Building the Layer

### Option 1: Local Build (Docker required)

```bash
cd lambda/layers/tesseract
chmod +x build.sh
./build.sh
```

This creates `tesseract-layer.zip` containing:
- `/bin/tesseract` - Tesseract binary
- `/lib/` - Required shared libraries (Leptonica, libpng, libjpeg, etc.)
- `/share/tessdata/` - Trained data files (eng.traineddata, ell.traineddata)

### Option 2: AWS CloudShell Build

If you don't have Docker locally, use AWS CloudShell:

```bash
# In AWS CloudShell (us-east-1 or eu-north-1)
git clone https://gitlab.com/lcm-team/lcmgocloud_ca_genai_2026.git
cd lcmgocloud_ca_genai_2026/lambda/layers/tesseract

# Install Docker in CloudShell
sudo yum install -y docker
sudo service docker start

# Build and upload
./build.sh
aws s3 cp tesseract-layer.zip s3://lcmgo-cagenai-prod-lambda-artifacts-eun1/layers/
```

## Enabling the Layer

1. Build the layer and ensure `tesseract-layer.zip` exists in this directory

2. Enable in Terraform:
   ```bash
   cd infra/terraform
   terraform apply -var="enable_tesseract_layer=true"
   ```

3. Add the layer to CV processor Lambda by updating `lambda_cv_processor.tf`:
   ```hcl
   layers = [
     aws_lambda_layer_version.cv_processor.arn,
     aws_lambda_layer_version.lcmgo_package.arn,
     var.enable_tesseract_layer ? aws_lambda_layer_version.tesseract[0].arn : null,
   ]
   ```

## Lambda Environment Variables

When using Tesseract in Lambda, set these environment variables:

```hcl
environment {
  variables = {
    TESSDATA_PREFIX = "/opt/share/tessdata"
    PATH            = "/opt/bin:/var/task:/var/lang/bin:/usr/local/bin:/usr/bin:/bin"
    LD_LIBRARY_PATH = "/opt/lib:/var/lang/lib:/lib64:/usr/lib64"
  }
}
```

## Layer Contents

```
tesseract-layer.zip
├── bin/
│   └── tesseract          # Tesseract 5.3.4 binary
├── lib/
│   ├── libleptonica.so*   # Leptonica 1.84.1
│   ├── libtesseract.so*   # Tesseract shared lib
│   ├── libpng*.so*        # PNG support
│   ├── libjpeg*.so*       # JPEG support
│   ├── libtiff*.so*       # TIFF support
│   ├── libwebp*.so*       # WebP support
│   └── ...                # Other dependencies
└── share/
    └── tessdata/
        ├── eng.traineddata  # English (best quality)
        └── ell.traineddata  # Greek (best quality)
```

## Language Support

- `eng` - English
- `ell` - Greek (Modern)

For multilingual OCR, use: `tesseract input.png output -l ell+eng`

## Size

- Layer zip: ~50MB (compressed)
- Uncompressed: ~150MB (includes trained data)

Lambda layers have a 250MB unzipped limit total, so plan accordingly.

## Testing

```python
import subprocess
import os

os.environ['TESSDATA_PREFIX'] = '/opt/share/tessdata'

result = subprocess.run(
    ['/opt/bin/tesseract', 'image.png', 'stdout', '-l', 'ell+eng'],
    capture_output=True,
    text=True
)
print(result.stdout)
```

Or with pytesseract:

```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = '/opt/bin/tesseract'
text = pytesseract.image_to_string(image, lang='ell+eng')
```
