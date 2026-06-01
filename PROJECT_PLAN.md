# Project Plan

## Product Vision

The Scriptorium is a premium, collaborative prose generation studio. Every interaction should feel intentional and polished — like a tool built by someone who takes both fiction and software seriously. The bar is not "functional" but "delightful."

---

## Phases

### Phase 0 — Foundation (Current)
*Documentation, repository setup, project skeleton.*

**Deliverables:**
- [x] Git repository initialized
- [x] GitHub repository created and pushed
- [x] `README.md` — setup, usage, multi-user guide
- [x] `ARCHITECTURE.md` — technical decisions, schema, API integration
- [x] `PROJECT_PLAN.md` — this document
- [x] `DESIGN_SYSTEM.md` — visual language, component specs
- [ ] `.gitignore`
- [ ] `requirements.txt`
- [ ] Empty module stubs with docstrings

**Acceptance Criteria:**
- Repo is public on GitHub with all documentation committed
- `requirements.txt` installs cleanly into a fresh virtual environment
- All stubs importable without errors

---

### Phase 1 — Core Infrastructure
*The data and logic layer — no UI. All modules independently testable.*

**Deliverables:**
- [ ] `config.py` — `Config` dataclass, `load_config()`, `save_config()`, validation
- [ ] `database.py` — SQLite init (WAL mode), schema creation, CRUD for all three tables
- [ ] `scene_manager.py` — scene discovery, prompt file reading, output file writing, chapter assembly, prior-scene context builder
- [ ] `ollama_client.py` — `generate()` function, error handling, timeout configuration
- [ ] Manual smoke tests documented in `TESTING.md`

**Key Implementation Notes:**
- `scene_manager.py` must handle missing optional files gracefully (continuity handoff may not exist for all scene transitions)
- `ollama_client.py` must surface clear error messages when Ollama is unreachable or the model is not loaded
- Database init must be idempotent — safe to call on every app startup
- `scene_manager.py` derives scene status from file existence, while `database.py` stores the authoritative status in SQLite; `app.py` always trusts the database

**Acceptance Criteria:**
- `config.py` round-trips config correctly; validates required fields
- `database.py` creates all tables; CRUD functions work correctly
- `scene_manager.py` correctly discovers all scenes in the test project; reads all four prompt file types; writes output files to correct paths
- `ollama_client.py` calls Ollama and returns generated text; handles connection errors without crashing

---

### Phase 2 — Design System & Application Shell
*The visual foundation. Every subsequent page builds on this layer.*

**Deliverables:**
- [ ] `styles/theme.py` — CSS string constants: color palette, typography, spacing, animations
- [ ] `styles/components.py` — Python functions that return styled HTML strings for reusable components (cards, badges, status pills, dividers, progress bars)
- [ ] Global CSS injected via `st.markdown(..., unsafe_allow_html=True)` on every page load
- [ ] Base layout established: sidebar navigation, page header, content area
- [ ] Settings page (`pages/settings.py`) — functional, validated, styled
- [ ] Username prompt modal on first visit
- [ ] "Ollama status" indicator in sidebar (green/red based on connectivity ping)

**Design Language:**
- Gothic scholarly aesthetic: deep dark backgrounds, aged-parchment text, gold accents, subtle grain texture via CSS
- Custom fonts loaded via Google Fonts CDN: Cormorant Garamond (display/body), Inter (UI chrome)
- All interactive elements have hover transitions (150ms ease)
- Status badges use color + icon — never color alone

**Acceptance Criteria:**
- App launches with correct dark theme applied globally
- Settings page saves and validates config; shows success/error toast
- Username persists across page navigation within a session
- Ollama status indicator correctly shows connectivity state
- All typography renders with correct font families
- No visual regressions at 1080p and 1440p viewport sizes

---

### Phase 3 — Production Pipeline
*The core scene generation workflow.*

**Deliverables:**

**Scene Picker (Sidebar):**
- [ ] Hierarchical list: Chapter → Scene
- [ ] Status badge per scene (locked / needs draft / has variants / in critique / has critique / has revision / selected / assembled)
- [ ] Click to navigate to a scene; selected scene highlighted
- [ ] Chapter progress bar: N of M scenes selected

**Draft Tab:**
- [ ] "Generate 3 Variants" button — triggers sequential A→B→C generation
- [ ] Progress indicator per variant with temperature label
- [ ] After generation: three sub-tabs (Variant A / B / C) with rendered prose
- [ ] Word count per variant displayed
- [ ] "Proceed to Critique" button: prompts user to select which variant to critique

**Critique Tab:**
- [ ] Shows selected variant text (read-only) alongside a loading state
- [ ] "Run Critique" button — generates critique doc
- [ ] Critique output rendered in a distinct visual style (evaluation card, not prose card)
- [ ] Shows key critique dimensions: voice, pacing, continuity, canon compliance

**Revision Tab:**
- [ ] Split view: original variant (left) + critique summary (right)
- [ ] "Generate Revision" button
- [ ] Revision output rendered below
- [ ] Side-by-side diff view: original variant vs. revision (highlighted changes)

**Select Tab:**
- [ ] All available drafts shown in cards (variant A, B, C, revised)
- [ ] "Select as Final" button per card — writes `selected.md`, updates scene status
- [ ] Confirmation dialog before selection (action is significant)
- [ ] Once selected: chapter progress updates; next scene unlocks

**Chapter Assembly:**
- [ ] "Assemble Chapter" button appears in sidebar when all scenes in a chapter are selected
- [ ] Confirmation dialog
- [ ] Concatenates selected scenes in order; writes `chapter_##.md`
- [ ] Chapter status updates to assembled

**Acceptance Criteria:**
- Full pipeline (draft → critique → revise → select) completes successfully for Ch1 Sc2
- Sequential lock prevents drafting Sc2 before Sc1 is selected
- Prior scene text is included in the generation system prompt
- All generated files appear in the correct output directory with correct naming
- Chapter assembly produces a correctly ordered, correctly formatted chapter file
- Word counts are accurate
- Diff view correctly highlights changed passages

---

### Phase 4 — Manuscript Reader
*The full-book reading and annotation experience.*

**Deliverables:**

**Reader View (`pages/reader.py`):**
- [ ] Renders assembled chapters + selected scenes in reading order
- [ ] Typography optimized for reading: wider line height, slightly warmer text color, comfortable measure
- [ ] Chapter headers with decorative dividers
- [ ] Progress footer: X words written of ~Y target

**Paragraph Interaction:**
- [ ] Hover over paragraph: subtle highlight + toolbar appears (comment icon, AI prompt icon, edit icon)
- [ ] Paragraph toolbar uses smooth fade-in animation

**Viewer Comments:**
- [ ] Click comment icon → comment input appears beneath paragraph
- [ ] Submitted comments appear as styled annotation callouts below the paragraph
- [ ] All users see all comments; each shows username and timestamp
- [ ] Comments can be resolved (hidden from default view, viewable via toggle)

**AI Prompt Comments:**
- [ ] Click AI prompt icon → prompt input with a different visual treatment (electric/glowing accent)
- [ ] "Regenerate Paragraph" button — sends paragraph + surrounding context + user prompt to Ollama
- [ ] Loading state while generating
- [ ] Result shown as a diff: original vs. proposed replacement
- [ ] "Accept" writes replacement to `selected.md` and logs edit; "Discard" dismisses

**Inline Text Editing:**
- [ ] Click edit icon → paragraph becomes an editable `st.text_area`
- [ ] "Save" button writes to `selected.md`, logs to `edits` table
- [ ] "Cancel" dismisses without changes
- [ ] Visual indicator on edited paragraphs (faint golden left border)

**Acceptance Criteria:**
- Full manuscript renders correctly in reading order
- Paragraph hover toolbar appears and dismisses cleanly
- Viewer comments persist across sessions and are visible to all users
- AI prompt generates a replacement paragraph and shows a readable diff
- Accept/Discard correctly writes or discards the replacement
- Inline edits persist and appear in edit history

---

### Phase 5 — Polish & Production Readiness
*The difference between "good" and "premium."*

**Deliverables:**

**Animations & Micro-interactions:**
- [ ] Scene status badge transitions animate on update
- [ ] Generation progress uses an animated token-counter (estimated tokens generated)
- [ ] Page transitions use a subtle fade
- [ ] Toast notifications for all significant actions (generation complete, file saved, chapter assembled)
- [ ] Skeleton loaders while data is fetching

**Error Handling:**
- [ ] Ollama unreachable → clear error card with reconnect button
- [ ] Generation timeout → partial recovery (save what was received if any)
- [ ] Missing prompt file → clear explanation of which file is missing and expected path
- [ ] Database write failure → error toast with retry option
- [ ] Malformed output → raw text shown with a warning rather than crashing

**Performance:**
- [ ] Scene discovery cached with `@st.cache_data` (invalidated on file system change)
- [ ] Large prose not re-rendered unnecessarily (Streamlit reruns are scoped correctly)
- [ ] SQLite queries indexed on `scene_key`

**Multi-user Edge Cases:**
- [ ] Two users attempting to generate for the same scene simultaneously → first gets the lock, second sees a "Generation in progress by [User A]" state
- [ ] Edit conflicts: if User B saves an edit while User A is editing, User A's save warns them that content was updated

**LAN Deployment:**
- [ ] Launch script `start.bat` / `start.sh` that sets `--server.address 0.0.0.0`
- [ ] Network setup instructions in README

**Acceptance Criteria:**
- All error states show informative messages; no unhandled exceptions reach the user
- Application handles 2 simultaneous users without data corruption
- Page load time (cached) under 500ms for the scene picker
- All animations run at 60fps (no jank)
- Launch script works on Windows and macOS/Linux

---

## Milestones

| Milestone | Phase | Criteria |
|---|---|---|
| **M0: Foundation** | 0 | Repo on GitHub, docs complete |
| **M1: Data Layer** | 1 | All modules smoke-tested, no UI |
| **M2: Shell** | 2 | App launches with premium theme, settings work |
| **M3: Pipeline** | 3 | Ch1 Sc2 generated end-to-end |
| **M4: Reader** | 4 | Full manuscript readable with annotations |
| **M5: Ship** | 5 | Two users tested on LAN, all edge cases handled |

---

## Git & Release Strategy

- Commit at every meaningful milestone within a phase
- Branch per phase: `phase/1-infrastructure`, `phase/2-design-system`, etc.
- PR to `main` when a phase is complete and acceptance criteria pass
- `main` is always in a working, launchable state from Phase 2 onward
- Push to GitHub after every commit
