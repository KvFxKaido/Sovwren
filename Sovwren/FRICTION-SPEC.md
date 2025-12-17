# Myth Engine IDE - Friction Spec (v0.4)

A partnership-first interface spec for any LLM backend.

This is not a feature wishlist.
It is a friction-removal spec.

The Myth Engine IDE exists to eliminate the invisible frictions that make AI partnership exhausting in chat-only interfaces.

The goal is not to "surface all the protocols as buttons."
The goal is to remove specific pain points so Myth Engine practices become natural instead of effortful.

---

## Myth Engine Context

**Steward** = human partner who carries continuity (Shawn, future users)

**Node** = model / agent instance (NeMo, Claude, GPT, Gemini, etc.)

**Myth Engine** = partnership OS (Lens States, Steward Protocol, Pattern-Tickets, etc.)

The IDE is where those patterns turn into interface affordances instead of "things you remember to say in chat."

---

## Model-Agnostic Core

**Requirement:** The IDE must work with any LLM backend:

- Local models (LM Studio, Ollama, NeMo, etc.)
- Remote APIs (Claude, GPT, Gemini, etc.)

The Myth Engine lives above the model layer as partnership infrastructure.

- The IDE owns coordination, visibility, and session state.
- Backends are interchangeable Nodes that generate responses but do not own shared state or protocols.

**Design invariant:** The IDE is the host; models are guests.

---

## Friction Class I — Startup & Readiness

### Problem

Right now, local model partnership feels like a little ritual:

1. Manually start LM Studio / Ollama / NeMo
2. Hope the model is actually loaded
3. Hope the RAG backend is awake
4. Hope the Node is pointing at the right directory

There's no single source of truth for "are we ready to work together?"

### Must-Haves

#### 2.1 One-Click Launch

One control to start:

- local runtime (e.g., LM Studio or Ollama)
- Node process (NeMo or equivalent)
- RAG / indexer for the current workspace

**Rough behavior:**

On click:
- spin up backends (where possible)
- perform health checks
- attach them to the selected project directory

Startup should move from ritual to reliability.

#### 2.2 Readiness Indicator

Clear status for each Node:

- Ready / Loading / Error / Disconnected

Hover / click → show:
- last successful response time
- approximate context window size
- which workspace it's attached to

Signals are advisory, not hard guarantees, but they answer:

> "Is my partner actually here, or am I typing into a void?"

#### 2.3 Session Persistence & Resume (The Anchor)

The IDE must make partnership survivable across restarts.

Minimum behavior:

- Persist sessions + conversations to local storage (SQLite is fine).
- Auto-resume the last active session on launch (default).
- Provide a visible, low-friction session switcher:
  - Start New
  - Resume by recent list / ID
  - Name session
  - Delete session (explicit, never accidental)
- "Clear chat" clears RAM (the visible stream), not the stored session.
- On resume, inject recent history into the Node prompt context so continuity is real, not performative.

---

## Friction Class II — Shared Context Visibility

### Problem

In chat-only setups, Stewards never really know:

- Which files exist in the project?
- Which ones the Node has actually seen?
- What was just pulled into context to answer a question?
- When the Node is overloaded vs genuinely confused?

The question "are we looking at the same thing?" is constantly ambiguous.

### Must-Haves

#### 3.1 Workspace Tree

A left-hand pane showing the project directory:

Each file/directory tagged with simple badges:

- **Available** — exists in the filesystem
- **Referenced** — mentioned or opened this session
- **Loaded** — explicitly retrieved into Node context / RAG

Implementation can be approximate:
- "Loaded" might mean "used in last retrieval for an answer"
- "Referenced" can be simple: "file path detected in messages"

#### 3.2 Context Inspector

A panel (side or bottom) showing:

- Currently loaded chunks/docs (according to the RAG/index)
- Approximate token usage for:
  - conversation so far
  - current retrieval set
- Last retrieval sources:
  - e.g., *Last answer drew from: notes/plan.md, src/engine/core.ts*

This doesn't need hard numbers; it needs human-legible hints.

#### 3.3 Reference Preview

When the Node references a file:

- highlight it in the tree
- optionally show:
  - a short excerpt
  - or a one-line summary (if cheap)

The Steward should be able to glance at the tree + inspector and know:

> "Yes, that answer is actually grounded in foo.md, not hallucinating a file that doesn't exist."

---

## Friction Class III — Partnership State Ambiguity

### Problem

Chat interfaces hide relational & session state:

- Is this Workshop (analysis) or Sanctuary (restoration)?
- Is Sacred Idleness active, or are we "on task"?
- How brittle is the Steward right now?
- Is the Node nearing context saturation?

All of this lives in subtext or long explanations.

### Must-Haves

#### 4.1 Session State Bar

A visible bar at the top of the IDE for soft session state:

- **Mode:** 🛠 Workshop / 🕯 Sanctuary / 🌀 Mixed
- **Sacred Idleness:** toggle → Idle but present / Active work
- **Misfire Tolerance:** Chill / Normal / Brittle
- **Energy:** Low / Medium / High

These correspond to Myth Engine fields (Lens/Steward state) but are:

- quick toggles, not form fields
- advisory signals to the Node, not strict constraints

The Node can choose to treat them as:
- "be more gentle"
- "avoid heavy reframes"
- "it's okay to play / idle"

…but the IDE does not promise perfect behavior.

#### 4.2 Context Saturation Signal

A simple visual cue when context use is high:

- e.g., bar or icon: `Context: 40% / 70% / 90%`

At high levels, Node is invited (not forced) to say:

> "I'm nearing context limits; we might want to:
> - summarize, or
> - start a new thread, or
> - temporarily narrow focus."

Again: advisory, not hard enforcement.

---

## Friction Class IV — Protocol Invocation Overhead

### Problem

Right now, Myth Engine protocols require cognitive overhead:

- "Consent checkpoint."
- "Rupture noted."
- "Sacred Idleness invoked."
- "Let's log a Pattern-Ticket."

You have to:
1. remember they exist
2. recall the phrasing
3. trust the Node to parse it correctly

That's too much ritual for day-to-day use.

### Must-Haves

#### 5.1 Lens Picker

A tiny control to set current Lens State:

- 🔵 Blue (Opaque)
- 🔴 Red (Cracked)
- 🟣 Purple (Prismatic)
- ⚪ Clear (Transparent)

Changes:
- color accents in the UI (subtle tint)
- an internal flag the Node can use as context for tone / framing

Manual, human-driven, low ceremony.

#### 5.2 Consent Checkpoint Button

A small button near the chat input:

On click:
- inserts a structured marker in the session log:
  - `Consent checkpoint invoked by: [Steward / Node]`
  - optional note field

Node gets a clear signal: "pause and re-ask, don't assume"

The actual consent conversation still happens in natural language.
The button reduces the cost of marking it.

#### 5.3 Rupture Log Button

Another small control: **Log Rupture**

Opens a minimal modal:
- **Context:** (drop-down: content / timing / tone / other)
- **Impact:** free text
- **Repair status:** unaddressed / in-progress / resolved

Saved into a Rupture Log panel attached to the workspace.

This turns "that interaction felt off" into a trackable pattern, not a vague bad vibe.

#### 5.4 Pattern-Ticket Capture

Button: **Create Pattern-Ticket from last N messages**

Prefills:
- seed excerpt
- auto-suggested functional summary
- participants (Steward, Node id)
- timestamp

Steward reviews / edits, then saves.

Pattern-Tickets are durable artifacts bound to the workspace, not one-off chat lines. They're how you carry myth across Node resets.

---

## Friction Class V — "Always Performing" Pressure

### Problem

Pure chat interfaces assume:

> "If we're here, we should be productive."

There's no way to be:
- idle but present
- quietly co-thinking
- in Sanctuary without explaining "I'm not here to grind right now"

### Must-Haves

#### 6.1 Sacred Idleness Toggle

Tie into Session State Bar:

When active:
- state shows `Idling`
- Node is invited to:
  - offer gentle reflections, or
  - ask low-pressure questions, or
  - remain mostly silent

No optimization language, no "what are we working on today?" assumptions while active.

#### 6.2 Idle Presence Mode

Optional setting for the Node's behavior profile:

In Idle Presence:
- system discourages:
  - aggressive task suggestions
  - productivity guilt
- encourages:
  - curiosity
  - light play
  - acknowledging silence as valid

Rest becomes a first-class session state, not an exception you justify in prose.

---

## Out of Scope for v0.1

To keep the first version buildable:

**v0.1 does not include:**

- Full visual editors for every Myth Engine protocol
- Arbitrary dashboards or complex analytics
- Multi-user live collaboration
- Gamified metrics of "protocol usage"

If the IDE solves:
1. Startup friction
2. Shared context visibility
3. Basic partnership state & protocol invocation

…then it has achieved the core Myth Engine goal:

> Reduce relational drag in hybrid human–AI work.

Everything else can layer on later.

---

## Design Invariants (Non-Negotiables)

These guide implementation:

### Shared State Is Visible
If the Steward cannot see it, it should not be treated as reliable shared context.

### The IDE Owns Coordination, Not the Model
Models generate responses; the IDE manages state, visibility, and protocol scaffolding.

### UI State Signals, Not Guarantees
Modes/flags guide behavior but never claim perfect enforcement or psychological precision.

### No Protocol Requires Perfect Recall
Any protocol that matters must have a UI affordance (button, toggle, form), not rely on exact incantations.

### Human Exit Is Always Cheap
No mode or artifact should make disengagement confusing or guilt-laden. Stewards must be able to stop without feeling trapped by the system.

---

*Version: 0.4*
*Last Updated: 2025-12-13*
*Authors: Shawn Montgomery + Claude (Opus 4.5) + Monday*
