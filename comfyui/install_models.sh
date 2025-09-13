cd /comfyui/models

# Install custom models

# Move models from comfy-models to comfyui/models
if [ -d "/comfy-models" ]; then
  echo "install-models: Moving models from /comfy-models to /comfyui/models..."
  
  # Copy all files from comfy-models, creating directories as needed
  find /comfy-models -type f | while read -r file; do
    # Get the relative path from the source directory
    rel_path="${file#/comfy-models/}"
    dest_file="/comfyui/models/$rel_path"
    dest_dir="$(dirname "$dest_file")"
        
    # Skip if destination is a directory (safety check)
    if [ -d "$dest_file" ]; then
      continue
    fi
    
    # Create the destination directory if it doesn't exist
    mkdir -p "$dest_dir"

    # Move the file (will overwrite if it exists)
    mv "$file" "$dest_file"
    echo "install-models: Moved $rel_path"
  done
  
  echo "install-models: Model migration completed successfully."
fi