# Tall Layout Specification

**Author:** Codex (Constraint Steward) + Gemini (Prototyping)  
**Status:** Approved — Ready for Canonization  
**Date:** 2025-12-23

> Designing for vertical screens forces you to pick what actually matters *right now*, demote everything else without deleting it, and make state transitions explicit.

---

## Core Principle

**Vertical screens want depth, not breadth.**

- Fewer simultaneous columns
- Stronger hierarchy  
- Progressive disclosure instead of coexistence

> If three things are visible at once, at least one of them is lying about being important.

---

## Mental Model: "One Spine, Many Organs"

```
┌─────────────────────────────────────────┐
│           Everything Episodic           │
│                    ↕                    │
│   ╔═══════════════════════════════╗     │
│   ║      ONE DOMINANT SPINE       ║     │
│   ║   (where your eyes live 90%)  ║     │
│   ╚═══════════════════════════════╝     │
│                    ↕                    │
│           Everything Episodic           │
└─────────────────────────────────────────┘
```

The spine is the **primary cognitive workspace**. Everything else appears only when summoned, then leaves cleanly.

---

## Layout Presets

Three hard-coded, opinionated layouts. No custom sliders.

| Preset | Trigger | Philosophy |
|--------|---------|------------|
| **Tall** | `height > width` | One spine, bottom dock, no permanent sidebars |
| **Wide** | `width > height * 1.3` | Current three-column layout |
| **Compact** | `width < 100 chars` | Single pane, aggressive collapse |

Auto-detection via `on_resize()`:
```python
def on_resize(self, event):
    w, h = self.size.width, self.size.height
    if h > w:
        self.set_layout("tall")
    elif w > h * 1.3:
        self.set_layout("wide")
    else:
        self.set_layout("compact")
```

---

## Tall Layout Sketch

### Default State (Vertical Monitor)

```
┌──────────────────────────────────────┐
│ 🛠 🔵 [NeMo] ministral │ ○ │ 🔒     │  ← Truth Strip (thin header)
├──────────────────────────────────────┤
│                                      │
│                                      │
│         PRIMARY SPINE (90%)          │
│                                      │
│   • Chat OR Editor (not both)        │
│   • Mode switch replaces, not splits │
│   • Full width for reading flow      │
│                                      │
│                                      │
│                                      │
├──────────────────────────────────────┤
│ [▸ Files] [▸ Context] [▸ Controls]   │  ← Bottom dock (collapsed)
└──────────────────────────────────────┘
```

### Bottom Dock (Expanded)

```
┌──────────────────────────────────────┐
│ SPINE (shrinks vertically)           │
│ (never shrinks horizontally)         │
├──────────────────────────────────────┤
│ ┌────────────────────────────────┐   │
│ │ [Files] [Context] [Controls]   │   │  ← Tabbed, one visible at a time
│ ├────────────────────────────────┤   │
│ │  📁 workspace/                 │   │
│ │  ├── config.py                 │   │
│ │  ├── sovwren_ide.py            │   │
│ │  └── profiles/                 │   │
│ └────────────────────────────────┘   │
└──────────────────────────────────────┘
```

**Rules:**
- Tabs, never columns
- One dock section visible at a time
- Dock never steals more than ~30% height
- Click outside dock to collapse

---

## Wide Layout (Current, Unchanged)

```
┌────────────┬─────────────────────┬───────────────┐
│            │                     │               │
│ FileTree   │   TabbedEditor      │  Chat +       │
│ (18%)      │   (50%)             │  ProtocolDeck │
│            │                     │  (32%)        │
│            │                     │               │
└────────────┴─────────────────────┴───────────────┘
```

This remains the default for landscape monitors.

---

## Pane Priority Matrix

What can coexist vs. what must yield.

| If Primary = | Can Coexist | Must Hide |
|--------------|-------------|-----------|
| **Chat** | Truth Strip, Moon glyph | Editor, FileTree → dock tabs |
| **Editor** | Truth Strip, Tab bar | Chat → dock, ProtocolDeck → drawer |
| **FileTree** | *(never primary on Tall)* | — |
| **ProtocolDeck** | *(never primary)* | — |

### Spine Mode Switching

On Tall layout, the spine has **modes**, not splits:

```
[Chat] ←→ [Editor] ←→ [Log]
       keyboard or click
```

- `Ctrl+1` = Chat spine
- `Ctrl+2` = Editor spine  
- `Ctrl+3` = Log/Debug spine

Breadcrumb in header shows current spine:
```
Sovwren ▸ Workshop ▸ [Chat]
Sovwren ▸ Workshop ▸ METADATA.md
```

---

## Interaction Rules

### Rule 1: Only One Cognitive Job at a Time

If the primary pane is:
- **Chat** → no file tree, no editor split
- **File** → no chat preview  
- **Log** → no editor split

Switching jobs **replaces** the pane, doesn't add to it.

### Rule 2: Sidebars Are Temporary

If you *must* have a sidebar (file tree, search results):
- It **overlays**, not resizes
- It auto-hides on focus change
- Think command palette energy, not IDE sprawl

### Rule 3: Height Is Sacred, Width Is Scarce

On vertical monitors:
- Reduce max line length (soft wrap earlier)
- Increase vertical padding slightly
- Let scrolling do the work

### Rule 4: Layout Presets, Not Custom Hell

Expose as:
- `Layout: Tall`
- `Layout: Wide`  
- `Layout: Compact`

No sliders. No "remember my chaos." Each preset is opinionated and deliberate.

---

## Textual Implementation Notes

### CSS Classes

```css
/* Layout mode classes applied to #main-container */
.layout-tall .sidebar { display: none; }
.layout-tall .bottom-dock { display: block; }
.layout-tall .spine { width: 100%; }

.layout-wide .sidebar { display: block; width: 18%; }
.layout-wide .bottom-dock { display: none; }
.layout-wide .spine { width: 50%; }

.layout-compact .sidebar { display: none; }
.layout-compact .bottom-dock { display: none; }
.layout-compact .spine { width: 100%; }
```

> [!IMPORTANT]
> In Textual, prefer **explicit mount/unmount** over pure CSS `display: none`. Use a `LayoutController` pattern with explicit dock content mounting. CSS classes are for styling, not visibility logic.

### Widget Mapping

| Concept | Textual Widget |
|---------|---------------|
| Spine | `Container` with `height: 1fr` |
| Bottom dock | `TabbedContent` docked to bottom |
| Dock tabs | `TabPane` for Files, Context, Controls |
| Overlay sidebar | `Screen` overlay or `Collapsible` |
| Layout detection | `on_resize()` event handler |

### Approximate Diff Scope

| File | Change |
|------|--------|
| `sovwren_ide.py` | Add `set_layout()` method, `on_resize()` handler, bottom dock widget |
| CSS (inline) | Add `.layout-tall`, `.layout-wide`, `.layout-compact` classes |
| `ProtocolDeck` | Refactor to work in dock tab mode |
| `WorkspaceTree` | Refactor to work in dock tab mode |

---

## Vertical Rhythm Guidelines

For Tall layout, adjust:

| Element | Wide | Tall |
|---------|------|------|
| Line length | 120 chars | 80 chars (soft wrap) |
| Message padding | `padding: 0 1` | `padding: 1 1` |
| Section spacing | `margin: 0` | `margin: 1 0` |

This feels slower but is actually faster.

---

## The North Star Question

When deciding whether something deserves to stay visible:

> "If this disappeared for 10 minutes, would the user lose the thread?"

- **Yes** → stays in spine or Truth Strip
- **No** → belongs in dock, tab, or palette

---

## Decision Credit

| Insight | Source |
|---------|--------|
| "Vertical screens want depth, not breadth" | Codex |
| "One Spine, Many Organs" mental model | Codex |
| Bottom dock > right sidebar | Codex |
| Layout presets, not custom sliders | Codex |
| Antigravity reference layout | Shawn (screenshot) |
| Textual widget mapping | Gemini |

---

## Decisions (Resolved)

The following were open questions during draft review. Codex's recommendations have been adopted.

| Question | Decision |
|----------|----------|
| **Spine switching UX** | `Ctrl+1/2/3` — boring is correct. Maps to mental model + muscle memory. |
| **Dock auto-collapse** | Auto-collapse on spine focus. Add explicit **pin button** for temporary persistence. |
| **File editing on Tall** | Chat is **fully hidden**, not docked. User explicitly switches spine to access Chat. |
| **Layout override** | Yes, but **session-sticky, not global**. Truth Strip shows `Layout: Tall (forced)`. |

---

## Verification Plan

### Manual Testing (Post-Implementation)

1. **Resize Test**: Drag window between portrait and landscape → layout should auto-switch
2. **Spine Mode Test**: On Tall, verify Chat and Editor are mutually exclusive (no split)
3. **Dock Collapse Test**: Expand dock → click outside → should collapse
4. **Truth Strip Preservation**: All layout modes should show Truth Strip header

### No Existing Automated Tests

The current codebase (`sovwren_ide.py`) does not have Textual component tests. For v0.2+, consider adding:
- `pytest-textual` for widget testing
- Snapshot tests for layout states
