class ChomfyUniversalCounter:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "mode": (["Increment", "Decrement", "Random Step"],),
                "start_value": ("INT", {"default": 0, "min": -99999999, "max": 99999999}),
                "step_size": ("INT", {"default": 1, "min": 1, "max": 10000}),
                "modulo_limit": ("INT", {"default": 0, "min": 0, "max": 99999999, "tooltip": "Reset to 0 after reaching this number (0 = disabled)"}),
                # The control_value creates a unique hash to force updates
                "control_seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT", "STRING")
    RETURN_NAMES = ("int_out", "float_out", "str_out")
    FUNCTION = "count_process"
    CATEGORY = "ChomfyNodes/Utils"

    # Memory to hold the count between runs
    # We use a dictionary keyed by node_id to handle multiple counters in one workflow
    _counters = {}

    @classmethod
    def IS_CHANGED(s, **kwargs):
        # This tells ComfyUI: "Something changed, run me again!"
        # We return float("NaN") which is never equal to itself, ensuring a rerun.
        return float("NaN")

    def count_process(self, mode, start_value, step_size, modulo_limit, control_seed):
        # Determine the unique ID for this specific node instance based on the seed/settings
        unique_id = f"{control_seed}_{start_value}_{step_size}"
        
        # Initialize if not exists
        if unique_id not in self._counters:
            self._counters[unique_id] = start_value
        
        current_val = self._counters[unique_id]
        
        # Calculate Next Value for *Next* run (or current logic)
        # But usually, people want the count to move forward.
        
        if mode == "Increment":
            new_val = current_val + step_size
        elif mode == "Decrement":
            new_val = current_val - step_size
        elif mode == "Random Step":
            import random
            new_val = current_val + random.randint(-step_size, step_size)
        else:
            new_val = current_val

        # Handle Modulo (Looping)
        if modulo_limit > 0:
            if new_val >= modulo_limit:
                new_val = 0
            if new_val < 0:
                # Wrap around for negative
                new_val = modulo_limit - 1

        # Update memory
        self._counters[unique_id] = new_val

        # Return formats
        return (int(current_val), float(current_val), str(int(current_val)))

NODE_CLASS_MAPPINGS = {
    "ChomfyUniversalCounter": ChomfyUniversalCounter
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ChomfyUniversalCounter": "Chomfy Universal Counter"
}