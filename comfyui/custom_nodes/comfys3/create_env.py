import os

def main():
    env_content = f"""# S3 Configuration for ComfyS3
S3_REGION={os.getenv('COMFYS3_S3_REGION', '')}
S3_ACCESS_KEY={os.getenv('COMFYS3_S3_ACCESS_KEY', '')}
S3_SECRET_KEY={os.getenv('COMFYS3_S3_SECRET_KEY', '')}
S3_BUCKET_NAME={os.getenv('COMFYS3_S3_BUCKET_NAME', '')}
S3_ENDPOINT_URL={os.getenv('COMFYS3_S3_ENDPOINT_URL', '')}
S3_INPUT_DIR={os.getenv('COMFYS3_S3_INPUT_DIR', 'tmp/input')}
S3_OUTPUT_DIR={os.getenv('COMFYS3_S3_OUTPUT_DIR', 'tmp/output')}
"""

    with open('.env', 'w') as f:
      f.write(env_content)
    
    print("Created .env file")

if __name__ == '__main__':
    main()