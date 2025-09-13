#!/usr/bin/env bash

# Create a new snapshot by clicking on "Save snapshot"
# Get the *_snapshot.json from your ComfyUI: ComfyUI/custom_nodes/ComfyUI-Manager/snapshots
# Get the *_snapshot.json from your ComfyUI: ComfyUI/user/default/ComfyUI-Manager/snapshots

set -e

SNAPSHOT_FILE=$(ls /snapshot/*snapshot.json 2>/dev/null | head -n 1)

if [ -z "$SNAPSHOT_FILE" ]; then
  echo "comfy-snapshot-manager: No snapshot file found. Exiting..."
  exit 0
fi

# Temporarily copy entire custom_nodes to preserve all custom files during snapshot restoration
if [ -d "/comfyui/custom_nodes" ]; then
  echo "comfy-snapshot-manager: Backing up existing custom_nodes..."
  mv /comfyui/custom_nodes /comfyui/custom_nodes_backup
  mkdir -p /comfyui/custom_nodes
  # move back comfyui-manager to have it after snapshot restore
  mv /comfyui/custom_nodes_backup/ComfyUI-Manager /comfyui/custom_nodes/ComfyUI-Manager
fi

echo "comfy-snapshot-manager: restoring snapshot: $SNAPSHOT_FILE"

comfy --workspace /comfyui node restore-snapshot "$SNAPSHOT_FILE" --pip-non-url

for file in /workflows/*.{json,png}; do
  if [ -f "$file" ]; then
    comfy node install-deps --workflow="$file"
  fi
done

comfy node update all

# Restore and merge custom_nodes content if it was backed up
if [ -d "/comfyui/custom_nodes_backup" ]; then
  echo "comfy-snapshot-manager: Merging preserved custom_nodes content..."
  
  # Copy all files from backup, creating directories as needed
  find /comfyui/custom_nodes_backup -type f | while read -r file; do
    # Get the relative path from the backup directory
    rel_path="${file#/comfyui/custom_nodes_backup/}"
    dest_file="/comfyui/custom_nodes/$rel_path"
    dest_dir="$(dirname "$dest_file")"
        
    # Skip if destination is a directory (safety check)
    if [ -d "$dest_file" ]; then
      continue
    fi
    
    # Create the destination directory if it doesn't exist
    mkdir -p "$dest_dir"

    # ls dest_dir to verify
    ls -la "$dest_dir"

    # Copy the file (will overwrite if it exists)
    cp "$file" "$dest_file"
    echo "comfy-snapshot-manager: SUCCESS: File copied"
    
    # ls dest_dir to verify
    ls -la "$dest_dir"
  done
  
  rm -rf /comfyui/custom_nodes_backup
  
  echo "comfy-snapshot-manager: Custom nodes content merged successfully."
fi

rm -rf /comfyui/custom_nodes/ComfyUI-Manager

echo "comfy-snapshot-manager: restored snapshot file: $SNAPSHOT_FILE"