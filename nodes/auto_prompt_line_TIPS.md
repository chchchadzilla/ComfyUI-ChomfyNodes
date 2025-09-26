🔌 Hookup
prompt out ⟶ Flux Clip Text Encode (t5 + clip_l inputs)
done (bool) available if you need to stop a loop or trigger a reset
line_index + total_lines exposed if you want to display status or feed elsewhere
📦 Package Update
Drop the file above into your repo at nodes/auto_prompt_line.py.
Update nodes/__init__.py to expose the new node:

from .auto_prompt_line import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
Root __init__.py can remain:

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
Update README.md to describe the one-stop node. Sample snippet:

## Auto Prompt Line Loader
One node that:
- counts steps with wrapping & auto-reset
- loads the matching line from txt/md/csv/docx
- returns prompt, file line index, total lines, and a done flag
🧪 Usage Flow (Now Super Simple)

[Auto Prompt Line Loader] ─┬─ prompt ──► Flux Clip Text Encode (T5 & CLIP-L)
                           ├─ line_index (debug / status)
                           ├─ step_index (overall iteration count)
                           ├─ total_lines (if needed)
                           └─ done (control loops / triggers)
Configure start_value, step, max_steps, etc., right on the node—no external math or counters necessary. The node wraps indices automatically and stays in sync with file changes (reloading when the file is modified).