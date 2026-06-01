# Architecture

## Overview

The Scriptorium is a single-server, multi-client Streamlit application. One machine runs both Ollama and the Streamlit server. Other users on the local network connect via browser. All shared state flows through a SQLite database on the server; generated prose is stored as markdown files in the novel project directory.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Server Machine                          │
│                                                                 │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │   Streamlit │    │  SQLite DB       │    │  Ollama       │  │
│  │   app.py    │◄──►│  prose_generator │    │  :11434       │  │
│  │   :8501     │    │  .db             │    │               │  │
│  └──────┬──────┘    └──────────────────┘    └───────┬───────┘  │
│         │                                           │           │
│         │           ┌──────────────────┐            │           │
│         └──────────►│  Novel Project   │            │           │
│                     │  Directory       │            │           │
│                     │  04_Prompts/     │            │           │
│                     │  05_Local_Model_ │            │           │
│                     │  Output/         │◄───────────┘           │
│                     └──────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
         ▲                    ▲
         │  HTTP              │  HTTP
         │                    │
┌────────┴────────┐  ┌────────┴────────┐
│  User A Browser │  │  User B Browser │
│  (LAN)          │  │  (LAN)          │
└─────────────────┘  └─────────────────┘
```

---

## Layer Breakdown

### `app.py` — Main Pipeline Page
The primary Streamlit page. Renders the scene picker sidebar, injects the global CSS design system, and hosts the four-tab pipeline UI (Draft / Critique / Revision / Select). Delegates all data operations to `scene_manager.py`, `database.py`, and `ollama_client.py`.

### `pages/reader.py` — Manuscript Reader
Displays the full manuscript in reading order: assembled chapters first, then selected-but-unassembled scenes, then a progress indicator for what remains. Renders paragraph-level comments inline and provides comment + AI-prompt tooling per paragraph.

### `pages/settings.py` — Configuration
Reads and writes `config.json`. Validates Ollama connectivity and project directory structure on save. No LLM calls.

### `scene_manager.py` — File System Layer
- Scans `04_Prompts/` to discover all available scenes
- Reads prompt files (`CONTEXT_PACKET`, `DRAFT_PROMPT`, `CRITIQUE_PROMPT`, `REVISION_PROMPT`, continuity handoff)
- Reads prior scene's `selected.md` for context injection
- Writes generated output files to `05_Local_Model_Output/`
- Assembles chapters from selected scene files
- Never touches SQLite — pure file I/O

### `ollama_client.py` — LLM API Client
- Wraps `POST /api/chat` with the system/user message split
- Handles timeout, connection errors, and malformed responses gracefully
- Exposes a single `generate(system, user, temperature, num_ctx) -> str` function
- No streaming — returns the complete response

### `database.py` — Shared State Layer
- Initializes the SQLite schema on first run
- Provides typed CRUD functions for comments, edits, and scene status
- All reads return plain Python dicts/lists — no ORM
- Uses WAL journal mode for better multi-reader concurrency

### `config.py` — Configuration Management
- Reads/writes `config.json`
- Provides a `Config` dataclass with typed fields and defaults
- Validates that required fields are set before allowing pipeline operations

---

## Database Schema

```sql
-- Scene pipeline status
CREATE TABLE IF NOT EXISTS scene_status (
    scene_key        TEXT PRIMARY KEY,      -- e.g. "CH01_SC02"
    status           TEXT NOT NULL,         -- see Scene Status Lifecycle
    active_variant   TEXT,                  -- 'a', 'b', or 'c' — variant under critique/revision
    last_updated_by  TEXT,
    last_updated_at  TEXT DEFAULT (datetime('now'))
);

-- Viewer and AI-prompt comments
CREATE TABLE IF NOT EXISTS comments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_key        TEXT NOT NULL,
    paragraph_index  INTEGER,               -- NULL = whole-scene comment
    comment_type     TEXT NOT NULL,         -- 'viewer' | 'ai_prompt'
    username         TEXT NOT NULL,
    content          TEXT NOT NULL,
    resolved         INTEGER DEFAULT 0,     -- 0 = open, 1 = resolved
    created_at       TEXT DEFAULT (datetime('now'))
);

-- Full edit history (versioned)
CREATE TABLE IF NOT EXISTS edits (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_key        TEXT NOT NULL,
    paragraph_index  INTEGER NOT NULL,
    username         TEXT NOT NULL,
    original_text    TEXT NOT NULL,
    edited_text      TEXT NOT NULL,
    edited_at        TEXT DEFAULT (datetime('now'))
);
```

### Scene Status Lifecycle

```
locked
  │  (prior scene selected)
  ▼
needs_draft
  │  (generate 3 variants)
  ▼
has_variants
  │  (user chooses variant to critique)
  ▼
in_critique
  │  (critique generation complete)
  ▼
has_critique
  │  (generate revision)
  ▼
has_revision
  │  (user selects a draft as final)
  ▼
selected
  │  (all scenes in chapter selected → assemble)
  ▼
assembled
```

---

## Ollama API Integration

### Endpoint
```
POST http://{ollama_url}/api/chat
Content-Type: application/json
```

### Request Shape
```json
{
  "model": "tinyrick/gemma-4-31B-it-uncensored-heretic-llmfan46:Q4_K_M",
  "messages": [
    {
      "role": "system",
      "content": "<contents of CONTEXT_PACKET.md>"
    },
    {
      "role": "user",
      "content": "<contents of DRAFT_PROMPT.md>"
    }
  ],
  "options": {
    "temperature": 0.85,
    "num_ctx": 8192
  },
  "stream": false
}
```

### Response Shape
```json
{
  "message": {
    "role": "assistant",
    "content": "<generated prose>"
  },
  "done": true
}
```

### Per-Pass Temperature Strategy

| Pass | Temperature | Rationale |
|---|---|---|
| Draft Variant A | 0.7 | Conservative — reliable, on-spec prose |
| Draft Variant B | 0.85 | Balanced — slight creative risk |
| Draft Variant C | 1.0 | Bold — unexpected choices, vivid imagery |
| Critique | 0.3 | Analytical — consistent, focused evaluation |
| Revision | 0.7 | Creative but constrained by critique feedback |
| Paragraph regen | 0.75 | Targeted — must fit surrounding context |

### Prior Scene Context Injection

For Scene N (N > 1), the system message is composed as:

```
[Contents of CH##_SC{N}_CONTEXT_PACKET.md]

---
PRIOR SCENE (for continuity):
[Contents of scene_{N-1}_selected.md]

---
CONTINUITY HANDOFF:
[Contents of CH##_SC{N-1}_TO_SC{N}_CONTINUITY_HANDOFF.md, if present]
```

---

## File System Conventions

### Prompt File Discovery
Scenes are discovered by scanning `04_Prompts/` for files matching:
```
CH{chapter:02d}_SC{scene:02d}_DRAFT_PROMPT.md
```
Any directory depth is supported. Chapter and scene numbers are parsed from the filename.

### Output File Paths
All outputs write to `05_Local_Model_Output/Chapter_{chapter:02d}/`:

| File | Stage | Contents |
|---|---|---|
| `scene_{scene:02d}_variant_a.md` | After draft | Variant A prose |
| `scene_{scene:02d}_variant_b.md` | After draft | Variant B prose |
| `scene_{scene:02d}_variant_c.md` | After draft | Variant C prose |
| `scene_{scene:02d}_variant_{x}_critique.md` | After critique | Critique feedback doc |
| `scene_{scene:02d}_variant_{x}_revised.md` | After revision | Revised prose |
| `scene_{scene:02d}_selected.md` | After selection | Final accepted prose |
| `chapter_{chapter:02d}.md` | After assembly | Full chapter prose |

---

## Multi-User Concurrency

- SQLite is configured with WAL (Write-Ahead Logging) mode, allowing concurrent reads during writes
- Streamlit re-runs on every user interaction, so the UI always reflects database state at render time
- No optimistic locking — last write wins for text edits. Version history in the `edits` table ensures no content is permanently lost
- Generation requests (which can take several minutes) are blocking within a user's session but do not block other users' sessions
- Users refresh their browser to see changes made by others

---

## Configuration File (`config.json`)

```json
{
  "prompts_path": "D:\\path\\to\\04_Prompts",
  "output_path": "D:\\path\\to\\05_Local_Model_Output",
  "ollama_url": "http://localhost:11434",
  "model_name": "tinyrick/gemma-4-31B-it-uncensored-heretic-llmfan46:Q4_K_M",
  "num_ctx": 8192
}
```

`config.json` is gitignored because it contains machine-specific absolute paths.
