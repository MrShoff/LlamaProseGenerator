# Manual Smoke Tests — Phase 1

Run these in a Python REPL from the project root after `pip install -r requirements.txt`.

---

## config.py

```python
from config import load_config, save_config, validate_config, Config

# Defaults when config.json doesn't exist yet
cfg = load_config()
print(cfg)

# Empty config should fail validation (ollama_url has a default, so 3 required fields fail)
errors = validate_config(cfg)
print(errors)
assert len(errors) == 3, errors

# Fill in and save
cfg.prompts_path = r"D:\Development\Personal\Books\Project1\Romance_Novel_Project\04_Prompts"
cfg.output_path  = r"D:\Development\Personal\Books\Project1\Romance_Novel_Project\05_Local_Model_Output"
cfg.model_name   = "tinyrick/gemma-4-31B-it-uncensored-heretic-llmfan46:Q4_K_M"
save_config(cfg)

# Round-trip
cfg2 = load_config()
assert cfg2.prompts_path == cfg.prompts_path
assert cfg2.model_name   == cfg.model_name
assert cfg2.num_ctx      == 8192
print("config.py OK")
```

---

## database.py

```python
from database import (
    init_db,
    get_scene_status, set_scene_status, get_all_scene_statuses,
    add_comment, get_comments, resolve_comment,
    add_edit, get_edit_history,
)

init_db()  # idempotent — safe to call repeatedly

# --- Scene status ---
set_scene_status("CH01_SC01", "selected", "alice")
row = get_scene_status("CH01_SC01")
assert row["status"] == "selected"
assert row["last_updated_by"] == "alice"

# Upsert
set_scene_status("CH01_SC01", "has_variants", "bob", active_variant="b")
row = get_scene_status("CH01_SC01")
assert row["status"] == "has_variants"
assert row["active_variant"] == "b"

all_statuses = get_all_scene_statuses()
assert "CH01_SC01" in all_statuses

# --- Comments ---
cid = add_comment("CH01_SC01", "alice", "Love this opening.", "viewer", paragraph_index=0)
comments = get_comments("CH01_SC01", paragraph_index=0)
assert len(comments) == 1
assert comments[0]["content"] == "Love this opening."
assert comments[0]["comment_type"] == "viewer"

resolve_comment(cid)
comments_after = get_comments("CH01_SC01", paragraph_index=0)
assert len(comments_after) == 0  # resolved hidden by default
comments_with = get_comments("CH01_SC01", paragraph_index=0, include_resolved=True)
assert len(comments_with) == 1

# AI prompt comment
add_comment("CH01_SC01", "bob", "Make this more visceral.", "ai_prompt", paragraph_index=2)
ai_comments = get_comments("CH01_SC01", paragraph_index=2)
assert ai_comments[0]["comment_type"] == "ai_prompt"

# --- Edits ---
add_edit("CH01_SC01", 3, "alice", "Original line.", "Improved line.")
history = get_edit_history("CH01_SC01", paragraph_index=3)
assert len(history) == 1
assert history[0]["edited_text"] == "Improved line."

add_edit("CH01_SC01", 3, "bob", "Improved line.", "Even better line.")
history2 = get_edit_history("CH01_SC01", paragraph_index=3)
assert len(history2) == 2  # newest first
assert history2[0]["edited_text"] == "Even better line."

print("database.py OK")
```

---

## scene_manager.py

```python
from config import load_config
from scene_manager import (
    discover_scenes, read_prompt, build_system_prompt,
    status_from_files, active_variant_from_files,
    split_paragraphs, replace_paragraph,
    build_critique_user_prompt, build_revision_user_prompt,
    chapter_is_assembleable,
)

cfg = load_config()

# Discovery
scenes = discover_scenes(cfg.prompts_path)
print(f"Discovered {len(scenes)} scenes")
for s in scenes:
    print(f"  {s.scene_key}  —  {s.prompts_dir.name}")
assert len(scenes) > 0

# Prompt reading
sc = scenes[0]
context = read_prompt(sc, "CONTEXT_PACKET")
draft   = read_prompt(sc, "DRAFT_PROMPT")
print(f"Context packet: {len(context):,} chars")
print(f"Draft prompt:   {len(draft):,} chars")
assert len(context) > 100
assert len(draft) > 100

# System prompt composition (first scene — no prior selected)
system = build_system_prompt(sc, cfg.output_path, scenes)
print(f"System prompt:  {len(system):,} chars")
assert context in system

# System prompt for second scene (if it exists and SC01 is selected)
if len(scenes) > 1:
    sc2 = scenes[1]
    system2 = build_system_prompt(sc2, cfg.output_path, scenes)
    print(f"SC02 system prompt: {len(system2):,} chars")

# Status from files
status = status_from_files(cfg.output_path, sc.chapter, sc.scene)
print(f"{sc.scene_key} file-derived status: {status}")

# Paragraph utilities
sample = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
paras = split_paragraphs(sample)
assert len(paras) == 3
replaced = replace_paragraph(sample, 1, "Replaced second paragraph.")
assert "Replaced" in replaced
assert "First" in replaced

print("scene_manager.py OK")
```

---

## ollama_client.py

```python
from config import load_config
from ollama_client import check_connectivity, list_local_models, generate

cfg = load_config()

# Connectivity
ok, err = check_connectivity(cfg.ollama_url)
print(f"Ollama reachable: {ok}" + (f"  ({err})" if err else ""))

# Available models
if ok:
    models = list_local_models(cfg.ollama_url)
    print(f"Models available: {models}")
    assert cfg.model_name in models, f"{cfg.model_name!r} not found in {models}"

    # Short generation to confirm the model responds
    result = generate(
        base_url=cfg.ollama_url,
        model=cfg.model_name,
        system="You are a test assistant. Be brief.",
        user="Say hello in exactly five words.",
        temperature=0.5,
        num_ctx=512,
    )
    print(f"Generated: {result!r}")
    assert len(result) > 0
    print("ollama_client.py OK")
else:
    print("Skipping generation test — Ollama not reachable.")
```
