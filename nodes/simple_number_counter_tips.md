# Simple Number Counter
## Counts upward (or downward) by a configurable amount.

| Input | **Type** | Description |
|--------------|---------|---------------|
| **start_value** |  FLOAT | *Initial value emitted* |
| **step** | FLOAT | *Amount to add each tick* |
| **max_steps** | INT | *Total numbers to emit (`-1` for infinite)* |
| **auto_reset** | BOOLEAN | *Auto-restart after reaching `max_steps`* |
| **reset** | BOOLEAN | *Manual reset toggle* |

Outputs:

- `value` – current number in the sequence
- `step_index` – 1-based emission index
- `done` – `True` once `max_steps` reached (when `max_steps >= 0`)

## **🔁 High-Level Flow** 

### **Simple Number Counter**

Emits a new step (1, 2, 3, …) **every time** the workflow runs.

### Works With:

#### WAS Math Expressions node
- Uses modulo math to keep the index within the number of lines you have in the prompt file.
- Convert index to a widget/input
#### If needed, you can feed it into:
- Load Line From Text File (or a custom line-loader)
- It takes the (1-based) line index and returns the corresponding prompt text.
- Connect prompt text ***to both*** **CLIP-T5** and **CLIP-L** inputs in the **Flux Clip Text Encoder node**.
- Feed those encodings into your Flux sampler / rest of workflow.

#### 📐 Example Math Expression
##### If you know your prompt file has **exactly 94 lines**, use the Math Expressions node with:

### Use: 
`A % 94) + 1` 
#### Where:
- `A` -- *is the integer output from the counter... 1-based)*
- `% 94` -- *keeps the value between 0–93.*
- `+ 1` -- *shifts it to 1–94 for the Load Line From Text File node (most are 1-based)*.

#### 📝 Tip: Use the step_index output from the Simple Number Counter (already an INT) so you don’t have to cast FLOAT to INT.