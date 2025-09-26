"""
Prompt Line Loader node for ComfyUI.
------------------------------------

Reads plain text, Markdown, CSV, or DOCX files and returns a single line
(or column entry) based on a 1-based index supplied as input.
"""

import csv
import os
from typing import List

try:
    import docx  # python-docx
except ImportError:
    docx = None


class PromptLineLoader:
    CATEGORY = "Chomfy 🧮"
    RETURN_TYPES = ("STRING", "INT", "INT")
    RETURN_NAMES = ("prompt", "line_index", "total_lines")
    FUNCTION = "load_line"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": ""}),
                "line_index": ("INT", {"default": 1, "min": 1}),
            },
            "optional": {
                "csv_column": ("STRING", {"default": ""}),
                "strip_whitespace": ("BOOLEAN", {"default": True}),
            },
        }

    def _read_txt(self, path: str) -> List[str]:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().splitlines()

    def _read_md(self, path: str) -> List[str]:
        return self._read_txt(path)

    def _read_csv(self, path: str, column: str) -> List[str]:
        lines = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f) if column else csv.reader(f)
            for row in reader:
                if isinstance(row, dict):
                    if column not in row:
                        raise ValueError(f"Column '{column}' not found in CSV.")
                    lines.append(row[column])
                else:
                    lines.append(", ".join(row))
        return lines

    def _read_docx(self, path: str) -> List[str]:
        if docx is None:
            raise ImportError(
                "python-docx is required for DOCX support. Install with 'pip install python-docx'."
            )
        document = docx.Document(path)
        return [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]

    def load_line(self, file_path: str, line_index: int, csv_column: str = "", strip_whitespace: bool = True):
        if not file_path:
            raise ValueError("file_path is empty.")

        path = os.path.expanduser(file_path)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File not found: {path}")

        ext = os.path.splitext(path)[1].lower()
        if ext in {".txt", ".log"}:
            lines = self._read_txt(path)
        elif ext == ".md":
            lines = self._read_md(path)
        elif ext == ".csv":
            lines = self._read_csv(path, csv_column)
        elif ext == ".docx":
            lines = self._read_docx(path)
        else:
            raise ValueError(f"Unsupported file extension '{ext}'. Use txt, md, csv, or docx.")

        total_lines = len(lines)
        if total_lines == 0:
            raise ValueError("The selected file contained zero lines.")

        index = ((line_index - 1) % total_lines) + 1
        text = lines[index - 1]

        if strip_whitespace:
            text = text.strip()

        return text, index, total_lines


NODE_CLASS_MAPPINGS = {"PromptLineLoader": PromptLineLoader}
NODE_DISPLAY_NAME_MAPPINGS = {"PromptLineLoader": "Prompt Line Loader"}