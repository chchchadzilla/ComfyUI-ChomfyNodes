import sys
import os
import importlib.util

# Automatically scan the 'nodes' folder for .py files
node_dir = os.path.join(os.path.dirname(__file__), "nodes")
node_files = [f for f in os.listdir(node_dir) if f.endswith(".py") and f != "__init__.py"]

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

for file in node_files:
    module_name = file[:-3]
    file_path = os.path.join(node_dir, file)
    
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if hasattr(module, "NODE_CLASS_MAPPINGS"):
        NODE_CLASS_MAPPINGS.update(module.NODE_CLASS_MAPPINGS)
    
    if hasattr(module, "NODE_DISPLAY_NAME_MAPPINGS"):
        NODE_DISPLAY_NAME_MAPPINGS.update(module.NODE_DISPLAY_NAME_MAPPINGS)

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

print(f"Loaded chomfy nodes: {list(NODE_CLASS_MAPPINGS.keys())}")