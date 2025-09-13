import io
import os
import time
import requests
import traceback
import json
import base64
import uuid
import logging
import logging.handlers
import runpod
from runpod.serverless.utils.rp_validator import validate
from runpod.serverless.modules.rp_logger import RunPodLogger
from requests.adapters import HTTPAdapter, Retry
from schemas.input import INPUT_SCHEMA
from PIL import Image

APP_NAME = 'runpod-worker-comfyui'
BASE_URI = 'http://127.0.0.1:3000'
VOLUME_MOUNT_PATH = '' # we are using the local comfy instance (used to be /runpod-volume)
LOG_FILE = 'comfyui-worker.log'
TIMEOUT = 600
LOG_LEVEL = 'INFO'


class SnapLogHandler(logging.Handler):
    def __init__(self, app_name: str):
        super().__init__()
        self.app_name = app_name
        self.rp_logger = RunPodLogger()
        self.rp_logger.set_level(LOG_LEVEL)
        self.runpod_endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID')
        self.runpod_cpu_count = os.getenv('RUNPOD_CPU_COUNT')
        self.runpod_pod_id = os.getenv('RUNPOD_POD_ID')
        self.runpod_gpu_size = os.getenv('RUNPOD_GPU_SIZE')
        self.runpod_mem_gb = os.getenv('RUNPOD_MEM_GB')
        self.runpod_gpu_count = os.getenv('RUNPOD_GPU_COUNT')
        self.runpod_volume_id = os.getenv('RUNPOD_VOLUME_ID')
        self.runpod_pod_hostname = os.getenv('RUNPOD_POD_HOSTNAME')
        self.runpod_debug_level = os.getenv('RUNPOD_DEBUG_LEVEL')
        self.runpod_dc_id = os.getenv('RUNPOD_DC_ID')
        self.runpod_gpu_name = os.getenv('RUNPOD_GPU_NAME')
        self.log_api_endpoint = os.getenv('LOG_API_ENDPOINT')
        self.log_api_timeout = os.getenv('LOG_API_TIMEOUT', 5)
        self.log_api_timeout = int(self.log_api_timeout)
        self.log_token = os.getenv('LOG_API_TOKEN')

    def emit(self, record):
        runpod_job_id = os.getenv('RUNPOD_JOB_ID')

        try:
            # Handle string formatting and extra arguments
            if hasattr(record, 'msg') and hasattr(record, 'args'):
                if record.args:
                    if isinstance(record.args, dict):
                        message = record.msg % record.args if '%' in str(record.msg) else record.msg
                    else:
                        message = str(record.msg) % record.args if '%' in str(record.msg) else record.msg
                else:
                    message = record.msg
            else:
                message = str(record)

            # # Extract extra arguments (like job_id) if present
            # extra = record.args[len(record.msg.split('%'))-1:] if isinstance(record.args, (list, tuple)) else []
            #
            # # Append extra arguments to the message
            # if extra:
            #     message += f" (Extra: {', '.join(map(str, extra))})"

            # Only log to RunPod logger if the length of the log entry is >= 1000 characters
            if len(message) <= 1000:
                level_mapping = {
                    logging.DEBUG: self.rp_logger.debug,
                    logging.INFO: self.rp_logger.info,
                    logging.WARNING: self.rp_logger.warn,
                    logging.ERROR: self.rp_logger.error,
                    logging.CRITICAL: self.rp_logger.error
                }

                # Wrapper to invoke RunPodLogger logging
                rp_logger = level_mapping.get(record.levelno, self.rp_logger.info)

                if runpod_job_id:
                    rp_logger(message, runpod_job_id)
                else:
                    rp_logger(message)

            if self.log_api_endpoint:
                try:
                    headers = {'Authorization': f'Bearer {self.log_token}'}

                    log_payload = {
                        'app_name': self.app_name,
                        'log_asctime': self.formatter.formatTime(record),
                        'log_levelname': record.levelname,
                        'log_message': message,
                        'runpod_endpoint_id': self.runpod_endpoint_id,
                        'runpod_cpu_count': self.runpod_cpu_count,
                        'runpod_pod_id': self.runpod_pod_id,
                        'runpod_gpu_size': self.runpod_gpu_size,
                        'runpod_mem_gb': self.runpod_mem_gb,
                        'runpod_gpu_count': self.runpod_gpu_count,
                        'runpod_volume_id': self.runpod_volume_id,
                        'runpod_pod_hostname': self.runpod_pod_hostname,
                        'runpod_debug_level': self.runpod_debug_level,
                        'runpod_dc_id': self.runpod_dc_id,
                        'runpod_gpu_name': self.runpod_gpu_name,
                        'runpod_job_id': runpod_job_id
                    }

                    response = requests.post(
                        self.log_api_endpoint,
                        json=log_payload,
                        headers=headers,
                        timeout=self.log_api_timeout
                    )

                    if response.status_code != 200:
                        self.rp_logger.error(f'Failed to send log to API. Status code: {response.status_code}')
                except requests.Timeout:
                    self.rp_logger.error(f'Timeout error sending log to API (timeout={self.log_api_timeout}s)')
                except Exception as e:
                    self.rp_logger.error(f'Error sending log to API: {str(e)}')
            else:
                self.rp_logger.warn('LOG_API_ENDPOINT environment variable is not set, not logging to API')
        except Exception as e:
            # Add error handling for message formatting
            self.rp_logger.error(f'Error in log formatting: {str(e)}')

# ---------------------------------------------------------------------------- #
#                               ComfyUI Functions                              #
# ---------------------------------------------------------------------------- #

def wait_for_service(url):
    retries = 0

    while True:
        try:
            requests.get(url)
            return
        except requests.exceptions.RequestException:
            retries += 1

            # Only log every 15 retries so the logs don't get spammed
            if retries % 30 == 0:
                logging.info('Service not ready yet. Retrying...')
        except Exception as err:
            logging.error(f'Error: {err}')

        time.sleep(0.1)


def send_get_request(endpoint):
    return session.get(
        url=f'{BASE_URI}/{endpoint}',
        timeout=TIMEOUT
    )


def send_post_request(endpoint, payload):
    return session.post(
        url=f'{BASE_URI}/{endpoint}',
        json=payload,
        timeout=TIMEOUT
    )


def get_txt2img_payload(workflow, payload):
    workflow["3"]["inputs"]["seed"] = payload["seed"]
    workflow["3"]["inputs"]["steps"] = payload["steps"]
    workflow["3"]["inputs"]["cfg"] = payload["cfg_scale"]
    workflow["3"]["inputs"]["sampler_name"] = payload["sampler_name"]
    workflow["4"]["inputs"]["ckpt_name"] = payload["ckpt_name"]
    workflow["5"]["inputs"]["batch_size"] = payload["batch_size"]
    workflow["5"]["inputs"]["width"] = payload["width"]
    workflow["5"]["inputs"]["height"] = payload["height"]
    workflow["6"]["inputs"]["text"] = payload["prompt"]
    workflow["7"]["inputs"]["text"] = payload["negative_prompt"]
    return workflow


def get_workflow_payload(workflow_name, payload):
    with open(f'/workflows/{workflow_name}.json', 'r') as json_file:
        workflow = json.load(json_file)

    if workflow_name == 'txt2img':
        workflow = get_txt2img_payload(workflow, payload)

    return workflow


"""
Get the filenames of the output files
"""
def get_filenames(output):
    image_filenames = []
    text_filenames = []
    for key, value in output.items():
        if 'images' in value and isinstance(value['images'], list):
            image_filenames.extend(value['images'])  # Add all images to the list
        if 'texts' in value and isinstance(value['texts'], list):
            text_filenames.extend(value['texts'])
    return image_filenames, text_filenames  # Return the full list after looping


"""
Create a unique filename prefix for each request to avoid a race condition where
more than one request completes at the same time, which can either result in the
incorrect output being returned, or the output image not being found.
"""
def create_unique_filename_prefix(payload):
    for key, value in payload.items():
        class_type = value.get('class_type')

        if class_type == 'SaveImage':
            current_prefix = payload[key]['inputs']['filename_prefix']
            # Only replace if the filename_prefix value is a string
            if isinstance(current_prefix, str):
                payload[key]['inputs']['filename_prefix'] = str(uuid.uuid4())
        elif class_type == 'SaveText|pysssss':
            # For pysssss SaveText node, we modify the filename instead
            current_file = payload[key]['inputs']['file']
            # Only replace if the file value is a string
            if isinstance(current_file, str):
                unique_id = str(uuid.uuid4())
                # Split filename and extension
                ext = os.path.splitext(current_file)[1]
                payload[key]['inputs']['file'] = f"{unique_id}{ext}"

# ---------------------------------------------------------------------------- #
#                                RunPod Handler                                #
# ---------------------------------------------------------------------------- #
def handler(event):
    job_id = event['id']
    os.environ['RUNPOD_JOB_ID'] = job_id

    try:
        validated_input = validate(event['input'], INPUT_SCHEMA)

        if 'errors' in validated_input:
            return {
                'error': '\n'.join(validated_input['errors'])
            }

        payload = validated_input['validated_input']
        workflow_name = payload['workflow']
        callback = payload['callback']
        payload = payload['payload']

        logging.info(f'Workflow: {workflow_name}', job_id)

        if workflow_name != 'custom':
            try:
                payload = get_workflow_payload(workflow_name, payload)
            except Exception as e:
                logging.error(f'Unable to load workflow payload for: {workflow_name}', job_id)
                raise

        create_unique_filename_prefix(payload)
        logging.debug('Queuing prompt', job_id)

        queue_response = send_post_request(
            'prompt',
            {
                'prompt': payload
            }
        )

        if queue_response.status_code == 200:
            resp_json = queue_response.json()
            prompt_id = resp_json['prompt_id']
            logging.info(f'Prompt queued successfully: {prompt_id}', job_id)
            retries = 0

            while True:
                # Only log every 30 retries so the logs don't get spammed
                if retries == 0 or retries % 30 == 0:
                    logging.info(f'Getting status of prompt: {prompt_id}', job_id)

                r = send_get_request(f'history/{prompt_id}')
                resp_json = r.json()

                if r.status_code == 200 and len(resp_json):
                    break

                time.sleep(0.1)
                retries += 1

            status = resp_json[prompt_id]['status']

            if status['status_str'] == 'success' and status['completed']:
                # Job was processed successfully
                outputs = resp_json[prompt_id]['outputs']

                if len(outputs):
                    logging.info(f'Files generated successfully for prompt: {prompt_id}', job_id)
                    image_filenames, text_filenames = get_filenames(outputs)
                    images = []
                    texts = []

                    # Merge all filenames with type information for unified processing
                    all_filenames = []
                    for image_info in image_filenames:
                        all_filenames.append({'filename': image_info['filename'], 'type': 'image'})
                    for text_info in text_filenames:
                        all_filenames.append({'filename': text_info['filename'], 'type': 'text'})

                    for file_info in all_filenames:
                        filename = file_info['filename']
                        file_type = file_info['type']
                        file_path = f'{VOLUME_MOUNT_PATH}/comfyui/output/{filename}'

                        if os.path.exists(file_path):
                            if file_type == 'image':
                                # Process image file
                                with Image.open(file_path) as img:
                                    # Get the dimensions of the image
                                    width, height = img.size

                                    # Determine the quality based on the dimensions
                                    if width <= 1024 and height <= 1024:
                                        quality = 100
                                    else:
                                        quality = 95
                                    
                                    # Convert to WebP in-memory
                                    buffer = io.BytesIO()
                                    img.save(buffer, format='WEBP', quality=quality)
                                    buffer.seek(0)
                                    images.append(base64.b64encode(buffer.read()).decode('utf-8'))

                            elif file_type == 'text':
                                # Process text file
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    
                                    # Try to parse as JSON if the file extension is .json
                                    if file_path.lower().endswith('.json'):
                                        try:
                                            # Parse JSON and add as structured data
                                            json_data = json.loads(content)
                                            texts.append({
                                                'filename': filename,
                                                'content_raw': content,
                                                'content_parsed': json_data,
                                                'type': 'json'
                                            })
                                        except json.JSONDecodeError:
                                            # If JSON parsing fails, treat as plain text
                                            texts.append({
                                                'filename': filename,
                                                'content_raw': content,
                                                'type': 'text'
                                            })
                                    else:
                                        # Plain text file
                                        texts.append({
                                            'filename': filename,
                                            'content_raw': content,
                                            'type': 'text'
                                        })

                            logging.info(f'Deleting output file: {file_path}', job_id)
                            os.remove(file_path)
                        else:
                            logging.error(f'Output file {file_path} not found')

                    return {
                        'callback': callback,
                        'images': images,
                        'images_format': 'webp',
                        'texts': texts
                    }
                else:
                    raise RuntimeError(f'No output found for prompt id: {prompt_id}')
            else:
                # Job did not process successfully
                for message in status['messages']:
                    key, value = message

                    if key == 'execution_error':
                        if 'node_type' in value and 'exception_message' in value:
                            node_type = value['node_type']
                            exception_message = value['exception_message']
                            raise RuntimeError(f'{node_type}: {exception_message}')
                        else:
                            # Log to file instead of RunPod because the output tends to be too verbose
                            # and gets dropped by RunPod logging
                            error_msg = f'Job did not process successfully for prompt_id: {prompt_id}'
                            logging.error(error_msg)
                            logging.info(f'{job_id}: Response JSON: {resp_json}')
                            raise RuntimeError(error_msg)

        else:
            try:
                queue_response_content = queue_response.json()
            except Exception as e:
                queue_response_content = str(queue_response.content)

            logging.error(f'HTTP Status code: {queue_response.status_code}', job_id)
            logging.error(queue_response_content, job_id)

            return {
                'error': f'HTTP status code: {queue_response.status_code}',
                'output': queue_response_content
            }
    except Exception as e:
        logging.error(f'An exception was raised: {e}', job_id)

        return {
            'error': traceback.format_exc(),
            'refresh_worker': True
        }


def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    # Remove all existing handlers from the root logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
    log_handler = SnapLogHandler(APP_NAME)
    log_handler.setFormatter(formatter)
    root_logger.addHandler(log_handler)


if __name__ == '__main__':
    session = requests.Session()
    retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    setup_logging()
    wait_for_service(url=f'{BASE_URI}/system_stats')
    logging.info('ComfyUI API is ready')
    logging.info('Starting RunPod Serverless...')
    runpod.serverless.start(
        {
            'handler': handler
        }
    )
