"""
Wildcard Prompt Assembler node for ComfyUI.
-------------------------------------------

Builds a prompt by sampling lines from multiple files (txt, md, csv, docx),
inserting optional custom text between each segment.

Provides three ways to supply the list of files:
  • MANUAL      -> newline-separated paths typed into the node
  • CONFIG_FILE -> read file paths from an external manifest (.txt)
  • DIRECTORY   -> scan a directory with an optional glob pattern (e.g. *.txt)

Supports random or sequential selection per file, caching, and automatic
reloading when the underlying files change.
"""

import csv
import glob
import json
import os
import random
from typing import Dict, List, Optional, Tuple

try:
    import docx  # python-docx for .docx support
except ImportError:
    docx = None


class WildcardPromptAssembler:
    CATEGORY = "Chomfy 🧮"
    FUNCTION = "compose"
    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("prompt", "segments_json", "file_count")

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._positions: Dict[str, int] = {}
        self._global_step: int = 0

    # ------------------------------------------------------------------ #
    # Input specification
    # ------------------------------------------------------------------ #
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (
                    "STRING",
                    {
                        "default": "MANUAL",
                        "choices": ["MANUAL", "CONFIG_FILE", "DIRECTORY"],
                    },
                ),
                "selection_mode": (
                    "STRING",
                    {
                        "default": "RANDOM",
                        "choices": ["RANDOM", "SEQUENTIAL"],
                    },
                ),
                "auto_space": ("BOOLEAN", {"default": True}),
                "strip_whitespace": ("BOOLEAN", {"default": True}),
                "ignore_blank_lines": ("BOOLEAN", {"default": True}),
                "random_seed": ("INT", {"default": -1}),
            },
            "optional": {
                # Manual mode
                "manual_paths": ("STRING", {"default": "", "multiline": True}),

                # Config-file mode
                "manifest_path": ("STRING", {"default": ""}),

                # Directory mode
                "directory_path": ("STRING", {"default": ""}),
                "directory_glob": ("STRING", {"default": "*.txt"}),
                "max_files": ("INT", {"default": 16, "min": 1, "max": 128}),

                # General options
                "custom_inserts": ("STRING", {"default": "", "multiline": True}),
                "prefix_text": ("STRING", {"default": ""}),
                "suffix_text": ("STRING", {"default": ""}),
                "csv_column": ("STRING", {"default": ""}),
                "reset": ("BOOLEAN", {"default": False}),
            },
        }

    # ------------------------------------------------------------------ #
    # Public execution entrypoint
    # ------------------------------------------------------------------ #
    def compose(
        self,
        mode: str,
        selection_mode: str,
        auto_space: bool,
        strip_whitespace: bool,
        ignore_blank_lines: bool,
        random_seed: int,
        manual_paths: str = "",
        manifest_path: str = "",
        directory_path: str = "",
        directory_glob: str = "*.txt",
        max_files: int = 16,
        custom_inserts: str = "",
        prefix_text: str = "",
        suffix_text: str = "",
        csv_column: str = "",
        reset: bool = False,
    ):
        if reset:
            self._reset_state()

        files = self._gather_files(
            mode=mode,
            manual_paths=manual_paths,
            manifest_path=manifest_path,
            directory_path=directory_path,
            directory_glob=directory_glob,
            max_files=max_files,
        )
        if not files:
            raise ValueError("Wildcard Prompt Assembler: No files found for the selected mode.")

        inserts = self._parse_custom_inserts(custom_inserts)

        rng = self._make_rng(random_seed)

        segments = []
        parts = [prefix_text] if prefix_text else []

        for idx, file_entry in enumerate(files):
            path, column = self._split_path_and_column(file_entry, csv_column)
            line_text, line_index, total = self._select_line_from_file(
                path=path,
                column=column,
                selection_mode=selection_mode,
                strip=strip_whitespace,
                ignore_blank=ignore_blank_lines,
                rng=rng,
            )

            if idx < len(inserts) and inserts[idx]:
                parts.append(inserts[idx])

            parts.append(line_text)

            segments.append(
                {
                    "file": path,
                    "column": column,
                    "line_index": line_index,
                    "total_lines": total,
                    "text": line_text,
                }
            )

        if len(inserts) > len(files) and inserts[len(files)]:
            parts.append(inserts[len(files)])

        if suffix_text:
            parts.append(suffix_text)

        prompt = (
            " ".join(filter(None, parts))
            if auto_space
            else "".join(part for part in parts if part)
        )

        segments_json = json.dumps(
            {
                "mode": mode,
                "selection_mode": selection_mode,
                "prompt": prompt,
                "segments": segments,
            },
            ensure_ascii=False,
        )

        return prompt, segments_json, len(files)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _reset_state(self):
        self._positions.clear()
        self._global_step = 0

    def _make_rng(self, random_seed: int) -> random.Random:
        self._global_step += 1
        if random_seed >= 0:
            return random.Random(random_seed + self._global_step - 1)
        return random.Random()

    def _gather_files(
        self,
        mode: str,
        manual_paths: str,
        manifest_path: str,
        directory_path: str,
        directory_glob: str,
        max_files: int,
    ) -> List[str]:
        if mode == "MANUAL":
            return self._parse_manual_paths(manual_paths, max_files)
        if mode == "CONFIG_FILE":
            return self._load_manifest(manifest_path, max_files)
        if mode == "DIRECTORY":
            return self._scan_directory(directory_path, directory_glob, max_files)
        raise ValueError(f"Unknown mode '{mode}'")

    def _parse_manual_paths(self, manual_paths: str, max_files: int) -> List[str]:
        entries = [
            line.strip()
            for line in manual_paths.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        return entries[:max_files]

    def _load_manifest(self, manifest_path: str, max_files: int) -> List[str]:
        if not manifest_path:
            raise ValueError("Manifest mode requires 'manifest_path'.")
        path = os.path.expanduser(manifest_path)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Manifest file not found: {path}")

        entries = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                entries.append(line)
        return entries[:max_files]

    def _scan_directory(self, directory_path: str, directory_glob: str, max_files: int) -> List[str]:
        if not directory_path:
            raise ValueError("Directory mode requires 'directory_path'.")
        directory = os.path.expanduser(directory_path)
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"Directory not found: {directory}")

        pattern = os.path.join(directory, directory_glob or "*.txt")
        entries = sorted(glob.glob(pattern))
        return entries[:max_files]

    def _parse_custom_inserts(self, custom_inserts: str) -> List[str]:
        if not custom_inserts:
            return []
        return [line.rstrip("\n") for line in custom_inserts.splitlines()]

    def _split_path_and_column(self, entry: str, default_column: str) -> Tuple[str, Optional[str]]:
        if "::" in entry:
            path, column = entry.split("::", 1)
            return path.strip(), column.strip() or None
        return entry.strip(), default_column.strip() or None

    def _select_line_from_file(
        self,
        path: str,
        column: Optional[str],
        selection_mode: str,
        strip: bool,
        ignore_blank: bool,
        rng: random.Random,
    ) -> Tuple[str, int, int]:
        path = os.path.expanduser(path)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Prompt file not found: {path}")

        records = self._load_file_lines(path, column, strip, ignore_blank)
        if not records:
            raise ValueError(f"No usable lines found in file: {path}")

        key = f"{path}::{column or ''}"

        if selection_mode == "SEQUENTIAL":
            position = self._positions.get(key, 0)
            idx = position % len(records)
            self._positions[key] = position + 1
        else:
            idx = rng.randrange(len(records))

        record = records[idx]
        return record["text"], record["line_index"], len(records)

    def _load_file_lines(
        self,
        path: str,
        column: Optional[str],
        strip: bool,
        ignore_blank: bool,
    ) -> List[Dict[str, str]]:
        mtime = os.path.getmtime(path)
        cache_key = f"{path}::{column or ''}"
        cached = self._cache.get(cache_key)
        if cached and cached["mtime"] == mtime and cached["strip"] == strip and cached["ignore_blank"] == ignore_blank:
            return cached["records"]

        ext = os.path.splitext(path)[1].lower()
        if ext in {".txt", ".log"}:
            records = self._read_text_file(path, strip, ignore_blank)
        elif ext == ".md":
            records = self._read_markdown(path, strip, ignore_blank)
        elif ext == ".csv":
            records = self._read_csv(path, column, strip, ignore_blank)
        elif ext == ".docx":
            records = self._read_docx(path, strip, ignore_blank)
        else:
            raise ValueError(f"Unsupported file extension '{ext}' for {path}")

        self._cache[cache_key] = {
            "mtime": mtime,
            "records": records,
            "strip": strip,
            "ignore_blank": ignore_blank,
        }
        return records

    def _read_text_file(self, path: str, strip: bool, ignore_blank: bool) -> List[Dict[str, str]]:
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                text = line.rstrip("\n")
                if strip:
                    text = text.strip()
                if ignore_blank and not text:
                    continue
                records.append({"line_index": idx, "text": text})
        return records

    def _read_markdown(self, path: str, strip: bool, ignore_blank: bool) -> List[Dict[str, str]]:
        return self._read_text_file(path, strip, ignore_blank)

    def _read_csv(
        self,
        path: str,
        column: Optional[str],
        strip: bool,
        ignore_blank: bool,
    ) -> List[Dict[str, str]]:
        records = []
        with open(path, newline="", encoding="utf-8") as f:
            if column:
                reader = csv.DictReader(f)
                if column not in reader.fieldnames:
                    raise ValueError(
                        f"CSV column '{column}' not found in {path}. Available columns: {reader.fieldnames}"
                    )
                for idx, row in enumerate(reader, start=1):
                    text = row.get(column, "")
                    if strip:
                        text = text.strip()
                    if ignore_blank and not text:
                        continue
                    records.append({"line_index": idx, "text": text})
            else:
                reader = csv.reader(f)
                for idx, row in enumerate(reader, start=1):
                    text = ", ".join(cell.strip() if strip else cell for cell in row)
                    if strip:
                        text = text.strip()
                    if ignore_blank and not text:
                        continue
                    records.append({"line_index": idx, "text": text})
        return records

    def _read_docx(self, path: str, strip: bool, ignore_blank: bool) -> List[Dict[str, str]]:
        if docx is None:
            raise ImportError(
                "python-docx is required for DOCX support. Install with 'pip install python-docx'."
            )

        document = docx.Document(path)
        records = []
        for idx, paragraph in enumerate(document.paragraphs, start=1):
            text = paragraph.text
            if strip:
                text = text.strip()
            if ignore_blank and not text:
                continue
            records.append({"line_index": idx, "text": text})
        return records


NODE_CLASS_MAPPINGS = {"WildcardPromptAssembler": WildcardPromptAssembler}
NODE_DISPLAY_NAME_MAPPINGS = {"WildcardPromptAssembler": "Wildcard Prompt Assembler"}