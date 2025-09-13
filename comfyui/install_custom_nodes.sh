#!/bin/bash

echo "Fixing dependencies..."

# timm fix
pip install --force-reinstall timm==1.0.19

# fixing torch 2.9
# (1.) Uninstall current PyTorch, torchvision, torchaudio
pip uninstall torch torchvision torchaudio -y
# (2.) Clear pip cache (optional but helps avoid old wheel conflicts)
pip cache purge
# (3.) Install nightly PyTorch for CUDA 12.9
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu129

echo "Starting custom nodes installation..."

# Custom nodes installation commands go here

# Configure comfys3 (already installed via snapshot)
echo "Configuring comfys3..."
cd /comfyui/custom_nodes/comfys3
python ./create_env.py

echo "Installation complete."
