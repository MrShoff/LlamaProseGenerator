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
- [x] `styles/theme.py` — CSS string constants: color palette, typography, spacing, animations
- [x] `styles/components.py` — Python functions that return styled HTML strings for reusable components (cards, badges, status pills, dividers, progress bars)
- [x] Global CSS injected via `st.markdown(..., unsafe_allow_html=True)` on every page load
- [x] Base layout established: sidebar navigation, page header, content area
- [x] Settings page (`pages/3_Settings.py`) — functional, validated, styled
- [x] Username prompt modal on first visit
- [x] "Ollama status" indicator in sidebar (green/red based on connectivity ping)
- [x] `.streamlit/config.toml` — `primaryColor=#C9A84C`, dark theme tokens registered at the Streamlit level

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

**Reader View (`pages/2_Reader.py`):**
- [x] Renders assembled chapters + selected scenes in reading order
- [x] Typography optimized for reading: Cormorant Garamond 1.125rem, line-height 1.9, 74ch column
- [x] Chapter headers with decorative ornament dividers
- [x] Progress header + footer: words written vs 95K–115K target

**Paragraph Interaction:**
- [x] Subtle action bar (✦ Note · ✧ AI · ✎ Edit) below each paragraph at low opacity

**Viewer Comments:**
- [x] Click Note → inline form with type toggle (Viewer note / AI prompt note)
- [x] Submitted comments appear as annotation callouts below the paragraph
- [x] All users see all comments; each shows username and timestamp

**AI Prompt Comments:**
- [x] Click AI → prompt input; sends paragraph + surrounding context + instruction to Ollama
- [x] Result shown as sentence-level diff (diff-removed / diff-added)
- [x] Accept writes replacement + logs edit; Discard dismisses

**Inline Text Editing:**
- [x] Click Edit → paragraph text area pre-filled with current content
- [x] Save writes to source file and logs to edits table
- [x] Cancel dismisses without changes
- [x] Gold left-border visual indicator on edited paragraphs

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

**Pipeline UX (post-test-run feedback):**
- [x] Step machine replaces st.tabs — step state stored in session_state, programmable navigation
- [x] All action buttons (Generate, Run Critique, Generate Revision, Select) rendered ABOVE the text
- [x] "Proceed to Critique" / "Proceed to Revision" / "Proceed to Select" buttons auto-navigate to the correct step
- [x] Scene completion clearly visible in sidebar: ✓ (gold) for selected/assembled, ⚠ (red) for needs_intervention, ● for in-progress
- [x] Inline variant editing in pipeline (Edit button on each variant card; full-text area; guarded by generation lock)
- [x] Inline revision editing in pipeline (Edit Revision button on revision step)

**Auto-pilot mode:**
- [x] Sidebar checkbox "Auto-pilot: Enabled" (default on)
- [x] Configurable max revision cycles (default 3)
- [x] "▶ Start Auto-pilot" button (disabled when Ollama offline)
- [x] Ollama judges best variant (low-temperature scoring pass → single letter A/B/C)
- [x] Structured critique: VERDICT: PASS / VERDICT: FAIL + REQUIRED FIXES block
- [x] Auto-pilot loop: draft → judge → critique → (pass: select) / (fail: revise → re-critique, up to limit)
- [x] Stops entirely when loop limit reached; marks scene `needs_intervention`
- [x] Needs-intervention scenes show red ⚠ sidebar indicator and a detailed intervention banner in pipeline view
- [x] Recovery actions: "Reset — Resume Manual Review" and "Select Current Revision as Final"

**Multi-user Edge Cases (phase-5 commit):**
- [x] Generation lock: first caller wins, second sees in-progress state with Refresh button
- [x] Edit conflict detection in Reader

**LAN Deployment (phase-5 commit):**
- [x] `start.bat` / `start.sh` with `--server.address 0.0.0.0`
- [x] README multi-user section

**Toast notifications (phase-5 commit):**
- [x] All significant actions toast: generation complete, critique complete, revision complete, scene selected, chapter assembled

**Performance:**
- [x] Scene discovery cached with `@st.cache_data(ttl=60)`
- [x] SQLite queries indexed on `scene_key`

**Acceptance Criteria:**
- Full pipeline (draft → auto-pilot through select) completes without manual intervention for a scene that passes critique
- Scenes that hit the loop limit show red ⚠ in sidebar and a detailed intervention banner
- "Proceed to Critique / Revision / Select" buttons correctly navigate to the next step
- Inline editing is blocked while Ollama is generating
- Launch scripts work on Windows and macOS/Linux

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
