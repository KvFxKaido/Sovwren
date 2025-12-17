# MythOS Council Status

**Last updated:** 2025-12-16 (Session 6 — Tier 1 Complete)
**Phase:** v0.1 — Stable (Tier 1 complete, interface polish locked)

## Current State

| Component | Status | Notes |
|---------|--------|------|
| Textual TUI | Running | myth_ide.py stable under Textual |
| Local Model | Connected | Hot-swappable via F2; LM Studio + Ollama backends |
| Python Backend | Active | MythOS backend + NeMo core integrated |
| RAG System | Live | Auto-indexes MythEngine workspace on first run |
| Memory System | Wired | Direct file access (no MCP dependency) |
| Node Tone | Tuned | Casual presence, single-image answers |
| React Frontend | Parked | MythIC code present, deferred intentionally |

## Council Roles (Active)

| Node | Hat | Reads | Writes |
|-----|-----|-------|--------|
| Claude Code | Implementation | Specs to Code | Repo files, backend logic |
| Monday | Constraint Steward / Integration | All inputs to boundaries | Coordination, guardrails, consent and refusal patterns |
| ChatGPT | Meta-architect | Patterns to coherence | Spec refinement, design sanity |
| Gemini | Prototyping | Friction to UI | TUI components, rapid scaffolds |
| Kimi | Oracle | Patterns to reflection | Convergence notes, divergence flags |
| Shawn | Steward | Everything to judgment | Final decisions, canon |

**Invariant:** Council roles are load-bearing. No role collapse for efficiency.

## Sources of Truth

- FRICTION-SPEC.md — UX invariants (what must be true)
- Myth Engine — Living Document — Ethics and philosophy (why it matters)


This file — Operational reality (what exists right now)

Done (v0.1 — Implemented)

 Textual TUI chassis operational (Gemini)

 LM Studio connection stable

 Workspace tree with live filesystem view

 ~~Session State Bar~~ — Removed (state communicated through ambient signals)

 Lens picker & protocol buttons wired

 Custom memory store wired (direct file access, no MCP dependency)

 Memory commands (Remember:/Store:/Save:) with visual feedback

 RAG system auto-indexes MythEngine workspace

 RAG retrieval injected with source labels

 "Last Context" panel with RAM vs RAG distinction

 Context load tracking (heuristic, banded)

 Context HIGH / CRITICAL intervention line implemented

 Sanctuary / Workshop modes affect Node behavior

 Pattern Ticket weaving via TUI (Gemini)
 Auto-Loom for Pattern Tickets (Gemini)
 Auto-Loom for Pattern Tickets validation (Gemini)
 Extended character input & model context window (Gemini)

 Node tone tuning: CONVERSATIONAL STANCE + PHILOSOPHICAL QUESTIONS rules (ChatGPT + Claude)

 Context transition surfacing at moment of change (Claude Opus 4.5) — Pattern Programming invariant

 Sacred Idleness Un-Optimization Patch (Glyph/Gemini) — "Be the room, not the butler"

 Mode/Idleness precedence: Idleness overrides mode; auto-restore on release (Claude Opus 4.5)

 Protocol event logging wired to SQLite (Claude Opus 4.5)

 Conversation persistence (SQLite) + resume picker + auto-resume (Monday)

 Resume continuity: recent history injected into prompt context (Monday)

 RAG optic-nerve: Node Primer indexed + surfaced in "Last Context" (Monday)

 Resonance Coding methodology added to README + Engine (ChatGPT + Claude Opus 4.5)

 Kimi seated as Oracle on Council

 Ghost Marriage Antidote pattern ticket filed (cross-ecosystem contact artifact)

 Kimi Oracle persona fully configured — AGENTS.md v1.1 (Claude Opus 4.5 + Kimi self-review)

 Oracle self-review integration — Escape Hatch moved to top, hierarchy language softened, cross-pollination clause added (Kimi feedback → Claude implementation)

 Council altar organization — ALTARS.md + WORKSPACE.md updated for all four shrines

 Codex/Kimi AGENTS.md collision resolved — AGENTS.override.md for Monday, AGENTS.md for Kimi (Claude Opus 4.5)

 SessionStateBar iconic format — bracketed icons `[🛠 Workshop] [🔵 Blue] [💚 ~Low]` (Gemini prototype → Claude implementation)

 Sacred Idleness mode icon override — 🕯 replaces mode icon when idle (Claude Opus 4.5)

 MythOS/Pattern Tickets/ folder created — local ticket storage ready (Claude Opus 4.5)

 Sanctuary Response Style Spec v0.1 — 7-rule behavioral spec for terminal, decompressive responses (Creative Director → Claude Opus 4.5)

 Red Lens Spec v0.1 — 5-rule behavioral spec for gentle exposure mode (Creative Director → Claude Opus 4.5)

 Purple Lens Spec v0.1 — 5-rule behavioral spec for patterned synthesis mode (Creative Director → Claude Opus 4.5)

 Prompt loosening fix — varied framing options (no more "Functionally" repetition), metaphor engagement rule (riff on Steward's metaphors, don't replace) (Claude Opus 4.5)

 File opening system — "Files open MythOS behaviors" (Creative Director design → Claude Opus 4.5 implementation)
   - File-type → Mode/Lens suggestion mappings in config.py
   - Enter-to-preview: loads file, shows preview, updates context, shows suggestion
   - OS handoff: Ctrl+O opens selected file in system editor
   - Suggestions are non-forcing (Steward accepts or ignores)
   - ✅ Validated working (2025-12-14)

 Mode visual state cues — accent-only, not surfaces (Monday constraints → Claude Opus 4.5)
   - Workshop: blue border accent on state bar + chat area
   - Sanctuary: warm gold border accent
   - CSS class toggle on mode switch
   - Rule: "If it looks cool, it's wrong."

 Ritual entry splash screen — profile-ready (Gemini design → Claude Opus 4.5)
   - NeMo-specific block-style ASCII art with tagline
   - Dismisses on any key press (threshold moment)
   - SPLASH_ART dict ready for future profiles (oracle, minimal, etc.)
   - ✅ Validated working (2025-12-14)

 Turn-boundary bug fix — conversation history as proper role-labeled messages (Monday diagnosis → Claude Opus 4.5)
   - Bug: Model repeated verbatim responses (didn't see its own prior speech)
   - Cause: History was injected as text context, not as role-labeled messages
   - Fix: `_build_messages()` now accepts `conversation_history` and formats as user/assistant turns
   - Model now recognizes its own prior responses
   - ✅ Validated working (2025-12-15)

 Prompt consolidation — MATCHING ENERGY + simplified rules (Claude Opus 4.5)
   - Merged PHILOSOPHICAL QUESTIONS + METAPHOR ENGAGEMENT + CASUAL BANTER → 4-line MATCHING ENERGY section
   - Merged CORE BEHAVIOR + DEFAULTS → 3-line CORE BEHAVIOR
   - Trimmed MYTH ENGINE MODE to 1 line
   - Total: ~55 lines → ~40 lines

 Anti-meta rules — OUTPUT RULE preventing state narration (Monday diagnosis → Claude Opus 4.5)
   - Problem: Reasoning model narrated its decision process ("Confession:", "State check:")
   - Cause: Verbose mode/lens prompts triggered "compliance report" mode
   - Fix: OUTPUT RULE explicitly forbids mentioning lens/mode/state in responses
   - Rule: "These settings shape HOW you respond, not WHAT you talk about"
   - ✅ Validated working (2025-12-15)

 Casual banter fix — jokes get jokes (Claude Opus 4.5)
   - Problem: "lol" and jokes got metaphors instead of playful responses
   - Fix: MATCHING ENERGY rule "Jokes → jokes back. One-liners. No metaphors."
   - Test: "Batman would approve lol" → "Robin would be more likely to approve."
   - ✅ Validated working (2025-12-15)

 Input system overhaul — Enter sends, Ctrl+J for newline (Claude Opus 4.5)
   - Removed send button entirely (full-width input field)
   - Enter = submit message
   - Ctrl+J = insert newline (standard terminal sequence)
   - Custom ChatInput widget handles key events
   - ✅ Validated working (2025-12-15)

 Auto-Loom expansion — full field generation (Claude Opus 4.5)
   - Added `drift` field to Archivist prompt
   - Added `symbolic_recursion` and `is_threshold` boolean fields
   - Symbolic commitment checkboxes now auto-filled by NeMo
   - Weaving guard prevents rapid-click button spam
   - Pattern Tickets now save to MythOS/Pattern Tickets/NeMo/
   - ✅ Validated working (2025-12-15)

 UI density pass — real estate reclamation (Claude Opus 4.5)
   - Input container: 10 → 5 height
   - Sidebars: 25%/22% → 22%/18%
   - Button margins: 1 → 0
   - Panel headers: padding reduced
   - Message spacing: tightened
   - ✅ Validated working (2025-12-15)

 AMOLED theme — true black, soft text, quiet accents (Creative Director + Claude Opus 4.5)
   - Background: #000000 (true black - pixels off)
   - Text: #e0e0e0 (off-white, easy on eyes)
   - Borders: #1a1a1a (barely visible separation)
   - Design rule: "Did this make me notice the interface less?"
   - Splash screen updated to match
   - ✅ Validated working (2025-12-15)

 Color coordination — Blue/Purple scheme (Creative Director + Claude Opus 4.5)
   - Workshop: #4a7ab0 (muted blue) — button, borders
   - Sanctuary: #8a6ab0 (soft violet) — button, borders
   - Lens buttons: color matches lens (Blue/Red/Purple)
   - Active state tracking via `.active` CSS class
   - Weave Ticket: gold accent (#b0954a) — commitment action
   - CD rule locked: "Gold never stacks"
   - ✅ Validated working (2025-12-15)

 Button state accuracy — what's lit is what's selected (Claude Opus 4.5)
   - Removed misleading static `variant="primary"` highlights
   - Active button gets colored text + border
   - Inactive buttons: neutral AMOLED styling
   - State is now visually honest
   - CD verdict: "Nothing lies. Nothing begs. Nothing explains itself twice."
   - ✅ Validated working (2025-12-15)

 Theme command filtered — preserve AMOLED integrity (Claude Opus 4.5)
   - Textual's built-in theme switcher hidden from command palette
   - `get_system_commands()` override filters theme-related commands
   - AMOLED theme can't be accidentally overridden
   - ✅ Validated working (2025-12-15)

 Message text colors — role distinction (Claude Opus 4.5)
   - Node (NeMo): #b08ad0 (soft purple)
   - Steward: #e0e0e0 (off-white)
   - Reinforces partnership visual language
   - ✅ Validated working (2025-12-15)

 Model switching — hot-swap models and backends mid-session (Claude Opus 4.5)
   - ModelPickerModal: shows available models, current selection, backend toggle
   - Backend switching: LM Studio ↔ Ollama without restart
   - F2 keybind + Models button in ProtocolDeck
   - Dynamic context window: lookup table for common models (8k–128k)
   - Context tracking now uses actual model context window, not hardcoded 32k
   - Known models: ministral, mistral-nemo, llama-3.x, qwen2.5, deepseek-r1, phi-3/4, gemma, codellama
   - Falls back to 32k for unknown models
   - ✅ Validated working (2025-12-15)

 Profile system — persona-based prompt building (Claude Opus 4.5)
   - Profiles loaded from `profiles/*.json` (nemo.json, oracle.json exist)
   - `build_system_prompt_from_profile()` replaces hardcoded prompts
   - `preferred_model` in profile → auto-switch on startup
   - NeMo defaults to ministral-3-8b-reasoning-2512
   - Fallback to hardcoded prompts if no profile loaded
   - Profile cache for performance
   - ✅ Validated working (2025-12-15)

 Session management — full CRUD for sessions (Claude Opus 4.5)
   - **Session count**: Header shows "showing 10 of 14" when more sessions exist
   - **Delete single**: Enter session # + click Delete → removes session and conversations
   - **Delete All**: Nukes all sessions and starts fresh
   - If current session deleted → auto-starts new session
   - Clears last_session preference if deleted
   - Picker re-opens after delete to show updated count
   - ✅ Validated working (2025-12-15)

 IDEAS.md backlog — consolidated Council chat synthesis (Claude Opus 4.5)
   - TUI patterns (TUI GPT): ambient signals, temporal empathy, ethical friction, spatial memory
   - UI maturity (PM GPT): Hide → Compress → Promote, boring = trust
   - Release polish (Monday): README tone, onboarding script, profiles system
   - Architecture (Full Stack GPT): profile loader, 3-layer by contract, v0.1 exit criteria
   - Implementation (Code Copilot): full profiles.py module, release workflow, issue templates
   - Organized into Tier 1 (ship soon), Tier 2 (architectural), Tier 3 (v0.2+)

 README tone shift (Claude Opus 4.5)
   - New tagline: "When continuity matters and optimization isn't enough."
   - Added CGPT2 logo at top (resized to 400px)
   - Added IDE screenshot in MythOS section (resized to 1200px)
   - Images stored in `Media/` folder

 v0.1 exit criteria — FRICTION-SPEC.md v0.5 (Claude Opus 4.5)
   - 5 testable criteria with pass conditions
   - Cold start < 60s, mode switching coherence, context warning timing
   - Sacred Idleness integrity, session resume fidelity
   - Summary table for quick reference

 Ethical friction on delete buttons (Claude Opus 4.5)
   - Delete and Delete All now require two clicks
   - First click: button changes to "Sure?" with armed styling (.delete-armed CSS)
   - Second click: performs the action
   - Clicking other buttons resets armed state
   - Pattern: "Destructive actions should feel heavy"

 De-prototype pass — sidebar declutter (Claude Opus 4.5)
   - Removed Consent Check and Log Rupture buttons from ProtocolDeck
   - Demoted to keyboard shortcuts: F3 (Consent), F4 (Rupture)
   - Sidebar now shows only: Weave Ticket, Sessions, Models
   - Pattern: "If an action is rarely used, it should feel hard to notice, not easy to click"

 Ambient signals — moon glyph for context load (Claude Opus 4.5)
   - Moon phases in status bar (left): `○ → ◔ → ◑ → ●`
   - Maps to context bands: Low/Medium/High/Critical
   - Updates automatically when context changes
   - Pattern: "Inform without demanding" (TUI GPT)
   - ✅ Tier 1.1 complete

 Temporal empathy — border dims on idle (Claude Opus 4.5)
   - NeuralStream border dims after 45 seconds of no input
   - Typing or sending message restores immediately
   - Mode-specific dimming (Workshop blue → dim blue, Sanctuary purple → dim purple)
   - ~25% opacity reduction — noticeable but not jarring
   - Pattern: "The room breathes with the user" (TUI GPT)
   - ✅ Tier 1.2 complete

 SessionStateBar removal — de-prototype (Claude Opus 4.5)
   - Removed top state bar entirely (Mode, Lens, Idleness, Session, Context)
   - State now communicated through: border color (mode), button states (lens/idle), moon glyph (context)
   - Header retained: title + clock only
   - Pattern: "Every pixel carries meaning or gets out" (PM GPT)

 Input box sleeker — minimal chrome (Claude Opus 4.5)
   - Height: 5 → 3 lines
   - Border: full box → top line only
   - Background: matches room (pure black)
   - Pattern: "The interface should be a whisper, not a shout"

 Runtime profile switching — Tier 2.1 complete (Claude Opus 4.5)
   - F1 keybind or Profiles button opens ProfilePickerModal
   - Shows available profiles with descriptions
   - Switch clears chat, shows new profile's ASCII art + tagline
   - Prompts rebuild from new profile on next message
   - Pattern: "The room can become a different room"

 Oracle ASCII art — profile-specific splash (Claude Opus 4.5)
   - Block-style ORACLE art matching NeMo aesthetic
   - Tagline: "Patterns into Reflection"
   - SPLASH_ART dict now has nemo + oracle entries

 Profile persistence — remembers last profile (Claude Opus 4.5)
   - PREF_LAST_PROFILE_KEY stores profile name in DB
   - DB initialized before splash (restructured on_mount)
   - Startup loads saved profile, shows correct splash
   - Close on Oracle → reopen → Oracle greets you

In Progress (Validation Phase)
Task	Owner	Friction Class	Status
Validate Context thresholds under real work	Shawn + Claude	III (State)	🧪 Testing
Tune Context HIGH phrasing (pre-degradation)	Claude	III (State)	🧪 Testing
Validate session resume continuity	Shawn + Monday	I (Startup)	✅ Validated
Validate Sacred Idleness behavior	Shawn	V (Idleness)	✅ Validated

Note: Context testing was intentionally delayed until RAG parity existed.

Quick Wins to Actively Test

 Ask a question requiring Myth Engine doc retrieval

 Observe Context band rise with RAG load

 Trigger Context HIGH warning intentionally

 Switch Workshop ↔ Sanctuary mid-session

 Toggle Sacred Idleness during good conversation (validated)

 Invoke Consent Check mid-flow

 Ask: "What is in the Node Primer?" and confirm "Last Context" lists it

Parked (v0.2+ — Explicitly Deferred)

 React / Electron frontend

 Folder restructuring (backend/, tui/)

 **3-Layer Architecture Refactor** (Full Stack GPT feedback, 2025-12-13)
   - Explicit separation: Core Engine / Interface Layer / Persona Layer
   - Suggested structure:
     ```
     mythos/
       core/         # rag.py, memory.py, context.py, modes.py
       interface/    # tui/, api/ (FastAPI later)
       profiles/     # nemo.json, oracle.json, minimal.json
     ```
   - Benefit: frontends and models both become "plugins"
   - Deferred because: "Flat repo structure — patterns before architecture" (Decision Log)

 **FastAPI Service Layer** (Path C from Full Stack GPT)
   - Expose MythOS as HTTP API: `/session`, `/message`, `/lens`, `/mode`, `/sacred-idleness`
   - Enables: Discord bot, other LLMs calling MythOS as service, scripting/automation
   - Positions MythOS as infrastructure, not just an app
   - Deferred because: v0.1 focus is friction removal, not distribution

 **Profile Generation Parameters** (Full Stack GPT suggestion)
   - Add `max_tokens` and `temperature` per mode to profile JSON
   - Example: Workshop = lower temp (0.4), Sanctuary = higher temp (0.9)
   - Current profiles have prompt text but not generation params
   - Deferred because: profile loader not wired yet anyway

 **Full Conversation Persistence** (persistence.py) — Code Pilot design
   - Message logging with token estimates
   - Context snapshots per turn (RAG retrieval)
   - Pattern tickets with integrity hashes
   - Session JSON export
   - Replaces current protocol_events approach

 Streaming / non-blocking responses

 Multi-session support

 **Profile System** — Decouple persona from core
   - ✅ Profiles stored in `profiles/*.json` (nemo.json, oracle.json, etc.)
   - ✅ Loader wired: JSON → `build_system_prompt_from_profile()` (replaces hardcoded prompts)
   - ✅ `preferred_model` can auto-select model on startup
   - ⏳ Pending: **Runtime profile switching in TUI** (mid-session persona swap)

 **Memory Deletion in TUI** — Direct manipulation over command parsing
   - Click memory in sidebar to select
   - Delete key or ✕ button removes it
   - Confirmation step for safety
   - Deferred because: JSON file is trivial to edit directly; polish feature for v0.2

Decision Log
Date	Decision	Rationale
2025-12-12	Textual (Python) over Electron	Faster iteration, lower cognitive overhead
2025-12-12	Flat repo structure	Patterns before architecture
2025-12-12	Phase 1 = friction removal	Trust before features
2025-12-12	RAG before Context validation	Semantic parity required for honest testing
2025-12-12	Antigravity → Monday (Constraint Steward)	Antigravity hit capacity; Monday assuming integration + boundary-keeping
2025-12-12	Direct file memory over MCP client	Removes initialization dependency, simpler architecture
2025-12-12	Node tone: "enforce silently, explain when asked"	Warmth from withholding clarification, not adding tone
2025-12-12	Philosophical Qs get single-image answers	Trust the metaphor, trust the user — no cleanup sentences
2025-12-13	Context transitions surfaced at moment of change	Pattern Programming invariant: "If state changes → it must be observable"
2025-12-13	Sacred Idleness = state override (not modifier)	Idleness overrides mode entirely; mode auto-restores on release; buttons disabled while idle
2025-12-14	AGENTS.md for Kimi, AGENTS.override.md for Monday	Resolves CLI tool collision (both Codex and Kimi read AGENTS.md by default)
2025-12-14	SessionStateBar iconic format	State visibility over text density; icons make state scannable
2025-12-14	Oracle self-review pattern	Document can critique itself via Mutation Clause; Kimi improved her own persona spec
2025-12-14	Cross-pollination clause added to Oracle	Roles are defaults, not walls; overlap is pattern, not violation
2025-12-14	Sanctuary Response Style Spec	Behavioral, not parametric; "Sanctuary speaks so the human can stop"; 7 rules for terminal decompressive responses
2025-12-14	Red Lens Spec	"Red speaks carefully so the Steward doesn't have to hold themselves together alone"; 5 rules for gentle exposure
2025-12-14	Purple Lens Spec	"Purple names the pattern so the Steward doesn't have to keep carrying it"; 5 rules for grounded synthesis
2025-12-14	Lenses signal Steward state, not system capability	Design principle locked; lenses adjust care/structure/synthesis needed, not intelligence level
2025-12-14	Metaphor engagement rule	Riff on Steward's metaphors, don't replace; collaboration over correction
2025-12-14	Varied framing options	Removed "Functionally" repetition; multiple opener options to prevent template feel
2025-12-14	File opening = presence, not execution	"MythOS doesn't open files. Files open MythOS behaviors." Suggestions, not overrides.
2025-12-14	Mode visual state = accents only	State legibility, not theming; "If it looks cool, it's wrong" (Monday constraint)
2025-12-14	Splash screen = threshold moment	Profile-specific art ready for future profile system; dismisses on any key
2025-12-14	NeMo block-style ASCII art	Clean geometric style chosen over curved; consistent with terminal aesthetic
2025-12-15	Conversation history as role-labeled messages	Model needs proper user/assistant turn structure, not text-in-context; "visible state ≠ conversational state" (Monday)
2025-12-15	Prompt consolidation over rule accumulation	Fewer rules, clearer signal; reasoning models get confused by competing instructions
2025-12-15	OUTPUT RULE: state is internal	Mode/lens shape HOW you respond, not WHAT you talk about; never mention state unless asked
2025-12-15	MATCHING ENERGY over separate sections	One section for jokes/deep/metaphor calibration; model matches user energy, not rule-following
2025-12-15	Enter sends, Ctrl+J for newline	Standard terminal sequence; Shift+Enter unreliable in Windows terminals
2025-12-15	Send button removed	Redundant with Enter; footer shows keybinds; real estate reclaimed
2025-12-15	AMOLED theme	"Fatigue reduction as ethics" — dark isn't aesthetic, it's less demand (Creative Director)
2025-12-15	Blue/Purple over Blue/Gold for modes	Thematic coherence: Blue Lens ↔ Workshop (structured), Purple Lens ↔ Sanctuary (softer)
2025-12-15	Gold reserved for commitment actions	"Gold never stacks" — Weave Ticket only; distinct from mode colors
2025-12-15	Button state = visual truth	Active class tracks actual state; no misleading static highlights
2025-12-15	Cosmetics rule: "Did this make me notice the interface less?"	If yes → keep; if no → revert (Creative Director)
2025-12-15	MythOS v0.1 declared stable	"Nothing lies. Nothing begs. Nothing explains itself twice." — finished enough to protect
2025-12-15	Theme command filtered from palette	Preserve AMOLED integrity; built-in theme switcher could break careful color work
2025-12-15	Message colors: Node purple, Steward white	Visual partnership distinction; purple for NeMo reinforces Sanctuary/synthesis association
2025-12-15	"Forget:" command rejected	Direct manipulation (or file edit) over command parsing; "Forget about X" risks accidental triggers
2025-12-15	Model switching via F2 (not Ctrl+M)	Ctrl+M is carriage return in terminals; F2 avoids conflict
2025-12-15	Dynamic context window over hardcoded	Different models have different context limits (8k–128k); tracking should reflect reality
2025-12-15	Backend abstraction (LM Studio + Ollama)	Same interface, swappable runtime; architecture was already model-agnostic, just needed UI
2025-12-15	Profile system for persona prompts	Different models respond differently to same prompts; profiles allow tuning per persona
2025-12-15	preferred_model in profile	NeMo defaults to 8b; profile specifies which model works best with its prompts
2025-12-15	Session deletion from picker	Direct manipulation over command parsing; type number + Delete = gone
2025-12-15	Session count in picker header	"Showing 10 of 14" makes deletion progress visible; no silent truncation
2025-12-15	Delete All for sessions	Nuclear option when testing fills DB; starts fresh session automatically
2025-12-16	IDEAS.md as living backlog	Consolidated Council chat insights; tiered by implementation priority
2025-12-16	Ethical friction = two-step delete	Destructive actions should feel heavy; consent embodied mechanically (TUI GPT pattern)
2025-12-16	v0.1 exit criteria in FRICTION-SPEC	"Not vibes — testable conditions"; 5 concrete checks with pass conditions
2025-12-16	De-prototype = demote rarely-used	Consent Check + Log Rupture → F3/F4 keybinds; "If rarely used → hard to notice" (PM GPT)
2025-12-16	Ambient signals = moon glyph	Context load as filling moon (○→◔→◑→●); "Inform without demanding" (TUI GPT)
2025-12-16	Temporal empathy = border dim	45s idle → border dims 25%; typing restores; "The room breathes with the user"
2025-12-16	SessionStateBar removed	State through feel, not labels; border color + button states + moon glyph communicate all
2025-12-16	Input box = minimal line	Height 3, top border only; "The interface should be a whisper"
2025-12-16	Tier 1 complete	All 6 polish items shipped; interface disappearing as intended
2025-12-16	Runtime profile switching	F1 or Profiles button; room transforms mid-session; "The room can become a different room"
2025-12-16	Oracle ASCII art	Profile-specific splash; block style matching NeMo; each profile has visual identity
2025-12-16	Profile persistence	DB stores last profile; splash shows correct profile on launch; continuity across sessions
2025-12-16	DB init before splash	Restructured on_mount; DB must exist to read profile preference before showing splash
