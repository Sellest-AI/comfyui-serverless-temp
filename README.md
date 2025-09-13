# What is this repository

⚠️ **COMFY S3 REQUIRES ENV VARIABLSE TO WORK**

```sh
COMFYS3_S3_REGION="required"
COMFYS3_S3_ACCESS_KEY="required"
COMFYS3_S3_SECRET_KEY="required"
COMFYS3_S3_BUCKET_NAME="required"
COMFYS3_S3_ENDPOINT_URL="required"
COMFYS3_S3_INPUT_DIR="optional"
COMFYS3_S3_OUTPUT_DIR="optional"
```
---

This repository aims to provide a wrapper for comfy ui serverless. 
At this date it uses ``rp_handler`` from **Runpod**. To run a serverless docker.

# How is it structured

> 🖼️ **comfyui**: comfyui files to be copied on docker creation

> 📖 **docs**: Documentation files from the forked repository

> ⛓️ **schemas**: The schemas (similar to zod) to parse the API data

> 🛟 **snapshot**: The ``*snapshot.json`` file that contains the ``custom_nodes`` from comfyui that will be installed (with their dependencies) on docker creation

> 🧪 **tests**: Some tests files if you want to run tests

> 🎊 **workflows**: Pre-built workflows JSON so we don't have to send the whole custom JSON workflow to the API. 

> **Root**: the root folder contains all the important things.

# Focus on specific elements

## 🧪 Tests

This folder contains a ``test_input.json`` file that will be triggered by the ``rp_handler`` to test the docker locally if built locally. This helps ensuring that the docker works properly. This file contains the API input to run the tests.

## 🛟 Snapshot

When running a workflow in comfyui, you will sometimes need ``custom_nodes``. Those nodes are not installed by default. If you want to run a custom workflow with specific nodes, this docker needs to install them first. To do so :

1. Go to comfyUI
2. Open the comfy manager
3. Create a new snapshot
4. Go to ``custom_nodes > comfyui-manager > snapshots`` to retrieve your snapshot
5. rename your snapshot with ``<SOMETHING>_snapshot.json``, it will automatically be picked by the docker on built

☣️ ComfyUI-Manager will be automatically deleted on docker creation to speed up the boot time.

☣️ Be careful not to import too many nodes that might be long to be started.

## 🎊 Workflows

This folder contains all the workflows in JSON API format to run on comfy. It will then be picked by ``rp_handler.py`` and will automatically replace the input data.

```py
# API input
api_input = { input: { workflow: 'txt2img', payload: {seed: 123 } } }
data = api_input.get('input')

def get_workflow_payload(workflow_name, payload):
    with open(f'/workflows/{workflow_name}.json', 'r') as json_file:
        workflow = json.load(json_file)

    if workflow_name == 'txt2img':
        workflow = get_txt2img_payload(workflow, payload)

    return workflow

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


# Will retrieve the 'txt2img' workflow
workflow = get_workflow_payload(data.get('workflow'), data.get('payload'))
```

☣️ When you add a new workflow in the ``workflows`` folder, you must add its corresponding ``functions``.

❔ In the future we might want to extract each workflow in their specific ``.py`` and load them in the ``rp_handler.py`` instead of having all the workflows functions in the ``rp_handler.py`` itself.

## ⌨️ start.sh

This file starts the comfy UI and starts the ``rp_handler`` (runpod API handler).

# Digging into the Dockerfile 🐋

This docker file is pretty straightforward.
1. It first download a ``nvidia/cuda`` image to be able to run the docker with ``GPUs``.
2. It installs the necessary dependencies that are most likely to be used.
3. It copies the requirements file to install python dependencies that are used by this docker.
4. It installs ``comfyui`` with the ``comfy-cli`` to the following directory: ``/comfyui``.
5. ☣️ MIGHT BREAK: It downloads comfy models from a custom ``hugging-face`` repository into a ``/comfy-models`` directory. ``extra_model_paths.yml`` will then link this folder to the comfy instance to read the models from this external folder (``/comfy-models``). That's where/when you should download custom models.
6. It copies the snapshot and install the ``custom_nodes`` python dependencies.
7. Adds other missing files.
8. start the ``start.sh`` script.

# Local limitation

Since this docker is aimed to be used by a runpod worker with a ``runpod-volume`` attached to it there are some limitations to be known.

1. To explore the docker files while running you need to uncomment a line in ``start.sh`` to copy the ``test_input.json`` and force the API to run a fake request. Please refer to the section *Local build tips* bellow.

2. To run this docker locally you need ``docker compose``. The ``docker-compose.yml`` contains all the requirements to run this docker.

3. Since this docker is aimed to work with a ``runpod-volume``, make sure to have a fake one in ``.storage/runpod-volume`` in this folder. Check the ``docker-compose.yml`` for more information.

### Runpod-volume

The ``runpod-volume`` is a volume that will be attached to the docker locally. On runpod, this volume contains ``ComfyUI`` (optional) (the whole ComfyUI instance), ``huggingface`` (some cached models from huggingface) and a ``logs`` folder that contains logs from different services linked to it.

☣️ To run this docker locally you will need the same structure. Create the necessary folders.

❔(optional) for ``ComfyUI`` use the following command to download the ``comfyui`` folder from inside the docker. Then move the downloaded folder to ``ComfyUI``.
```sh
docker cp <CONTAINER_ID>:/comfyui ./storage/runpod-volume/tmp-comfyui
```
The ``ComfyUI`` network folder acts as a fallback if models are not found locally, but this can decrease performance, so keep that in mind and try to upload the files to the docker instead.

### Local build tips

When building the runpod locally, you should uncomment the following lines in the ``start.sh`` script to trigger a test on built. This will allow you to browse the docker while it's processing, ensuring all the files are correct etc.

```bash
echo "Copy Runpod Test"
cp /test_input.json /comfyui/test_input.json
```

# Global limitation

ComfyUI requires high demand models to be installed to run efficiently. Linking a network volume to the container is not enough to ensure high speed performance. The same applies with ``custom_nodes``. To overcome those limitations, you should download ``models`` and ``custom_nodes`` to the docker when building it. This will ensure that everything will be available on START with high speed performance.

Check the section *Digging into the Dockerfile* to better understand when and where to download the files.

