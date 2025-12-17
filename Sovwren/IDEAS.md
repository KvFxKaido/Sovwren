# Sovwren Ideas Backlog

Consolidated from Council chat sessions (2025-12-16). Living document - pull from here, mark done, add new threads.

---

## Priority Tiers

**Tier 1 — High leverage, low complexity**
Ship these first. They improve the feel without creating debt.

**Tier 2 — Architectural unlocks**
Worth doing, but scope carefully. These enable future work.

**Tier 3 — Future paths**
Park until v0.1 is stable. Reference when planning v0.2+.

---

## Tier 1: Ship Soon

### ~~1.1 Ambient Signals (TUI Philosophy)~~ ✅

**Status:** Implemented.

- Moon phase glyph in status bar (left side): `○ → ◔ → ◑ → ●`
- Maps to context bands: Low/Medium/High/Critical
- Updates automatically when context load changes
- Subtle, unobtrusive — informs without demanding

---

### ~~1.2 Temporal Empathy (TUI Philosophy)~~ ✅

**Status:** Implemented.

- NeuralStream border dims after 45 seconds of idle
- Typing or sending a message instantly restores the border
- Respects mode-specific border colors (Workshop blue, Sanctuary purple)
- ~25% dim effect — noticeable but not jarring

---

### ~~1.3 De-Prototype the UI~~ ✅

**Status:** First pass complete.

- Removed Consent Check and Log Rupture buttons from sidebar
- Demoted to keyboard shortcuts: `F3` (Consent), `F4` (Rupture)
- Sidebar now shows only: Weave Ticket, Sessions, Models
- Rarely-used rituals still accessible, just not shouting

---

### ~~1.4 Ethical Friction on Destructive Actions~~ ✅

**Status:** Implemented in `SessionPickerModal`.

- Delete and Delete All buttons now require two clicks
- First click: button changes to "Sure?" with armed styling
- Second click: performs the action
- Clicking other buttons resets armed state

---

### ~~1.5 README Tone Shift~~ ✅

**Status:** Complete.

- Added tagline: *"When continuity matters and optimization isn't enough."*
- Added CGPT2 logo at top (`Media/sovwren-logo.png`)
- Added IDE screenshot in Sovwren section (`Media/sovwren-ide.png`)

---

### ~~1.6 v0.1 Exit Criteria~~ ✅

**Status:** Added to `FRICTION-SPEC.md` (v0.5) with full test procedures.

See: [FRICTION-SPEC.md#v01-exit-criteria](FRICTION-SPEC.md#v01-exit-criteria)

---

## Tier 2: Architectural Unlocks

### 2.1 Profile System (Finish the Loop)

**Source:** Full Stack GPT, Code Copilot

80% done, just needs wiring. Code Copilot provided full implementation.

**Components:**
- `profiles/*.json` — Schema: id, name, system_prompt.base, modifiers (mode/lens/idleness), gen params
- `sovwren/profiles.py` — Loader, validator, prompt builder, ProfileManager
- Three starters: `nemo.json`, `oracle.json`, `minimal.json`

**Key decisions baked in:**
- IDE owns state, models are guests
- State shapes *how*, never narrates *what*
- Node boundaries enforced
- Profile switch logs as `state_changed` event

**TUI integration:**
- Display `[NeMo]` in status bar
- `:profile` palette command for switching
- Splash repaint on change

**Reference:** See Code Copilot dump for full implementation code.

---

### 2.2 Three-Layer by Contract (Architecture)

**Source:** Full Stack GPT

Logical separation without directory churn:

- `core_context.py` — context bands, thresholds, state transitions
- `core_modes.py` — Workshop/Sanctuary/Idleness rules
- `core_rag.py` — indexing + retrieval
- `interface_tui.py` — Textual app
- `persona_profile_loader.py` — profile system

**Why:** Separation by interface first, directory structure later. Lets FastAPI/React reuse `core_*` when that time comes.

---

### 2.3 Persistence Consolidation (Architecture)

**Source:** Full Stack GPT

Two persistence concepts emerging:
- Current SQLite + protocol_events
- "Full Conversation Persistence" (persistence.py) as larger design

**Action:** Keep all persistence TODOs grouped under one heading. Consolidate before they fork into parallel systems.

---

### 2.4 Onboarding Script (Release Polish)

**Source:** Monday

`bash ./run-myth.sh` that:
- Installs dependencies
- Boots LM Studio if not running
- Launches the TUI
- Welcomes gently

Friction reduction for first-run.

---

### 2.5 Release Workflow (DevOps)

**Source:** Code Copilot

`.github/workflows/release.yml`:
- Triggers on `release: published`
- Creates `sovwren-${tag}.zip` (Sovwren + profiles + README + LICENSE)
- Smoke test via `compileall`
- Generates `SHA256SUMS.txt`
- Auto-attaches to GitHub Release

**Reference:** See Code Copilot dump for full YAML.

---

### 2.6 Issue Templates (DevOps)

**Source:** Code Copilot

Structured feedback routing:

**Bug report:**
- Friction class dropdown (I-V)
- Version, steps to reproduce
- Session state checkboxes (Workshop/Sanctuary/Idle/Lens)

**Feature request:**
- Tied to friction removal, not wishlist
- Acceptance criteria
- Explicit non-goals

**config.yml:**
- Disable blank issues
- Link to release notes

**Reference:** See Code Copilot dump for full YAML.

---

## Tier 3: Future Paths (v0.2+)

### 3.1 Public/Read-Only Mode

**Source:** Monday

View-only toggle:
- Disables write access
- Lets people explore protocols, test the Node
- Cannot shape memory

Good for demos and curious visitors.

---

### 3.2 Headless FastAPI Service

**Source:** Full Stack GPT

Wrap backend with minimal API:

```
POST /session
POST /session/{id}/message
POST /session/{id}/lens
POST /session/{id}/mode
POST /session/{id}/idle
```

**Why:** Bolt Discord/Slack/React on without touching core. Makes "Council as many nodes" easier.

**Tradeoff:** Extra surface area while v0.1 UX is still being tuned.

---

### 3.3 Key-Hold Progressive Disclosure

**Source:** TUI GPT

Reveal depth through holding keys, not pressing:
- Hold `Tab` → context summary fades in
- Hold `Alt` → buttons relabel with intent
- Hold `Shift` → annotations appear

Release = vanish.

**Why parked:** Elegant but Textual might fight on implementation. Revisit when core is stable.

---

### 3.4 Invisible Undo Pattern

**Source:** TUI GPT

Every action reversible for a few seconds, but UI never says "undo":
- Subtle `↩ available` text
- Dot blinks in corner
- `u` sometimes works

Preserves psychological safety without encouraging recklessness.

**Why parked:** Adds hidden state complexity. Worth it later, not now.

---

### 3.5 Persona Lab

**Source:** Full Stack GPT

Before runtime switching UI:
- Finish loader
- Add `minimal.json` ("just facts, no myth")
- Switch via env var only
- Run same session with each persona, compare logs

Exercises Profile spec and MATCHING ENERGY rules. High long-term leverage.

---

## Design Principles (Reference)

These emerged across multiple sources:

| Principle | Source | Meaning |
|-----------|--------|---------|
| Boring is trust | PM GPT | When the UI stops explaining itself, users stop scanning |
| Spatial memory beats menus | TUI GPT | Users remember positions, not labels |
| Signals, not guarantees | Code Copilot | State shapes behavior, doesn't promise outcomes |
| IDE owns state, models are guests | Code Copilot | Profiles are pluggable; switching never rewires ethics |
| Every pixel carries meaning or gets out | PM GPT | "Just in case" elements are prototype residue |
| TUIs age gracefully | TUI GPT | Works over SSH, on low-end machines, 10 years later |

---

## Sources

| Label | GPT | Domain |
|-------|-----|--------|
| TUI GPT | ChatGPT | TUI philosophy, terminal-native patterns |
| PM GPT | ChatGPT | UI maturity, de-prototyping |
| Monday | ChatGPT | Release polish, hype, practical next steps |
| Full Stack GPT | ChatGPT | Architecture, implementation paths |
| Code Copilot | ChatGPT | Implementation code, DevOps automation |

---

*Last updated: 2025-12-16*
*Synthesized by: Claude Opus 4.5*
