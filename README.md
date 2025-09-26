# ComfyUI-ChomfyNodes

A collection of light-hearted utility nodes for [ComfyUI](https://github.com/comfyanonymous/ComfyUI).

## ✨ Nodes

### Simple Number Counter
Counts upward (or downward) by a configurable amount.

| Input        | Type    | Description                                      |
|--------------|---------|--------------------------------------------------|
| start_value  | FLOAT   | Initial value emitted                            |
| step         | FLOAT   | Amount to add each tick                          |
| max_steps    | INT     | Total numbers to emit (`-1` for infinite)        |
| auto_reset   | BOOLEAN | Auto-restart after reaching `max_steps`          |
| reset        | BOOLEAN | Manual reset toggle                              |

Outputs:

- `value` – current number in the sequence
- `step_index` – 1-based emission index
- `done` – `True` once `max_steps` reached (when `max_steps >= 0`)

## 📥 Installation

1. Clone or download this repo into ComfyUI’s `custom_nodes` directory:

   ```bash
   cd /path/to/ComfyUI/custom_nodes
   git clone https://github.com/yourname/ComfyUI-ChomfyNodes.git