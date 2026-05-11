import requests

base = "http://127.0.0.1:8188"

# Get all model paths config
folder_paths = requests.get(f"{base}/folder_paths").json()

# Get all checkpoints
checkpoints = requests.get(f"{base}/models/checkpoints").json()

# Get everything via object_info (heavier but complete)
obj_info = requests.get(f"{base}/object_info").json()
# Extract checkpoint combos from e.g. CheckpointLoaderSimple
# ckpts = obj_info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]