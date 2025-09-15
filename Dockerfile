FROM nvidia/cuda:12.9.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
  PIP_PREFER_BINARY=1 \
  PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /

# Upgrade apt packages and install required dependencies (single RUN to avoid leftover layers)
RUN apt update && \
  apt upgrade -y && \
  apt install -y \
  software-properties-common \
  python3-dev \
  python3-pip \
  python3.11 \
  python3.11-dev \
  python3.11-venv \
  fonts-dejavu-core \
  rsync \
  git \
  git-lfs \
  jq \
  moreutils \
  aria2 \
  wget \
  curl \
  libglib2.0-0 \
  libsm6 \
  libgl1 \
  libxrender1 \
  libxext6 \
  ffmpeg \
  libgoogle-perftools4 \
  libtcmalloc-minimal4 \
  procps && \
  apt-get autoremove -y && \
  rm -rf /var/lib/apt/lists/* && \
  apt-get clean -y

RUN git lfs install

# Set Python 3.11 as the default Python
RUN ln -s /usr/bin/python3.11 /usr/bin/python
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Clean up to reduce image size
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies (clear pip cache in same RUN)
COPY requirements.txt .
RUN pip install --upgrade pip && \
  pip install -r requirements.txt && \
  pip cache purge || true

# Install comfy-cli
RUN comfy --skip-prompt --workspace=/comfyui install --nvidia

# Download comfy-ui models
RUN mkdir -p /comfy-models
RUN git clone --depth=1 https://huggingface.co/franckdsf/Wan2.2-Lightning /comfy-models \
  && rm -rf /comfy-models/.git

# COPY /storage/comfy-models /comfy-models

# Add shared comfy-ui files
COPY /comfyui/ /comfyui/

# Add workflows
COPY workflows /workflows

# Install extra custom models
RUN chmod +x /comfyui/install_models.sh && \
  /comfyui/install_models.sh

# Add scripts
COPY /snapshot /snapshot
RUN chmod +x /snapshot/restore_snapshot.sh
# Restore the snapshot to install custom nodes
RUN /snapshot/restore_snapshot.sh

# Install custom nodes
RUN chmod +x /comfyui/install_custom_nodes.sh
RUN /comfyui/install_custom_nodes.sh

# Add RunPod Handler and Docker container start script
COPY start.sh rp_handler.py /

# Add validation schemas
COPY schemas /schemas

# Start the container
RUN chmod +x /start.sh
ENTRYPOINT /start.sh
