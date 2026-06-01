# Design System

## Design Language

**Gothic Scholarly** — The Scriptorium should feel like a premium digital atelier for serious fiction: the weight and texture of an illuminated manuscript, the precision of a well-designed editorial tool. Dark, intentional, with moments of warmth and gold. Not horror, not minimalism — *literary*.

### Principles

1. **Atmosphere over chrome** — The UI recedes so the prose can breathe. Navigation and controls are present but quiet.
2. **Intentional hierarchy** — Every element has a clear visual weight. Nothing competes with the content.
3. **Earned feedback** — Interactions reward the user with satisfying, subtle responses. Nothing is abrupt.
4. **Readable first** — Body text optimized for reading long-form prose. Every typographic decision serves comprehension.
5. **Consistent depth** — Cards and panels use layered backgrounds (not drop shadows) to suggest depth without noise.

---

## Color Palette

### Base

| Token | Hex | Usage |
|---|---|---|
| `--color-bg-base` | `#0D0B14` | Page background — near-black with purple undertone |
| `--color-bg-surface` | `#151220` | Primary cards, panels |
| `--color-bg-elevated` | `#1E1A2E` | Modals, popovers, active sidebar items |
| `--color-bg-inset` | `#0A0812` | Text areas, code blocks, inset wells |

### Text

| Token | Hex | Usage |
|---|---|---|
| `--color-text-primary` | `#EDE8DF` | Body prose, primary labels — aged parchment |
| `--color-text-secondary` | `#8A7F9A` | Metadata, timestamps, secondary labels |
| `--color-text-muted` | `#4A4458` | Disabled states, placeholder text |
| `--color-text-inverse` | `#0D0B14` | Text on gold/light backgrounds |

### Accent — Gold

| Token | Hex | Usage |
|---|---|---|
| `--color-gold-primary` | `#C9A84C` | Primary actions, selected states, active highlights |
| `--color-gold-muted` | `#8A6E2A` | Hover states, secondary gold |
| `--color-gold-subtle` | `#2A2010` | Gold-tinted backgrounds, left-border accents |

### Accent — Rose

| Token | Hex | Usage |
|---|---|---|
| `--color-rose-primary` | `#9B4D6B` | AI prompt actions, revision indicators |
| `--color-rose-muted` | `#6B3349` | Hover on rose elements |
| `--color-rose-subtle` | `#200D14` | Rose-tinted backgrounds |

### Status

| Token | Hex | Usage |
|---|---|---|
| `--color-status-locked` | `#3A3550` | Locked/unavailable state |
| `--color-status-needs` | `#4A6B8A` | Needs action (draft/critique ready) |
| `--color-status-progress` | `#6B5E2A` | In-progress state |
| `--color-status-complete` | `#2A5C42` | Selected/assembled/complete |
| `--color-status-error` | `#6B2A35` | Error states |

### Borders & Dividers

| Token | Hex | Usage |
|---|---|---|
| `--color-border-subtle` | `#1E1A2E` | Between surface elements |
| `--color-border-medium` | `#2E2A40` | Card borders, panel edges |
| `--color-border-strong` | `#4A4458` | Focused inputs, emphasized dividers |

---

## Typography

### Font Families

```css
/* Display & prose body */
--font-display: 'Cormorant Garamond', 'Georgia', serif;

/* UI chrome: labels, buttons, badges, metadata */
--font-ui: 'Inter', 'Segoe UI', system-ui, sans-serif;

/* Code and raw text blocks */
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

Loaded via Google Fonts:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### Type Scale

| Token | Size | Weight | Family | Usage |
|---|---|---|---|---|
| `--text-display-xl` | 2.25rem | 300 | Display | Page titles, chapter headings |
| `--text-display-lg` | 1.75rem | 400 | Display | Section headings, scene titles |
| `--text-display-md` | 1.375rem | 500 | Display | Card headings, panel titles |
| `--text-prose-lg` | 1.125rem | 400 | Display | Primary prose body (reader view) |
| `--text-prose-md` | 1rem | 400 | Display | Secondary prose, draft previews |
| `--text-ui-md` | 0.875rem | 400 | UI | Standard UI labels |
| `--text-ui-sm` | 0.75rem | 500 | UI | Badges, metadata, timestamps |
| `--text-ui-xs` | 0.6875rem | 500 | UI | Fine-print labels |

### Prose Typography (Reader View)

```css
.prose-body {
  font-family: var(--font-display);
  font-size: var(--text-prose-lg);
  line-height: 1.85;
  letter-spacing: 0.01em;
  color: var(--color-text-primary);
  max-width: 68ch;          /* Optimal reading measure */
  margin: 0 auto;
}
```

---

## Spacing Scale

Based on a 4px base unit:

| Token | Value | Usage |
|---|---|---|
| `--space-1` | 4px | Tight internal padding |
| `--space-2` | 8px | Compact elements, badge padding |
| `--space-3` | 12px | Small component padding |
| `--space-4` | 16px | Standard component padding |
| `--space-5` | 24px | Card padding, section gaps |
| `--space-6` | 32px | Large section spacing |
| `--space-7` | 48px | Page section dividers |
| `--space-8` | 64px | Major page sections |

---

## Components

### Scene Status Badge

A pill-shaped label communicating the current pipeline stage of a scene.

```
Visual spec:
  Shape:       pill (border-radius: 999px)
  Padding:     4px 10px
  Font:        UI SM, weight 500, uppercase, letter-spacing 0.08em
  Border:      1px solid (matching status color at 60% opacity)
  Background:  status color at 12% opacity

Status map:
  locked        → icon: 🔒  color: --color-status-locked    label: LOCKED
  needs_draft   → icon: ✦   color: --color-status-needs     label: NEEDS DRAFT
  has_variants  → icon: ◈   color: --color-status-progress  label: VARIANTS READY
  in_critique   → icon: ◎   color: --color-status-progress  label: CRITIQUING
  has_critique  → icon: ◉   color: --color-status-progress  label: CRITIQUE DONE
  has_revision  → icon: ◈   color: --color-status-progress  label: REVISED
  selected      → icon: ✓   color: --color-status-complete  label: SELECTED
  assembled     → icon: ◆   color: --color-status-complete  label: ASSEMBLED
```

### Prose Card

Container for displaying generated scene content.

```
Visual spec:
  Background:    --color-bg-surface
  Border:        1px solid --color-border-medium
  Border-radius: 8px
  Padding:       --space-5
  
  Header:
    Font:          UI SM, uppercase, letter-spacing 0.1em
    Color:         --color-text-secondary
    Border-bottom: 1px solid --color-border-subtle
    Padding-bottom: --space-3
    Margin-bottom:  --space-4
  
  Body:
    Font:          Display MD, line-height 1.7
    Color:         --color-text-primary
  
  Footer:
    Font:          UI XS
    Color:         --color-text-muted
    Margin-top:    --space-3
    Content:       Word count, temperature, generation timestamp
```

### Variant Tab Bar

Three-tab selector for Draft variants A / B / C.

```
Visual spec:
  Container:     Horizontal flex, border-bottom: 1px solid --color-border-subtle
  
  Tab (inactive):
    Font:        UI MD, weight 500
    Color:       --color-text-secondary
    Padding:     --space-3 --space-5
    Border-bottom: 2px solid transparent
    Transition:  all 150ms ease
  
  Tab (active):
    Color:       --color-gold-primary
    Border-bottom: 2px solid --color-gold-primary
  
  Tab (hover):
    Color:       --color-text-primary
    Border-bottom: 2px solid --color-border-strong
  
  Temperature label:
    Font:        UI XS
    Color:       --color-text-muted
    Content:     "temp 0.70" / "temp 0.85" / "temp 1.00"
```

### Chapter Progress Bar

Thin progress indicator showing scene completion within a chapter.

```
Visual spec:
  Height:     3px
  Background: --color-border-subtle
  Fill:       Linear gradient from --color-gold-muted to --color-gold-primary
  Segments:   One segment per scene; gap of 2px between segments
  Animation:  Fill slides in from left (500ms ease) on status change
```

### Diff View

Side-by-side comparison of original vs. revised text for revision and paragraph regeneration.

```
Visual spec:
  Layout:       Two columns, equal width, gap: --space-4
  
  Column header:
    Font:       UI SM, uppercase, letter-spacing 0.08em
    Left:       "ORIGINAL" in --color-text-secondary
    Right:      "REVISION" in --color-gold-primary
  
  Removed text (left column):  background: rgba(139, 40, 40, 0.15), text: #C87070
  Added text (right column):   background: rgba(40, 100, 60, 0.15), text: #70C894
  Unchanged text:              normal prose card styling
  
  Diff granularity: sentence-level (split on ". " within paragraphs)
```

### Comment Annotation

Displayed beneath a paragraph when viewer comments exist.

```
Visual spec:
  Container:
    Border-left: 3px solid --color-border-medium
    Padding-left: --space-4
    Margin-top:   --space-2
    Background:   --color-bg-inset
    Border-radius: 0 6px 6px 0
  
  Header:
    Username:    UI SM weight 600, --color-text-primary
    Timestamp:   UI XS, --color-text-muted
    Spacing:     Flex row, space-between
  
  Body:
    Font:        UI MD, --color-text-secondary, line-height 1.6
  
  AI Prompt variant:
    Border-left: 3px solid --color-rose-primary
    Username:    rose color tint
    Small "AI PROMPT" badge in header
```

### Paragraph Toolbar

Appears on paragraph hover in the reader view.

```
Visual spec:
  Position:    Absolute, top-right of paragraph container
  Background:  --color-bg-elevated
  Border:      1px solid --color-border-medium
  Border-radius: 6px
  Padding:     --space-2
  Gap:         --space-2
  
  Appear:      Fade in, 150ms ease
  Disappear:   Fade out, 100ms ease
  
  Buttons:     Icon-only, 28x28px, border-radius 4px
               Hover: --color-bg-surface background
  
  Icons:
    Comment:   Speech bubble (viewer comment)
    AI Prompt: Sparkle/wand (AI prompt)
    Edit:      Pencil (inline edit)
```

### Action Buttons

Primary, secondary, and destructive button variants.

```
Primary (gold):
  Background:   --color-gold-primary
  Text:         --color-text-inverse (dark)
  Font:         UI MD, weight 600
  Padding:      10px 20px
  Border-radius: 6px
  Hover:        background --color-gold-muted, translateY(-1px)
  Transition:   all 150ms ease

Secondary:
  Background:   transparent
  Border:       1px solid --color-border-medium
  Text:         --color-text-primary
  Hover:        background --color-bg-elevated
  
Destructive:
  Background:   transparent
  Border:       1px solid --color-status-error
  Text:         #C87070
  Hover:        background rgba(107, 42, 53, 0.2)

AI Action (rose):
  Background:   --color-rose-primary
  Text:         --color-text-primary
  Hover:        background --color-rose-muted
```

### Generation Progress Indicator

Shown during Ollama generation (which can take several minutes).

```
Visual spec:
  Container:   Full-width card, centered content
  
  Spinner:     Custom CSS ring animation (not Streamlit default)
               Color: --color-gold-primary
               Size:  48px
  
  Label:       "Generating Variant A..."
               Font: Display MD
               Color: --color-text-primary
  
  Sub-label:   "Temperature 0.70 · Model: [model name]"
               Font: UI SM
               Color: --color-text-secondary
  
  Animation:   Subtle pulse on the card background (opacity 0.8 ↔ 1.0, 2s ease infinite)
```

---

## Animation Specification

All animations use CSS transitions or keyframe animations. No JavaScript animation libraries.

| Interaction | Property | Duration | Easing |
|---|---|---|---|
| Button hover | transform, background | 150ms | ease |
| Tab switch | border-color, color | 150ms | ease |
| Badge appear | opacity, transform (scale) | 200ms | ease-out |
| Page content appear | opacity | 250ms | ease |
| Paragraph toolbar show | opacity | 150ms | ease |
| Paragraph toolbar hide | opacity | 100ms | ease |
| Status badge update | background, border-color | 300ms | ease |
| Progress bar fill | width | 500ms | ease |
| Card hover | box-shadow | 200ms | ease |
| Generation pulse | opacity | 2000ms | ease infinite |
| Toast appear | opacity, transform (Y) | 250ms | ease-out |
| Toast dismiss | opacity | 200ms | ease |

---

## Streamlit CSS Injection Strategy

Streamlit's theming system is insufficient for this level of visual quality. We override it entirely using CSS injected via `st.markdown(..., unsafe_allow_html=True)`.

### Approach

1. `styles/theme.py` exports a `GLOBAL_CSS` string constant containing all CSS custom properties and base overrides
2. `styles/components.py` exports functions that return styled HTML strings, injected via `st.markdown`
3. `app.py` calls `inject_global_styles()` at the top of every page load (Streamlit re-runs on every interaction)
4. Streamlit's default styles are overridden at the `.stApp`, `.stSidebar`, `.stButton`, `.stTextInput`, etc. level

### Sidebar Override

```css
/* Hide Streamlit's default decoration */
[data-testid="stSidebar"] {
  background-color: var(--color-bg-surface);
  border-right: 1px solid var(--color-border-subtle);
}

/* Remove Streamlit's page nav default styles */
[data-testid="stSidebarNavItems"] { display: none; }
```

### Font Injection

Fonts are loaded in the GLOBAL_CSS injection via `@import` — Streamlit does not provide a `<head>` hook, so we use the CSS `@import` rule within the injected `<style>` block.

### Prose Rendering

Scene content is rendered as HTML via `st.markdown(..., unsafe_allow_html=True)` wrapped in a styled `<div class="prose-card">` container, rather than raw Streamlit markdown. This allows precise typographic control.

---

## Accessibility

- Color is never used as the *only* signal — status badges combine color + text label + icon
- Interactive elements have visible focus states (`outline: 2px solid --color-gold-primary`)
- Minimum contrast ratio 4.5:1 for all body text against backgrounds
- Paragraph toolbar icons include `title` attributes for screen reader support
