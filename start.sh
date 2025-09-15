#!/usr/bin/env bash

echo "Worker Initiated"

# Ensure directories exist (create a fake one if no volume is mounted)
mkdir -p /runpod-volume/logs
# Create symlink
ln -s /runpod-volume/logs /comfyui-logs

echo "Copy Runpod Test"
cp /test_input.json /comfyui/test_input.json

echo "Initializing ENV variables"

cd /comfyui/custom_nodes/comfys3
python ./create_env.py

echo "Starting ComfyUI API"
# source /runpod-volume/venv/bin/activate
# TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
# export LD_PRELOAD="${TCMALLOC}"
# export PYTHONUNBUFFERED=true
export HF_HOME="/runpod-volume/huggingface"
cd /comfyui
python main.py --port 3000 > /comfyui-logs/comfyui-serverless.log 2>&1 &
# deactivate

echo "Starting RunPod Handler"
python3 -u /rp_handler.py