"""
Simple Number Counter node for ComfyUI.
---------------------------------------

Drop this file into: ComfyUI/custom_nodes/simple_number_counter.py
Restart ComfyUI and the node will appear under the category:
    "Utils 🧮 / Simple Number Counter"
"""

from typing import Dict, Any


class SimpleNumberCounter:
    """
    A tiny stateful counter node.
    On each execution it emits the next value in the sequence.

    Features:
      • start_value:   first value to emit
      • step:          amount to add (can be negative or fractional)
      • max_steps:     total number of values to output (set -1 for endless)
      • auto_reset:    if True, automatically restarts when max_steps reached
      • reset:         manual reset toggle

    Returns:
      • value        -> current number in the sequence
      • step_index   -> 1-based index of the emitted value
      • done         -> True if max_steps reached (only when max_steps >= 0)
    """

    CATEGORY = "Utils 🧮"
    RETURN_TYPES = ("FLOAT", "INT", "BOOLEAN")
    RETURN_NAMES = ("value", "step_index", "done")

    def __init__(self):
        self._state: Dict[str, Any] = {
            "initialized": False,
            "start_value": 0.0,
            "step": 1.0,
            "max_steps": -1,
            "auto_reset": False,
            "next_value": 0.0,
            "last_value": 0.0,
            "emitted_steps": 0,
        }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "start_value": ("FLOAT", {"default": 0.0}),
                "step": ("FLOAT", {"default": 1.0}),
                "max_steps": ("INT", {"default": -1, "min": -1}),
            },
            "optional": {
                "auto_reset": ("BOOLEAN", {"default": False}),
                "reset": ("BOOLEAN", {"default": False}),
            },
        }

    FUNCTION = "count"

    def _reset_state(self, start_value: float, step: float, max_steps: int, auto_reset: bool):
        self._state.update(
            {
                "initialized": True,
                "start_value": start_value,
                "step": step,
                "max_steps": max_steps,
                "auto_reset": auto_reset,
                "next_value": start_value,
                "last_value": start_value,
                "emitted_steps": 0,
            }
        )

    def _should_reset(
        self,
        start_value: float,
        step: float,
        max_steps: int,
        auto_reset: bool,
        reset: bool,
    ) -> bool:
        if reset:
            return True
        if not self._state["initialized"]:
            return True
        return (
            self._state["start_value"] != start_value
            or self._state["step"] != step
            or self._state["max_steps"] != max_steps
            or self._state["auto_reset"] != auto_reset
        )

    def count(
        self,
        start_value: float,
        step: float,
        max_steps: int,
        auto_reset: bool = False,
        reset: bool = False,
    ):
        if self._should_reset(start_value, step, max_steps, auto_reset, reset):
            self._reset_state(start_value, step, max_steps, auto_reset)

        # If max_steps reached, decide whether to hold or auto-reset
        if max_steps >= 0 and self._state["emitted_steps"] >= max_steps:
            if self._state["auto_reset"]:
                self._reset_state(start_value, step, max_steps, auto_reset)
            else:
                return (
                    float(self._state["last_value"]),
                    int(self._state["emitted_steps"]),
                    True,
                )

        value = float(self._state["next_value"])
        self._state["last_value"] = value
        self._state["emitted_steps"] += 1
        self._state["next_value"] = value + step

        done = max_steps >= 0 and self._state["emitted_steps"] >= max_steps
        return value, int(self._state["emitted_steps"]), done


NODE_CLASS_MAPPINGS = {
    "SimpleNumberCounter": SimpleNumberCounter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SimpleNumberCounter": "Simple Number Counter",
}