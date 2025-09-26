"""
Auto Prompt Line Loader node for ComfyUI.
----------------------------------------

Generates sequential prompt lines from text/markdown/CSV/DOCX files
with built-in counting, modulo-wrapping, and optional auto-reset.

Outputs:
  • prompt       -> the text line for this step
  • line_index   -> 1-based line number within the file (after wrap)
  • step_index   -> 1-based count of how many prompts have been emitted
  • total_lines  -> total lines discovered in the file
  • done         -> True when max_steps reached (max_steps >= 0)
"""

import csv
import os
from typing import List

try:
    import docx  # python-docx
except ImportError:
    docx = None


class AutoPromptLineLoader:
    CATEGORY = "Chomfy 🧮"
    RETURN_TYPES = ("STRING", "INT", "INT", "INT", "BOOLEAN")
    RETURN_NAMES = ("prompt", "line_index", "step_index", "total_lines", "done")
    FUNCTION = "next_prompt"

    def __init__(self):
        self._state = {
            "initialized": False,
            "file_path": "",
            "file_mtime": None,
            "csv_column": "",
            "strip_whitespace": True,
            "start_value": 1,
            "step": 1,
            "max_steps": -1,
            "auto_reset": False,
            "lines": [],
            "total_lines": 0,
            "next_index": 1,
            "emitted_steps": 0,
            "last_prompt": "",
            "last_line_index": 0,
            "last_step_index": 0,
        }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": ""}),
                "start_value": ("INT", {"default": 1}),
                "step": ("INT", {"default": 1}),
                "max_steps": ("INT", {"default": -1, "min": -1}),
            },
            "optional": {
                "auto_reset": ("BOOLEAN", {"default": False}),
                "reset": ("BOOLEAN", {"default": False}),
                "csv_column": ("STRING", {"default": ""}),
                "strip_whitespace": ("BOOLEAN", {"default": True}),
            },
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _normalize_index(self, index: int, total: int) -> int:
        if total == 0:
            raise ValueError("No lines available from the loaded file.")
        return ((index - 1) % total) + 1

    def _read_txt(self, path: str) -> List[str]:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().splitlines()

    def _read_md(self, path: str) -> List[str]:
        return self._read_txt(path)

    def _read_csv(self, path: str, column: str) -> List[str]:
        lines = []
        with open(path, newline="", encoding="utf-8") as f:
            if column:
                reader = csv.DictReader(f)
                if column not in reader.fieldnames:
                    raise ValueError(f"Column '{column}' not found in CSV header: {reader.fieldnames}")
                for row in reader:
                    lines.append(row.get(column, ""))
            else:
                reader = csv.reader(f)
                for row in reader:
                    lines.append(", ".join(row))
        return lines

    def _read_docx(self, path: str) -> List[str]:
        if docx is None:
            raise ImportError(
                "python-docx is required for DOCX support. Install with 'pip install python-docx'."
            )
        document = docx.Document(path)
        return [paragraph.text for paragraph in document.paragraphs if paragraph.text]

    def _load_lines(self, path: str, csv_column: str) -> List[str]:
        ext = os.path.splitext(path)[1].lower()
        if ext in {".txt", ".log"}:
            return self._read_txt(path)
        if ext == ".md":
            return self._read_md(path)
        if ext == ".csv":
            return self._read_csv(path, csv_column)
        if ext == ".docx":
            return self._read_docx(path)
        raise ValueError(f"Unsupported file extension '{ext}'. Use txt, md, csv, or docx.")

    def _should_reset(
        self,
        path: str,
        file_mtime: float,
        start_value: int,
        step: int,
        max_steps: int,
        auto_reset: bool,
        csv_column: str,
        strip_whitespace: bool,
        reset: bool,
    ) -> bool:
        state = self._state
        if reset or not state["initialized"]:
            return True
        return (
            state["file_path"] != path
            or state["file_mtime"] != file_mtime
            or state["start_value"] != start_value
            or state["step"] != step
            or state["max_steps"] != max_steps
            or state["auto_reset"] != auto_reset
            or state["csv_column"] != csv_column
            or state["strip_whitespace"] != strip_whitespace
        )

    def _reset_state(
        self,
        path: str,
        file_mtime: float,
        start_value: int,
        step: int,
        max_steps: int,
        auto_reset: bool,
        csv_column: str,
        strip_whitespace: bool,
    ):
        lines = self._load_lines(path, csv_column)
        if not lines:
            raise ValueError("The selected file contained zero usable lines.")

        self._state.update(
            {
                "initialized": True,
                "file_path": path,
                "file_mtime": file_mtime,
                "csv_column": csv_column,
                "strip_whitespace": strip_whitespace,
                "start_value": start_value,
                "step": step,
                "max_steps": max_steps,
                "auto_reset": auto_reset,
                "lines": lines,
                "total_lines": len(lines),
                "next_index": start_value,
                "emitted_steps": 0,
                "last_prompt": "",
                "last_line_index": 0,
                "last_step_index": 0,
            }
        )

    # ------------------------------------------------------------------ #
    # Public execution function
    # ------------------------------------------------------------------ #
    def next_prompt(
        self,
        file_path: str,
        start_value: int,
        step: int,
        max_steps: int,
        auto_reset: bool = False,
        reset: bool = False,
        csv_column: str = "",
        strip_whitespace: bool = True,
    ):
        if not file_path:
            raise ValueError("file_path is required.")
        path = os.path.expanduser(file_path)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File not found: {path}")

        file_mtime = os.path.getmtime(path)

        if self._should_reset(
            path,
            file_mtime,
            start_value,
            step,
            max_steps,
            auto_reset,
            csv_column,
            strip_whitespace,
            reset,
        ):
            self._reset_state(
                path,
                file_mtime,
                start_value,
                step,
                max_steps,
                auto_reset,
                csv_column,
                strip_whitespace,
            )

        state = self._state

        if max_steps >= 0 and state["emitted_steps"] >= max_steps:
            if state["auto_reset"]:
                self._reset_state(
                    path,
                    file_mtime,
                    start_value,
                    step,
                    max_steps,
                    auto_reset,
                    csv_column,
                    strip_whitespace,
                )
                state = self._state  # refreshed state
            else:
                return (
                    state["last_prompt"],
                    state["last_line_index"],
                    state["last_step_index"],
                    state["total_lines"],
                    True,
                )

        total = state["total_lines"]
        index = self._normalize_index(state["next_index"], total)
        raw_prompt = state["lines"][index - 1]
        prompt = raw_prompt.strip() if strip_whitespace else raw_prompt

        state["emitted_steps"] += 1
        step_index = state["emitted_steps"]
        done = max_steps >= 0 and state["emitted_steps"] >= max_steps
        state["next_index"] = state["next_index"] + state["step"]

        state["last_prompt"] = prompt
        state["last_line_index"] = index
        state["last_step_index"] = step_index

        return prompt, index, step_index, total, done


NODE_CLASS_MAPPINGS = {"AutoPromptLineLoader": AutoPromptLineLoader}
NODE_DISPLAY_NAME_MAPPINGS = {"AutoPromptLineLoader": "Auto Prompt Line Loader"}