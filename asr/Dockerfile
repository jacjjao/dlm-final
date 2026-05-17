FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    git cmake build-essential \
    python3 python3-pip \
    wget curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# Build sherpa-onnx C++ library with CUDA support
RUN git clone https://github.com/k2-fsa/sherpa-onnx && \
    cd sherpa-onnx && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release \
          -DBUILD_SHARED_LIBS=ON \
          -DSHERPA_ONNX_ENABLE_GPU=ON .. && \
    make -j$(nproc)

WORKDIR /opt/sherpa-onnx

# Download bilingual zh-en streaming model
RUN wget https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2 && \
    tar xvf sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2 && \
    rm sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2

RUN pip3 install --no-cache-dir \
    numpy \
    sherpa-onnx \
    fastapi \
    "uvicorn[standard]" \
    python-multipart

ENV LD_LIBRARY_PATH=/opt/sherpa-onnx/build/lib:$LD_LIBRARY_PATH

# Copy API server files
WORKDIR /app
COPY server.py transcribe.py ./

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
