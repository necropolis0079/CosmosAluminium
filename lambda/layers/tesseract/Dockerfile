# Build Tesseract OCR for AWS Lambda (Amazon Linux 2023)
FROM public.ecr.aws/lambda/python:3.11

# Install build dependencies
RUN dnf install -y \
    gcc \
    gcc-c++ \
    make \
    autoconf \
    automake \
    libtool \
    pkgconfig \
    libpng-devel \
    libjpeg-devel \
    libtiff-devel \
    zlib-devel \
    libwebp-devel \
    openjpeg2-devel \
    git \
    wget \
    && dnf clean all

# Build Leptonica (Tesseract dependency)
WORKDIR /build
RUN wget https://github.com/DanBloomberg/leptonica/releases/download/1.84.1/leptonica-1.84.1.tar.gz \
    && tar -xzf leptonica-1.84.1.tar.gz \
    && cd leptonica-1.84.1 \
    && ./configure --prefix=/opt \
    && make -j$(nproc) \
    && make install

# Build Tesseract
RUN wget https://github.com/tesseract-ocr/tesseract/archive/refs/tags/5.3.4.tar.gz \
    && tar -xzf 5.3.4.tar.gz \
    && cd tesseract-5.3.4 \
    && ./autogen.sh \
    && PKG_CONFIG_PATH=/opt/lib/pkgconfig ./configure --prefix=/opt \
    && make -j$(nproc) \
    && make install

# Download trained data for Greek and English
RUN mkdir -p /opt/share/tessdata \
    && wget -O /opt/share/tessdata/eng.traineddata https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata \
    && wget -O /opt/share/tessdata/ell.traineddata https://github.com/tesseract-ocr/tessdata_best/raw/main/ell.traineddata

# Create layer structure
RUN mkdir -p /layer/bin /layer/lib /layer/share/tessdata \
    && cp /opt/bin/tesseract /layer/bin/ \
    && cp -P /opt/lib/*.so* /layer/lib/ \
    && cp /opt/share/tessdata/*.traineddata /layer/share/tessdata/

# Copy required system libraries
RUN cp -P /usr/lib64/libpng*.so* /layer/lib/ \
    && cp -P /usr/lib64/libjpeg*.so* /layer/lib/ \
    && cp -P /usr/lib64/libtiff*.so* /layer/lib/ \
    && cp -P /usr/lib64/libwebp*.so* /layer/lib/ \
    && cp -P /usr/lib64/libopenjp2*.so* /layer/lib/ \
    && cp -P /usr/lib64/libgomp*.so* /layer/lib/ \
    && cp -P /usr/lib64/libjbig*.so* /layer/lib/ \
    && cp -P /usr/lib64/libzstd*.so* /layer/lib/ \
    && cp -P /usr/lib64/liblzma*.so* /layer/lib/ 2>/dev/null || true

CMD ["echo", "Build complete. Copy /layer contents for Lambda layer."]
