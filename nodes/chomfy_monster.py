import os
import folder_paths
import random
import json
import time
import platform
import torch
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

# --- HELPER FUNCTIONS ---

def get_wildcard_files(wildcard_dir):
    files = []
    if not os.path.exists(wildcard_dir):
        os.makedirs(wildcard_dir, exist_ok=True)
    for f in os.listdir(wildcard_dir):
        if f.endswith(".txt") or f.endswith(".csv"):
            files.append(f)
    return files if files else ["none.txt"]

def load_lines(file_path):
    if not os.path.exists(file_path):
        return [""]
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        return lines
    except Exception as e:
        print(f"Error loading wildcard: {e}")
        return [""]

# --- NODE 1: THE MONSTER PROMPT BUILDER ---

class ChomfyMegaPrompt:
    def __init__(self):
        # Go up two levels: /nodes/ -> /ComfyUI-ChomfyNodes/ -> /wildcards/
        base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.base_dir = os.path.join(base_path, "wildcards")

    @classmethod
    def INPUT_TYPES(s):
        # Dynamic Input Generation
        base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        wildcard_path = os.path.join(base_path, "wildcards")
        
        file_list = get_wildcard_files(wildcard_path)
        
        inputs = {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }
        # Generate 24 Slots
        for i in range(1, 25):
            slot = f"{i:02}"
            inputs["required"][f"on_{slot}"] = ("BOOLEAN", {"default": True, "label_on": "ON", "label_off": "OFF"})
            inputs["required"][f"file_{slot}"] = (file_list,)
            inputs["required"][f"mode_{slot}"] = (["Random", "Fixed", "Sequential Forward", "Sequential Reverse"],)
            inputs["required"][f"index_{slot}"] = ("INT", {"default": 0, "min": 0, "max": 10000})
            inputs["required"][f"join_{slot}"] = ("STRING", {"default": ", ", "multiline": False})

        return inputs

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("final_prompt",)
    FUNCTION = "build_prompt"
    CATEGORY = "ChomfyNodes"

    def build_prompt(self, seed, **kwargs):
        final_parts = []
        rng = random.Random(seed)

        for i in range(1, 25):
            slot = f"{i:02}"
            
            is_on = kwargs.get(f"on_{slot}", True)
            if not is_on:
                continue

            filename = kwargs.get(f"file_{slot}", "none.txt")
            if filename == "none.txt":
                continue

            full_path = os.path.join(self.base_dir, filename)
            lines = load_lines(full_path)
            total_lines = len(lines)

            if total_lines == 0:
                continue

            mode = kwargs.get(f"mode_{slot}", "Random")
            idx_input = kwargs.get(f"index_{slot}", 0)
            delimiter = kwargs.get(f"join_{slot}", ", ")

            selected_text = ""

            # Selection Logic
            if mode == "Fixed":
                safe_idx = max(0, min(idx_input, total_lines - 1))
                selected_text = lines[safe_idx]
            
            elif mode == "Random":
                slot_seed = seed + i * 100
                slot_rng = random.Random(slot_seed)
                selected_text = slot_rng.choice(lines)
                
            elif mode == "Sequential Forward":
                curr_idx = (idx_input + seed) % total_lines
                selected_text = lines[curr_idx]

            elif mode == "Sequential Reverse":
                curr_idx = (idx_input - seed) % total_lines
                selected_text = lines[curr_idx]

            if i == 1:
                final_parts.append(selected_text)
            else:
                if len(final_parts) > 0:
                    final_parts.append(delimiter) 
                final_parts.append(selected_text)

        final_string = "".join(final_parts)
        return (final_string,)


# --- NODE 2: THE FORENSIC LOGGER SAVER ---

class ChomfyDetailedLogger:
    def __init__(self):
        self.type = "output"
        self.prefix_append = "Chomfy_Forensics"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename_prefix": ("STRING", {"default": "Chomfy_Log"}),
            },
            "optional": {
                "model_opt": ("MODEL",),
                "vae_opt": ("VAE",),
                "latent_opt": ("LATENT",),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images_forensic"
    OUTPUT_NODE = True
    CATEGORY = "ChomfyNodes"

    def save_images_forensic(self, images, filename_prefix="Chomfy_Log", model_opt=None, vae_opt=None, latent_opt=None, prompt=None, extra_pnginfo=None):
        results = list()
        
        # 1. Gather Hardware/System Info
        sys_info = {
            "os": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "torch_version": torch.__version__,
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 2. Gather Workflow Info
        workflow_stats = {
            "nodes_count": len(prompt) if prompt else 0,
            "loras_detected": [],
            "checkpoints_detected": [],
            "sampler_config": "Check Workflow Graph"
        }

        if prompt:
            for key, valid_node in prompt.items():
                class_type = valid_node.get('class_type', '')
                inputs = valid_node.get('inputs', {})
                if 'CheckpointLoader' in class_type:
                    workflow_stats["checkpoints_detected"].append(inputs.get('ckpt_name', 'unknown'))
                if 'LoraLoader' in class_type:
                    workflow_stats["loras_detected"].append(inputs.get('lora_name', 'unknown'))

        # 3. Gather Execution Info
        exec_info = {}
        if latent_opt and "samples" in latent_opt:
            exec_info["latent_dims"] = list(latent_opt["samples"].shape)
        
        # FIX: Go up two levels so 'outputs' is in the ROOT of the node pack, not inside 'nodes'
        base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        custom_out_path = os.path.join(base_path, "outputs")
        os.makedirs(custom_out_path, exist_ok=True)

        for batch_number, image in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            filename_with_batch = f"{filename_prefix}_{time.time()}_{batch_number}"
            png_file = f"{filename_with_batch}.png"
            json_file = f"{filename_with_batch}.json"
            
            full_png_path = os.path.join(custom_out_path, png_file)
            full_json_path = os.path.join(custom_out_path, json_file)

            full_log = {
                "system": sys_info,
                "workflow_analysis": workflow_stats,
                "execution": exec_info,
                "prompt_api_format": prompt, 
            }

            with open(full_json_path, 'w', encoding='utf-8') as f:
                json.dump(full_log, f, indent=4)

            metadata = PngInfo()
            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt))
            if extra_pnginfo is not None:
                for x in extra_pnginfo:
                    metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            img.save(full_png_path, pnginfo=metadata, compress_level=4)
            
            # FIX: Updated folder path string to match new directory structure
            results.append({
                "filename": png_file,
                "subfolder": "custom_nodes/ComfyUI-ChomfyNodes/outputs",
                "type": self.type
            })

        return {"ui": {"images": results}}

NODE_CLASS_MAPPINGS = {
    "ChomfyMegaPrompt": ChomfyMegaPrompt,
    "ChomfyDetailedLogger": ChomfyDetailedLogger
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ChomfyMegaPrompt": "Chomfy Mega Wildcard Builder (24 Lines)",
    "ChomfyDetailedLogger": "Chomfy Forensic Saver"
}