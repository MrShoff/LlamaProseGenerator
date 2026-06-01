# The Scriptorium

> A collaborative prose generation studio for local LLMs — purpose-built for long-form fiction.

The Scriptorium is a Streamlit-based web application that manages the full scene-to-manuscript pipeline for AI-assisted novel writing. It connects to a locally-running Ollama instance, reads structured prompt packets from a project directory, generates scene drafts, and guides authors through a critique → revision → selection workflow — all in a premium, collaborative interface designed for two or more writers on a shared local network.

---

## Features

- **Sequential scene production** — scenes are locked until the prior scene is fully accepted, preserving narrative continuity
- **Prior-scene context injection** — each new generation automatically includes the completed prior scene to maintain voice and continuity
- **Three-variant drafting** — generates A/B/C drafts at stepped temperatures (0.7 / 0.85 / 1.0) for creative range
- **Four-stage pipeline** — Draft → Critique → Revision → Select, each powered by the scene's corresponding prompt packet
- **Paragraph-level AI revision** — highlight any passage in the reader view, add a prompt comment, and regenerate just that paragraph
- **Collaborative annotations** — viewer comments and AI-prompt comments are stored in a shared SQLite database and visible to all users
- **Inline text editing** — click any paragraph to edit directly; every version is preserved in edit history
- **Chapter assembly** — once all scenes in a chapter are selected, one click concatenates them into a chapter file
- **Full manuscript reader** — read the book in its current state at any time, with annotations displayed inline
- **LAN multi-user** — run the server on one machine; collaborators connect via local network IP
- **Premium dark UI** — gothic scholarly aesthetic with custom typography, animations, and component design

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | |
| Ollama | Latest | Running on `localhost:11434` or configured host |
| A local LLM | Any chat model | Tested with Gemma 4 27B IT |
| Git | Any | For version control |

---

## Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/LlamaProseGenerator.git
cd LlamaProseGenerator

# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the application
streamlit run app.py
```

On first launch you will be prompted to enter a username and configure your project paths via the Settings page.

---

## Project Directory Structure

The Scriptorium expects a novel project organized as follows:

```
Your_Novel_Project/
  04_Prompts/
    Chapter_01/
      Scene_01/
        CH01_SC01_CONTEXT_PACKET.md
        CH01_SC01_DRAFT_PROMPT.md
        CH01_SC01_CRITIQUE_PROMPT.md
        CH01_SC01_REVISION_PROMPT.md
      Scene_02/
        CH01_SC01_TO_SC02_CONTINUITY_HANDOFF.md   (optional)
        CH01_SC02_CONTEXT_PACKET.md
        ...
  05_Local_Model_Output/
    Chapter_01/
      scene_01_variant_a.md
      scene_01_variant_b.md
      scene_01_variant_c.md
      scene_01_selected.md
      chapter_01.md
```

Configure the paths to `04_Prompts` and `05_Local_Model_Output` in the Settings page.

---

## Multi-User LAN Setup

1. Run the server on the machine that also hosts Ollama:
   ```bash
   streamlit run app.py --server.address 0.0.0.0 --server.port 8501
   ```
2. Find the host machine's local IP address (e.g., `192.168.1.42`)
3. Other users on the same network navigate to `http://192.168.1.42:8501`
4. Each user sets a username on first visit — used for comment attribution

The shared SQLite database (`prose_generator.db`) lives on the server machine. Refresh the browser to see changes made by other users.

---

## Configuration

Settings are persisted to `config.json` (gitignored — machine-specific):

| Setting | Default | Description |
|---|---|---|
| `prompts_path` | *(required)* | Absolute path to `04_Prompts` directory |
| `output_path` | *(required)* | Absolute path to `05_Local_Model_Output` directory |
| `ollama_url` | `http://localhost:11434` | Ollama API base URL |
| `model_name` | *(required)* | Ollama model identifier |
| `num_ctx` | `8192` | Context window size in tokens |

---

## Technology Stack

| Layer | Technology |
|---|---|
| UI | Streamlit + custom CSS |
| State | SQLite via `sqlite3` (stdlib) |
| LLM API | Ollama `/api/chat` (REST) |
| HTTP | `httpx` (async-compatible) |
| Config | JSON file (`config.json`) |

---

## License

MIT
