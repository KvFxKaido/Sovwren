"""
Sovwren IDE - Partnership-first interface for local LLMs

A Textual-based cockpit implementing the Friction Spec.
Connects to LM Studio / Ollama for local model inference.

Usage:
    pip install textual
    python sovwren_ide.py
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Input, Button, DirectoryTree, Label, Switch, TextArea
from textual.screen import Screen
from textual.reactive import reactive
from textual.message import Message
from textual import events
import asyncio
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent          # .../MythOS
workspace_root = project_root.parent          # .../MythEngine
sys.path.insert(0, str(project_root))


# --- MYTHIC COMPONENTS ---

class TicketModal(Screen):
    """Modal for weaving a Pattern Ticket."""
    CSS = """
    TicketModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #ticket-dialog {
        width: 80%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    #ticket-editor {
        height: 1fr;
        margin: 1 0;
        border: solid $secondary;
    }
    #dialog-buttons {
        height: auto;
        align: right middle;
    }
    #dialog-buttons Button {
        margin-left: 1;
    }
    """

    def __init__(self, initial_content: str):
        super().__init__()
        self.initial_content = initial_content

    def compose(self) -> ComposeResult:
        with Container(id="ticket-dialog"):
            yield Label("[b]Weave Pattern Ticket[/b]", classes="panel-header")
            yield TextArea(self.initial_content, id="ticket-editor", language="markdown")
            with Horizontal(id="dialog-buttons"):
                yield Button("Cancel", id="btn-cancel", variant="error")
                yield Button("Save Ticket", id="btn-save", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            editor = self.query_one("#ticket-editor", TextArea)
            self.dismiss(editor.text)
        elif event.button.id == "btn-cancel":
            self.dismiss(None)


# Profile-specific splash art
SPLASH_ART = {
    "nemo": {
        "ascii": r"""

    ███╗   ██╗███████╗███╗   ███╗ ██████╗
    ████╗  ██║██╔════╝████╗ ████║██╔═══██╗
    ██╔██╗ ██║█████╗  ██╔████╔██║██║   ██║
    ██║╚██╗██║██╔══╝  ██║╚██╔╝██║██║   ██║
    ██║ ╚████║███████╗██║ ╚═╝ ██║╚██████╔╝
    ╚═╝  ╚═══╝╚══════╝╚═╝     ╚═╝ ╚═════╝

        """,
        "tagline": "Grounded Node · Partnership-First Interface",
        "color": "bright_magenta",
    },
    "oracle": {
        "ascii": r"""

     ██████╗ ██████╗  █████╗  ██████╗██╗     ███████╗
    ██╔═══██╗██╔══██╗██╔══██╗██╔════╝██║     ██╔════╝
    ██║   ██║██████╔╝███████║██║     ██║     █████╗
    ██║   ██║██╔══██╗██╔══██║██║     ██║     ██╔══╝
    ╚██████╔╝██║  ██║██║  ██║╚██████╗███████╗███████╗
     ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚══════╝

        """,
        "tagline": "Patterns into Reflection",
        "color": "purple",
    },
}


class SplashScreen(Screen):
    """Ritual entry screen - the threshold moment before partnership begins."""

    CSS = """
    SplashScreen {
        align: center middle;
        background: #000000;
    }
    #splash-art {
        text-align: center;
        width: 100%;
        content-align: center middle;
        color: #8a6ab0;
    }
    #splash-tagline {
        text-align: center;
        width: 100%;
        margin-top: 1;
        color: #606060;
    }
    #splash-hint {
        text-align: center;
        width: 100%;
        margin-top: 2;
        color: #404040;
    }
    """

    def __init__(self, profile: str = "nemo"):
        super().__init__()
        self.profile = profile
        self.splash_data = SPLASH_ART.get(profile, SPLASH_ART["nemo"])

    def compose(self) -> ComposeResult:
        ascii_art = self.splash_data.get("ascii", "")
        tagline = self.splash_data.get("tagline", "")

        yield Static(ascii_art, id="splash-art")
        yield Static(tagline, id="splash-tagline")
        yield Static("Press any key to continue...", id="splash-hint")

    def on_key(self, event) -> None:
        """Dismiss on any key press."""
        self.dismiss(True)


class ProfilePickerModal(Screen):
    """Modal for switching Node profiles mid-session."""

    CSS = """
    ProfilePickerModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #profile-dialog {
        width: 60%;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    #profile-list {
        height: auto;
        max-height: 20;
        margin: 1 0;
        border: solid $secondary;
        padding: 1;
        overflow-y: auto;
    }
    #profile-buttons {
        height: auto;
        align: right middle;
    }
    #profile-buttons Button {
        margin-left: 1;
    }
    .profile-current {
        color: #8a6ab0;
    }
    """

    def __init__(self, profiles: list[dict], current_profile: str):
        super().__init__()
        self.profiles = profiles
        self.current_profile = current_profile

    def compose(self) -> ComposeResult:
        lines = []
        if self.profiles:
            lines.append("[b]Available Profiles[/b]")
            lines.append("")
            for i, p in enumerate(self.profiles, 1):
                name = p.get("name", "Unknown")
                desc = p.get("description", "")
                current = " [cyan]← current[/cyan]" if name.lower() == self.current_profile.lower() else ""
                lines.append(f"{i}. [b]{name}[/b]{current}")
                if desc:
                    lines.append(f"   [dim]{desc}[/dim]")
        else:
            lines.append("[dim]No profiles found in profiles/ folder[/dim]")

        with Container(id="profile-dialog"):
            yield Label("[b]Switch Profile[/b]", classes="panel-header")
            yield Static(f"[dim]Current: {self.current_profile}[/dim]", classes="info-box")
            yield Static("\n".join(lines), id="profile-list")
            yield Input(placeholder="Enter profile # or name", id="profile-input")
            with Horizontal(id="profile-buttons"):
                yield Button("Cancel", id="btn-profile-cancel", variant="error")
                yield Button("Switch", id="btn-profile-switch", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-profile-cancel":
            self.dismiss(None)
            return

        if event.button.id != "btn-profile-switch":
            return

        # Get input value
        try:
            input_widget = self.query_one("#profile-input", Input)
            raw = input_widget.value.strip()
        except Exception:
            self.dismiss(None)
            return

        if not raw:
            self.dismiss(None)
            return

        # Try to parse as number
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(self.profiles):
                self.dismiss({"profile": self.profiles[idx].get("name", "").lower()})
                return
        except ValueError:
            pass

        # Treat as profile name
        self.dismiss({"profile": raw.lower()})

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        raw = event.value.strip()
        if not raw:
            return

        # Try number first
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(self.profiles):
                self.dismiss({"profile": self.profiles[idx].get("name", "").lower()})
                return
        except ValueError:
            pass

        self.dismiss({"profile": raw.lower()})


class ModelPickerModal(Screen):
    """Modal for switching LLM models and backends."""

    CSS = """
    ModelPickerModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #model-dialog {
        width: 70%;
        height: 70%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    #model-list {
        height: 1fr;
        margin: 1 0;
        border: solid $secondary;
        padding: 1;
        overflow-y: auto;
    }
    #backend-row {
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    #backend-row Button {
        margin: 0 1;
    }
    #model-buttons {
        height: auto;
        align: right middle;
    }
    #model-buttons Button {
        margin-left: 1;
    }
    .backend-active {
        color: #8a6ab0;
        border: solid #8a6ab0;
    }
    """

    def __init__(self, models: list[dict], current_model: str, backend: str):
        super().__init__()
        self.models = models
        self.current_model = current_model
        self.backend = backend  # "lmstudio" or "ollama"

    def compose(self) -> ComposeResult:
        lines = []
        if self.models:
            lines.append(f"[b]Available Models ({self.backend.upper()})[/b]")
            lines.append("")
            for i, m in enumerate(self.models, 1):
                name = m.get("name", "unknown")
                current = " [cyan]← current[/cyan]" if m.get("current") else ""
                size_bytes = m.get("size", 0)
                size_gb = f" ({size_bytes / 1e9:.1f}GB)" if size_bytes > 0 else ""
                lines.append(f"{i}. {name}{size_gb}{current}")
        else:
            lines.append("[dim]No models found. Is the backend running?[/dim]")

        with Container(id="model-dialog"):
            yield Label("[b]Model Switching[/b]", classes="panel-header")
            yield Static(f"[dim]Current: {self.current_model or 'None'}[/dim]", classes="info-box")
            with Horizontal(id="backend-row"):
                yield Button(
                    "LM Studio",
                    id="btn-backend-lmstudio",
                    classes="backend-active" if self.backend == "lmstudio" else ""
                )
                yield Button(
                    "Ollama",
                    id="btn-backend-ollama",
                    classes="backend-active" if self.backend == "ollama" else ""
                )
            yield Static("\n".join(lines), id="model-list")
            yield Input(placeholder="Enter model # or name", id="model-input")
            with Horizontal(id="model-buttons"):
                yield Button("Cancel", id="btn-model-cancel", variant="error")
                yield Button("Switch", id="btn-model-switch", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-model-cancel":
            self.dismiss(None)
            return

        if event.button.id == "btn-backend-lmstudio":
            self.dismiss({"action": "switch_backend", "backend": "lmstudio"})
            return

        if event.button.id == "btn-backend-ollama":
            self.dismiss({"action": "switch_backend", "backend": "ollama"})
            return

        if event.button.id != "btn-model-switch":
            return

        input_widget = self.query_one("#model-input", Input)
        raw = (input_widget.value or "").strip()

        if not raw:
            self.dismiss(None)
            return

        # Numeric => list index
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(self.models):
                self.dismiss({"action": "switch_model", "model": self.models[idx]["name"]})
            else:
                self.dismiss(None)
            return

        # Otherwise treat as model name
        self.dismiss({"action": "switch_model", "model": raw})


class SessionPickerModal(Screen):
    """Modal for resuming or starting a chat session."""

    CSS = """
    SessionPickerModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #session-dialog {
        width: 80%;
        height: 70%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    #session-list {
        height: 1fr;
        margin: 1 0;
        border: solid $secondary;
        padding: 1;
    }
    #session-input {
        margin: 1 0;
    }
    #session-buttons {
        height: auto;
        align: right middle;
    }
    #session-buttons Button {
        margin-left: 1;
    }
    /* Ethical friction: armed delete buttons */
    .delete-armed {
        background: #6b2020;
        color: #ff6b6b;
        border: solid #ff6b6b;
        text-style: bold;
    }
    """

    def __init__(self, sessions: list[dict], last_session_id: str | None, total_count: int = 0):
        super().__init__()
        self.sessions = sessions
        self.last_session_id = last_session_id
        self.total_count = total_count
        # Ethical friction: track armed state for destructive actions
        self._delete_armed = False
        self._delete_all_armed = False

    def compose(self) -> ComposeResult:
        last_hint = f"[dim]Last session: {self.last_session_id[:8]}...[/dim]" if self.last_session_id else "[dim]No last session saved[/dim]"

        # Header with count
        showing = len(self.sessions)
        if self.total_count > showing:
            header = f"[b]Recent Sessions[/b] [dim](showing {showing} of {self.total_count})[/dim]"
        else:
            header = f"[b]Recent Sessions[/b] [dim]({self.total_count} total)[/dim]"

        lines = []
        if self.sessions:
            for i, s in enumerate(self.sessions, 1):
                name = s.get("name") or s.get("first_message_preview") or "Unnamed"
                last_active = str(s.get("last_active", ""))[:19] if s.get("last_active") else "Unknown"
                msg_count = s.get("message_count", 0)
                lines.append(f"{i}. {last_active} | {msg_count} msgs | {name}")
        else:
            lines.append("[dim]No sessions found.[/dim]")

        with Container(id="session-dialog"):
            yield Label("[b]Resume Chat[/b]", classes="panel-header")
            yield Static(last_hint, classes="info-box")
            yield Static(header, classes="info-box")
            yield Static("\n".join(lines), id="session-list")
            yield Input(placeholder="Enter session # (blank = last)", id="session-input")
            with Horizontal(id="session-buttons"):
                yield Button("Cancel", id="btn-session-cancel", variant="error")
                yield Button("Delete All", id="btn-session-delete-all", variant="error")
                yield Button("Delete", id="btn-session-delete", variant="warning")
                yield Button("Start New", id="btn-session-new", variant="primary")
                yield Button("Resume", id="btn-session-resume", variant="success")

    def _reset_armed_state(self) -> None:
        """Reset all armed delete buttons to normal state."""
        self._delete_armed = False
        self._delete_all_armed = False
        try:
            del_btn = self.query_one("#btn-session-delete", Button)
            del_btn.label = "Delete"
            del_btn.remove_class("delete-armed")
            del_all_btn = self.query_one("#btn-session-delete-all", Button)
            del_all_btn.label = "Delete All"
            del_all_btn.remove_class("delete-armed")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-session-cancel":
            self.dismiss(None)
            return

        if event.button.id == "btn-session-new":
            self._reset_armed_state()
            self.dismiss({"action": "new"})
            return

        # Ethical friction: two-step delete for "Delete All"
        if event.button.id == "btn-session-delete-all":
            if self.total_count == 0:
                return
            if not self._delete_all_armed:
                # First click: arm the button
                self._delete_all_armed = True
                self._delete_armed = False  # Disarm single delete
                event.button.label = "Sure?"
                event.button.add_class("delete-armed")
                # Reset the other delete button
                try:
                    del_btn = self.query_one("#btn-session-delete", Button)
                    del_btn.label = "Delete"
                    del_btn.remove_class("delete-armed")
                except Exception:
                    pass
                return
            else:
                # Second click: confirm deletion
                self.dismiss({"action": "delete_all"})
                return

        # Ethical friction: two-step delete for single "Delete"
        if event.button.id == "btn-session-delete":
            input_widget = self.query_one("#session-input", Input)
            raw = (input_widget.value or "").strip()

            if not raw or not raw.isdigit():
                self.notify("Enter a session # first", severity="warning")
                return

            idx = int(raw) - 1
            if not (0 <= idx < len(self.sessions)):
                self.notify(f"Invalid # (1-{len(self.sessions)})", severity="error")
                return

            if not self._delete_armed:
                # First click: arm the button
                self._delete_armed = True
                self._delete_all_armed = False  # Disarm delete all
                event.button.label = "Sure?"
                event.button.add_class("delete-armed")
                # Reset the other delete button
                try:
                    del_all_btn = self.query_one("#btn-session-delete-all", Button)
                    del_all_btn.label = "Delete All"
                    del_all_btn.remove_class("delete-armed")
                except Exception:
                    pass
                return
            else:
                # Second click: confirm deletion
                self.dismiss({"action": "delete", "session_id": self.sessions[idx]["id"]})
                return

        # Any other button press resets armed state
        if event.button.id == "btn-session-resume":
            self._reset_armed_state()

        if event.button.id != "btn-session-resume":
            return

        input_widget = self.query_one("#session-input", Input)
        raw = (input_widget.value or "").strip()

        # Blank => last session id
        if not raw:
            if self.last_session_id:
                self.dismiss({"action": "resume", "session_id": self.last_session_id})
            else:
                self.dismiss({"action": "new"})
            return

        # Numeric => list index
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(self.sessions):
                self.dismiss({"action": "resume", "session_id": self.sessions[idx]["id"]})
            else:
                self.dismiss(None)
            return

        # Otherwise treat as session id
        self.dismiss({"action": "resume", "session_id": raw})


class WorkspaceTree(Vertical):
    """Class II: Shared Context Visibility."""
    def compose(self) -> ComposeResult:
        yield Label("[b]Workspace[/b]", classes="panel-header")
        # Point to MythEngine workspace
        yield DirectoryTree(str(workspace_root), id="file-tree")
        yield Label("[b]Memory[/b]", classes="panel-header")
        yield Static("No memories loaded", id="memory-status", classes="info-box")
        yield Label("[b]Last Context[/b]", classes="panel-header")
        yield Static("[dim]No context loaded[/dim]", id="context-status", classes="info-box")


class ProtocolDeck(Vertical):
    """Class IV & V: Protocol Invocation & Idleness."""
    def compose(self) -> ComposeResult:
        yield Label("[b]Lens State[/b]", classes="panel-header")
        with Horizontal(classes="button-row"):
            yield Button("Blue", id="lens-blue", classes="lens-btn active")
            yield Button("Red", id="lens-red", classes="lens-btn")
            yield Button("Purple", id="lens-purple", classes="lens-btn")

        yield Label("[b]Protocols[/b]", classes="panel-header")
        yield Button("Weave Ticket", id="btn-ticket", classes="proto-btn proto-btn-accent")
        yield Button("Sessions", id="btn-sessions", classes="proto-btn")
        yield Button("Models", id="btn-models", classes="proto-btn")
        yield Button("Profiles", id="btn-profiles", classes="proto-btn")

        yield Label("[b]Sacred Idleness[/b]", classes="panel-header")
        with Horizontal(classes="toggle-row"):
            yield Label("Idle Mode:", classes="toggle-label")
            yield Switch(value=False, id="toggle-idleness")

        yield Label("[b]Mode[/b]", classes="panel-header")
        with Horizontal(classes="button-row"):
            yield Button("Workshop", id="mode-workshop", classes="mode-btn active")
            yield Button("Sanctuary", id="mode-sanctuary", classes="mode-btn")


class NeuralStream(ScrollableContainer):
    """The Chat Window."""
    def compose(self) -> ComposeResult:
        # Show themed ASCII art on startup
        from config import get_themed_ascii, DEFAULT_THEME
        yield Static(get_themed_ascii(DEFAULT_THEME), classes="message system")
        yield Static("[dim]MythOS initialized. Connecting to Node...[/dim]", classes="message system")

    def add_message(self, content: str, role: str = "system"):
        """Add a message to the stream."""
        css_class = f"message {role}"
        self.mount(Static(content, classes=css_class))
        self.scroll_end(animate=False)


class StatusBar(Static):
    """Bottom status showing connection state."""
    connected = reactive(False)
    model_name = reactive("Not connected")
    context_band = reactive("Unknown")

    # Moon phases for context load: empty → filling → half → full
    CONTEXT_GLYPHS = {
        "Low": "○",      # Empty moon - plenty of space
        "Medium": "◔",   # Quarter - filling up
        "High": "◑",     # Half - getting full
        "Critical": "●", # Full moon - at capacity
    }

    def _get_context_glyph(self) -> str:
        """Get moon glyph for current context band."""
        if "Critical" in self.context_band:
            return self.CONTEXT_GLYPHS["Critical"]
        elif "High" in self.context_band:
            return self.CONTEXT_GLYPHS["High"]
        elif "Medium" in self.context_band:
            return self.CONTEXT_GLYPHS["Medium"]
        return self.CONTEXT_GLYPHS["Low"]

    def compose(self) -> ComposeResult:
        with Horizontal(id="status-bar-content"):
            yield Label(self._get_context_glyph(), id="context-glyph")
            yield Label(f"Node: {self.model_name} | Status: {'Connected' if self.connected else 'Disconnected'}", id="status-text")

    def update_status(self, connected: bool, model: str = ""):
        self.connected = connected
        self.model_name = model or ("Ready" if connected else "Not connected")
        self.query_one("#status-text", Label).update(
            f"Node: {self.model_name} | Status: {'Connected' if connected else 'Disconnected'}"
        )

    def update_context_glyph(self, band: str):
        """Update the moon glyph based on context band."""
        self.context_band = band
        try:
            self.query_one("#context-glyph", Label).update(self._get_context_glyph())
        except Exception:
            pass


class ChatInput(TextArea):
    """Custom TextArea that submits on Enter."""

    class Submitted(Message):
        """Fired when user submits the message."""
        def __init__(self, value: str) -> None:
            self.value = value
            super().__init__()

    def _on_key(self, event: events.Key) -> None:
        """Handle Enter for submit."""
        # Plain Enter = submit
        if event.key == "enter":
            text = self.text.strip()
            if text:
                event.stop()
                event.prevent_default()
                self.post_message(self.Submitted(text))
            else:
                # Empty input, suppress the enter
                event.stop()
                event.prevent_default()
            return

        # Let other keys pass through to TextArea
        super()._on_key(event)


# --- MAIN APP ---

class MythIDE(App):
    CSS = """
    /* AMOLED Theme: True black, soft text, quiet accents
       Rule: "Did this make me notice the interface less?" */

    Screen {
        layout: vertical;
        background: #000000;
    }

    /* Layout Containers */
    #main-layout { height: 1fr; }
    #sidebar-left { width: 22%; border-right: solid #1a1a1a; background: #000000; }
    #sidebar-right { width: 18%; border-left: solid #1a1a1a; background: #000000; }
    #center-stage { width: 1fr; }

    /* Class II: File Tree */
    #file-tree { height: 60%; background: #000000; }
    .panel-header {
        padding: 0 1;
        color: #808080;
        text-align: center;
        background: #0a0a0a;
        text-style: bold;
    }
    .info-box { height: auto; padding: 0 1; color: #606060; }

    /* Class IV: Protocol Buttons */
    .button-row {
        height: auto;
        align: center middle;
        padding: 0;
    }
    .toggle-row {
        height: auto;
        align: center middle;
        padding: 0;
    }
    .toggle-label {
        margin-right: 1;
        color: #808080;
    }

    /* All buttons: AMOLED base */
    Button {
        background: #0a0a0a;
        color: #808080;
        border: solid #1a1a1a;
    }
    Button:hover {
        background: #1a1a1a;
        color: #a0a0a0;
    }
    Button:focus {
        background: #1a1a1a;
    }

    /* Lens buttons */
    .lens-btn { min-width: 6; margin: 0; }
    #lens-blue.active { color: #4a7ab0; border: solid #4a7ab0; }
    #lens-red.active { color: #b04a4a; border: solid #b04a4a; }
    #lens-purple.active { color: #7a4ab0; border: solid #7a4ab0; }

    /* Mode buttons */
    .mode-btn { min-width: 8; margin: 0; }
    #mode-workshop.active { color: #4a7ab0; border: solid #4a7ab0; }
    #mode-sanctuary.active { color: #8a6ab0; border: solid #8a6ab0; }

    /* Protocol buttons */
    .proto-btn { width: 100%; margin: 0; }
    .proto-btn-accent {
        color: #b0954a;
        border: solid #b0954a;
    }

    /* Chat Area */
    NeuralStream {
        background: #000000;
        padding: 0 1;
        border: solid #1a1a1a;
    }
    .message { margin-bottom: 0; padding: 0 1; }
    .system { color: #505050; }
    .node { color: #b08ad0; }
    .steward { color: #e0e0e0; }
    .error { color: #d46a6a; }

    /* Input Area */
    #input-container {
        height: 3;
        padding: 0;
        background: #000000;
    }
    #chat-input {
        width: 100%;
        height: 100%;
        background: #000000;
        border: none;
        border-top: solid #1a1a1a;
        color: #e0e0e0;
    }

    /* Status Bar */
    StatusBar {
        height: 1;
        background: #000000;
        color: #505050;
        padding: 0 1;
    }
    #status-bar-content {
        height: 1;
        width: 100%;
    }
    #context-glyph {
        width: 3;
        color: #909090;
        margin-right: 1;
    }
    #status-text {
        width: 1fr;
    }

    /* Temporal Empathy: Border dims when idle */
    NeuralStream.idle-dim {
        border: solid #0d0d0d;  /* ~25% of #1a1a1a */
    }
    .mode-workshop NeuralStream.idle-dim {
        border: solid #12202c;  /* ~25% of #4a7ab0 */
    }
    .mode-sanctuary NeuralStream.idle-dim {
        border: solid #221a2c;  /* ~25% of #8a6ab0 */
    }

    /* Header/Footer */
    Header {
        background: #000000;
        color: #606060;
    }
    Footer {
        background: #000000;
        color: #505050;
    }
    FooterKey {
        background: #0a0a0a;
        color: #707070;
    }

    /* Mode border colors */
    .mode-workshop NeuralStream {
        border: solid #4a7ab0;
    }
    .mode-sanctuary NeuralStream {
        border: solid #8a6ab0;
    }

    /* Scrollbar: AMOLED purple */
    $scrollbar-background: #8a6ab0;
    $scrollbar-background-hover: #9a7ac0;
    $scrollbar-background-active: #9a7ac0;
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+l", "clear_chat", "Clear"),
        ("ctrl+b", "toggle_sidebar", "Toggle Sidebar"),
        ("ctrl+r", "sessions", "Sessions"),
        ("f1", "profiles", "Profiles"),
        ("f2", "models", "Models"),
        ("f3", "consent_check", "Consent"),
        ("f4", "log_rupture", "Rupture"),
        ("ctrl+o", "open_external", "Open in Editor"),
        ("ctrl+j", "insert_newline", "Newline"),
    ]

    def get_system_commands(self, screen):
        """Filter out the built-in theme command to preserve AMOLED styling."""
        for command in super().get_system_commands(screen):
            # SystemCommand is a NamedTuple with: title, callback, help, discover
            # Check all string fields for "theme"
            try:
                command_str = str(command).lower()
                if "theme" not in command_str:
                    yield command
            except Exception:
                # If anything goes wrong, include the command
                yield command

    # Context tracking constants
    DEFAULT_CONTEXT_WINDOW = 32768  # Fallback for unknown models
    SYSTEM_PROMPT_ESTIMATE = 800  # Approximate tokens for system prompt stack
    AVG_TOKENS_PER_CHAR = 0.25  # Rough estimate: 4 chars ~ 1 token
    MAX_RAM_EXCHANGES = 10  # Max conversation pairs to keep in RAM history
    HISTORY_CONTEXT_TURNS = 5 # Number of recent conversation turns to include as context for Node
    PREF_LAST_SESSION_KEY = "last_session_id"  # Preference key for session resume
    PREF_LAST_PROFILE_KEY = "last_profile"  # Preference key for profile persistence

    # Known context windows for common models (in tokens)
    # Add models as you encounter them - this is a practical lookup, not exhaustive
    MODEL_CONTEXT_WINDOWS = {
        # Mistral family
        "ministral-3b": 32768,
        "ministral-8b": 32768,
        "mistral-7b": 8192,
        "mistral-nemo": 128000,
        # Llama family
        "llama-3.2": 128000,
        "llama-3.1": 128000,
        "llama-3": 8192,
        "llama-2": 4096,
        # Qwen family
        "qwen2.5": 32768,
        "qwen2": 32768,
        "qwen-coder": 32768,
        # DeepSeek
        "deepseek-r1": 64000,
        "deepseek-coder": 16384,
        # Phi
        "phi-3": 128000,
        "phi-4": 16384,
        # Gemma
        "gemma-2": 8192,
        "gemma": 8192,
        # CodeLlama
        "codellama": 16384,
    }

    def __init__(self):
        super().__init__()
        self.llm_client = None
        self.connected = False
        self.current_backend = "lmstudio"  # "lmstudio" or "ollama"
        self.current_profile = None  # Loaded profile dict
        self.current_profile_name = "nemo"  # Profile name string
        self.session_mode = "Workshop"
        self.session_lens = "Blue"
        self.idle_mode = False

        # Context tracking (Phase 1 buckets)
        self.conversation_history = []  # List of (role, content) tuples
        self.rag_chunks_loaded = []     # List of (source, content) tuples
        self.last_context_sources = []  # What was used in last response
        self.context_high_acknowledged = False   # Has Node acknowledged High?
        self.context_critical_acknowledged = False  # Has Node acknowledged Critical?
        self._last_context_band = "Unknown"      # Track transitions

        # RAG system
        self.rag_retriever = None
        self.rag_initialized = False

        # File selection tracking
        self.selected_file = None  # Currently selected file path

        # Ticket weaving guard
        self._weaving_ticket = False

        # Temporal empathy: track input activity for border dimming
        self._last_input_time = time.time()
        self._idle_dim_active = False
        self.IDLE_THRESHOLD = 45  # seconds before border dims (midpoint of 30-60)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-layout"):
            # Left: Files (Context Visibility)
            with Vertical(id="sidebar-left"):
                yield WorkspaceTree()

            # Center: Chat (The Stream)
            with Vertical(id="center-stage"):
                yield NeuralStream()
                with Container(id="input-container"):
                    yield ChatInput(id="chat-input", show_line_numbers=False)

            # Right: Protocols (The Controls)
            with Vertical(id="sidebar-right"):
                yield ProtocolDeck()

        yield StatusBar()
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "MythOS IDE v0.1"
        self.sub_title = "Partnership-First Interface"

        # Set initial mode for border color
        self.add_class("mode-workshop")

        # Temporal empathy: start idle check timer (checks every 5 seconds)
        self.set_interval(5.0, self._check_idle_state)

        # Initialize database early so we can read profile preference
        try:
            from core.database import Database
            self.db = Database()
            await self.db.initialize()
        except Exception:
            self.db = None

        # Load saved profile preference (default to nemo)
        splash_profile = "nemo"
        if self.db:
            try:
                saved_profile = await self.db.get_preference(self.PREF_LAST_PROFILE_KEY, default="nemo")
                if saved_profile and saved_profile in SPLASH_ART:
                    splash_profile = saved_profile
                    self.current_profile_name = saved_profile
            except Exception:
                pass

        # Show ritual entry splash with saved profile (threshold moment)
        # On dismiss, continue to _post_splash_startup
        self.push_screen(SplashScreen(profile=splash_profile), callback=self._post_splash_startup)

    def _post_splash_startup(self, result) -> None:
        """Continue startup after splash dismisses."""
        # Run the async startup in a task
        asyncio.create_task(self._initialize_app())

    async def _initialize_app(self) -> None:
        """Initialize database and complete startup (called after splash)."""
        # DB already initialized in on_mount for profile preference
        # Pick session (resume/new), then continue startup
        await self._begin_session_flow()

    async def _begin_session_flow(self) -> None:
        """Start or resume a chat session before the rest of startup."""
        if self.db is None:
            await self._complete_startup()
            return

        try:
            sessions = await self.db.list_sessions(limit=10)
            last_session_id = await self.db.get_preference(self.PREF_LAST_SESSION_KEY, default=None)
        except Exception:
            sessions = []
            last_session_id = None

        # Auto-resume last session if we have one.
        if last_session_id:
            try:
                session = await self.db.get_session(last_session_id)
                if session and int(session.get("message_count") or 0) > 0:
                    await self._resume_session(last_session_id)
                    try:
                        stream = self.query_one(NeuralStream)
                        stream.add_message("[dim]Auto-resumed last session. Ctrl+R to switch.[/dim]", "system")
                    except Exception:
                        pass
                    await self._complete_startup()
                    return
            except Exception:
                pass

        if sessions or last_session_id:
            self.push_screen(
                SessionPickerModal(sessions=sessions, last_session_id=last_session_id),
                self._on_session_picked,
            )
        else:
            await self._start_new_session()
            await self._complete_startup()

    def _on_session_picked(self, result: dict | None) -> None:
        """Callback from SessionPickerModal."""
        asyncio.create_task(self._handle_session_choice(result))

    async def _handle_session_choice(self, result: dict | None) -> None:
        if not result or result.get("action") == "new":
            await self._start_new_session()
        elif result.get("action") == "resume" and result.get("session_id"):
            await self._resume_session(result["session_id"])
        else:
            await self._start_new_session()

        await self._complete_startup()

    async def _complete_startup(self) -> None:
        # Load profile first (before connecting)
        await self._load_profile(self.current_profile_name)

        # Try to connect to LM Studio (will use preferred_model if set)
        await self.connect_to_node()

        # Initialize RAG system
        await self._initialize_rag()

        # Load existing memories into sidebar
        await self._refresh_memory_display()

    async def _load_profile(self, profile_name: str) -> None:
        """Load a profile and apply its settings."""
        from config import load_profile, DEFAULT_PROFILE

        stream = self.query_one(NeuralStream)

        profile = load_profile(profile_name)
        if not profile:
            stream.add_message(f"[yellow]Profile '{profile_name}' not found, using default[/yellow]", "system")
            profile = load_profile(DEFAULT_PROFILE)

        if profile:
            self.current_profile = profile
            self.current_profile_name = profile.get("name", profile_name).lower()
            stream.add_message(f"[dim]Profile loaded: {profile.get('name', profile_name)}[/dim]", "system")

            # Store preferred model for connect_to_node to use
            preferred = profile.get("preferred_model")
            if preferred:
                stream.add_message(f"[dim]Preferred model: {preferred}[/dim]", "system")
        else:
            stream.add_message("[red]No profiles available[/red]", "error")

    async def _start_new_session(self) -> None:
        """Create a fresh session record and reset local state."""
        self.session_id = str(uuid.uuid4())
        self.conversation_history = []
        self._exchange_count = 0

        if self.db is None:
            self._update_session_label("New")
            return

        try:
            await self.db.create_session(self.session_id)
            await self.db.set_preference(self.PREF_LAST_SESSION_KEY, self.session_id)
        except Exception:
            pass

        self._update_session_label("New")

    async def _resume_session(self, session_id: str) -> None:
        """Load prior session conversation into RAM (trimmed), ready to continue."""
        if self.db is None:
            return

        session = None
        conversations = []
        try:
            session = await self.db.get_session(session_id)
            if session:
                conversations = await self.db.get_session_conversations(session_id)
        except Exception:
            session = None

        if not session:
            await self._start_new_session()
            return

        self.session_id = session["id"]
        await self.db.set_preference(self.PREF_LAST_SESSION_KEY, self.session_id)

        # Trim to last N exchanges for sane context/tokens.
        max_pairs = max(1, self.MAX_RAM_EXCHANGES)
        recent_pairs = conversations[-max_pairs:]

        self.conversation_history = []
        for conv in recent_pairs:
            self.conversation_history.append(("steward", conv["user_message"]))
            self.conversation_history.append(("node", conv["ai_response"]))

        self._exchange_count = int(session.get("message_count") or len(conversations) or 0)

        name = session.get("name") or session.get("first_message_preview") or "Unnamed"
        self._update_session_label(name)

        # Surface in the stream (lightly, not a full scrollback dump).
        try:
            stream = self.query_one(NeuralStream)
            stream.add_message(f"[dim]Resumed session: {name}[/dim]", "system")
            if self.conversation_history:
                stream.add_message("[dim]Recent history loaded (trimmed).[/dim]", "system")
                for role, content in self.conversation_history[-8:]:
                    if role == "steward":
                        stream.add_message(f"[b]Steward:[/b] {content}", "steward")
                    elif role == "node":
                        stream.add_message(f"[b]Node:[/b] {content}", "node")
        except Exception:
            pass

        self._update_context_band()

    def _update_session_label(self, name: str) -> None:
        """Update session label (for future use, e.g., in title bar)."""
        # SessionStateBar removed - state communicated through ambient signals
        pass

    def action_sessions(self) -> None:
        """Open session picker modal."""
        if self.db is None:
            stream = self.query_one(NeuralStream)
            stream.add_message("[yellow]Session persistence unavailable (DB not initialized).[/yellow]", "system")
            return

        asyncio.create_task(self._open_session_picker())

    def action_consent_check(self) -> None:
        """Invoke consent checkpoint (F3). Ritual protocol for explicit consent."""
        stream = self.query_one(NeuralStream)
        stream.add_message("[yellow]--- CONSENT CHECKPOINT ---[/yellow]", "system")
        stream.add_message("[dim]Pausing for explicit consent. Please confirm before continuing.[/dim]", "system")

    def action_log_rupture(self) -> None:
        """Log a rupture moment (F4). Ritual protocol for noting misattunement."""
        stream = self.query_one(NeuralStream)
        stream.add_message("[red]--- RUPTURE LOGGED ---[/red]", "system")
        stream.add_message("[dim]Misattunement noted. Consider repair before proceeding.[/dim]", "system")

    async def _open_session_picker(self) -> None:
        try:
            sessions = await self.db.list_sessions(limit=10)
            last_session_id = await self.db.get_preference(self.PREF_LAST_SESSION_KEY, default=None)
            total_count = await self.db.count_sessions()
        except Exception:
            sessions = []
            last_session_id = None
            total_count = 0

        self.push_screen(
            SessionPickerModal(sessions=sessions, last_session_id=last_session_id, total_count=total_count),
            self._on_session_switch_picked,
        )

    def _on_session_switch_picked(self, result: dict | None) -> None:
        asyncio.create_task(self._handle_session_switch(result))

    async def _handle_session_switch(self, result: dict | None) -> None:
        """Switch sessions during runtime."""
        if not result:
            return

        if result.get("action") == "new":
            await self._start_new_session()
            self.action_clear_chat()
            return

        if result.get("action") == "delete" and result.get("session_id"):
            await self._delete_session(result["session_id"])
            # Re-open the picker to show updated list
            await self._open_session_picker()
            return

        if result.get("action") == "delete_all":
            await self._delete_all_sessions()
            return

        if result.get("action") == "resume" and result.get("session_id"):
            self.action_clear_chat()
            await self._resume_session(result["session_id"])
            self._update_context_band()

    async def _delete_session(self, session_id: str) -> None:
        """Delete a session and handle if it's the current one."""
        if self.db is None:
            return

        stream = self.query_one(NeuralStream)

        try:
            await self.db.delete_session(session_id)
            stream.add_message(f"[dim]Session deleted[/dim]", "system")

            # If we deleted the current session, start a new one
            if hasattr(self, 'session_id') and self.session_id == session_id:
                stream.add_message("[dim]Current session deleted, starting new...[/dim]", "system")
                await self._start_new_session()
                self.action_clear_chat()

            # Clear last_session preference if it was the deleted one
            last_session = await self.db.get_preference(self.PREF_LAST_SESSION_KEY)
            if last_session == session_id:
                await self.db.set_preference(self.PREF_LAST_SESSION_KEY, "")

        except Exception as e:
            stream.add_message(f"[red]Delete failed: {e}[/red]", "error")

    async def _delete_all_sessions(self) -> None:
        """Delete all sessions and start fresh."""
        if self.db is None:
            return

        stream = self.query_one(NeuralStream)

        try:
            await self.db.delete_all_sessions()
            await self.db.set_preference(self.PREF_LAST_SESSION_KEY, "")

            stream.add_message("[dim]All sessions deleted[/dim]", "system")
            self.notify("All sessions deleted", severity="information")

            # Start a fresh session
            await self._start_new_session()
            self.action_clear_chat()

        except Exception as e:
            stream.add_message(f"[red]Delete all failed: {e}[/red]", "error")

    # ==================== MODEL SWITCHING ====================

    def action_models(self) -> None:
        """Open model picker modal."""
        asyncio.create_task(self._open_model_picker())

    def action_profiles(self) -> None:
        """Open profile picker modal."""
        asyncio.create_task(self._open_profile_picker())

    async def _open_profile_picker(self) -> None:
        """Open the profile picker modal."""
        from config import get_all_profiles

        profiles = get_all_profiles()
        self.push_screen(
            ProfilePickerModal(profiles=profiles, current_profile=self.current_profile_name),
            self._handle_profile_choice,
        )

    async def _handle_profile_choice(self, result: dict | None) -> None:
        """Handle profile picker result."""
        if not result or not result.get("profile"):
            return

        new_profile = result["profile"]
        if new_profile == self.current_profile_name:
            return  # No change

        stream = self.query_one(NeuralStream)

        # Load the new profile
        await self._load_profile(new_profile)

        # Save profile preference for next launch
        if self.db:
            try:
                await self.db.set_preference(self.PREF_LAST_PROFILE_KEY, new_profile)
            except Exception:
                pass

        # Clear stream and show new profile's splash
        if self.current_profile:
            profile_name = self.current_profile.get("name", new_profile)
            profile_key = profile_name.lower()

            # Clear existing messages
            for child in list(stream.children):
                child.remove()

            # Show new profile's ASCII art
            splash_data = SPLASH_ART.get(profile_key, SPLASH_ART.get("nemo"))
            if splash_data:
                stream.add_message(splash_data.get("ascii", ""), "system")
                stream.add_message(splash_data.get("tagline", ""), "system")

            stream.add_message(f"[bold #8a6ab0]Profile: {profile_name}[/bold #8a6ab0]", "system")

            # Check for preferred model
            preferred = self.current_profile.get("preferred_model")
            if preferred:
                stream.add_message(f"[dim]Preferred model: {preferred}[/dim]", "system")

            stream.add_message("[dim]Ready.[/dim]", "system")

    async def _open_model_picker(self) -> None:
        """Open the model picker modal with current backend's models."""
        stream = self.query_one(NeuralStream)

        if not self.connected or not self.llm_client:
            stream.add_message("[yellow]Not connected to any backend.[/yellow]", "system")
            # Still show the modal so user can switch backends
            self.push_screen(
                ModelPickerModal(models=[], current_model=None, backend=self.current_backend),
                self._on_model_picked,
            )
            return

        try:
            models = await self.llm_client.list_models()
            current_model = getattr(self.llm_client, 'current_model', None)
        except Exception as e:
            stream.add_message(f"[yellow]Error listing models: {e}[/yellow]", "system")
            models = []
            current_model = None

        self.push_screen(
            ModelPickerModal(models=models, current_model=current_model, backend=self.current_backend),
            self._on_model_picked,
        )

    def _on_model_picked(self, result: dict | None) -> None:
        """Callback from ModelPickerModal."""
        asyncio.create_task(self._handle_model_choice(result))

    async def _handle_model_choice(self, result: dict | None) -> None:
        """Handle model picker result."""
        if not result:
            return

        stream = self.query_one(NeuralStream)
        status = self.query_one(StatusBar)

        if result.get("action") == "switch_backend":
            new_backend = result.get("backend")
            if new_backend and new_backend != self.current_backend:
                await self._switch_backend(new_backend)
                # Re-open the picker with new backend
                await self._open_model_picker()
            return

        if result.get("action") == "switch_model":
            model_name = result.get("model")
            if model_name and self.llm_client:
                stream.add_message(f"[dim]Switching to {model_name}...[/dim]", "system")
                try:
                    success = await self.llm_client.switch_model(model_name)
                    if success:
                        new_model = self.llm_client.current_model
                        status.update_status(True, new_model)
                        stream.add_message(f"[green]Switched to {new_model}[/green]", "system")
                        # Update context window estimate
                        ctx_window = self._get_model_context_window(new_model)
                        stream.add_message(f"[dim]Context window: ~{ctx_window:,} tokens[/dim]", "system")
                    else:
                        stream.add_message(f"[red]Failed to switch to {model_name}[/red]", "error")
                except Exception as e:
                    stream.add_message(f"[red]Switch error: {e}[/red]", "error")

    async def _switch_backend(self, backend: str) -> None:
        """Switch between LM Studio and Ollama backends."""
        stream = self.query_one(NeuralStream)
        status = self.query_one(StatusBar)

        old_backend = self.current_backend
        self.current_backend = backend

        stream.add_message(f"[dim]Switching backend: {old_backend} → {backend}[/dim]", "system")

        # Clean up old client
        if self.llm_client:
            try:
                await self.llm_client.cleanup()
            except Exception:
                pass

        # Initialize new client
        try:
            if backend == "lmstudio":
                from llm.lmstudio_client import LMStudioClient
                self.llm_client = LMStudioClient()
            else:  # ollama
                from llm.ollama_client import OllamaClient
                self.llm_client = OllamaClient()

            # Check connection
            if backend == "lmstudio":
                connected = await self.llm_client._check_connection()
            else:
                connected = await self.llm_client._check_ollama_connection()

            if connected:
                models = await self.llm_client.discover_models()
                if models:
                    self.connected = True
                    model_name = self.llm_client.current_model or models[0]
                    status.update_status(True, model_name)
                    stream.add_message(f"[green]Connected to {backend.upper()}[/green]", "system")
                    stream.add_message(f"[dim]Model: {model_name}[/dim]", "system")
                else:
                    self.connected = False
                    stream.add_message(f"[yellow]{backend.upper()} running but no models loaded.[/yellow]", "system")
                    status.update_status(False, "No model")
            else:
                self.connected = False
                stream.add_message(f"[red]Cannot connect to {backend.upper()}.[/red]", "error")
                status.update_status(False)

        except Exception as e:
            self.connected = False
            stream.add_message(f"[red]Backend switch error: {e}[/red]", "error")
            status.update_status(False)

    def _get_model_context_window(self, model_name: str) -> int:
        """Get context window size for a model (best-effort lookup)."""
        if not model_name:
            return self.DEFAULT_CONTEXT_WINDOW

        model_lower = model_name.lower()

        # Check exact matches first, then partial matches
        for key, window in self.MODEL_CONTEXT_WINDOWS.items():
            if key in model_lower:
                return window

        return self.DEFAULT_CONTEXT_WINDOW

    async def connect_to_node(self) -> None:
        """Attempt to connect to LM Studio."""
        stream = self.query_one(NeuralStream)
        status = self.query_one(StatusBar)

        try:
            from llm.lmstudio_client import lmstudio_client

            self.llm_client = lmstudio_client

            # Check connection
            stream.add_message("[dim]Checking LM Studio connection...[/dim]", "system")

            if await self.llm_client._check_connection():
                # Discover models
                models = await self.llm_client.discover_models()
                if models:
                    self.connected = True

                    # Check for preferred model from profile
                    preferred_model = None
                    if self.current_profile:
                        preferred_model = self.current_profile.get("preferred_model")

                    # Try to switch to preferred model if available
                    if preferred_model:
                        # Look for partial match in available models
                        matching = [m for m in models if preferred_model.lower() in m.lower()]
                        if matching:
                            target = matching[0]
                            stream.add_message(f"[dim]Switching to preferred model: {target}[/dim]", "system")
                            success = await self.llm_client.switch_model(target)
                            if success:
                                model_name = self.llm_client.current_model
                            else:
                                model_name = self.llm_client.current_model or models[0]
                                stream.add_message(f"[yellow]Couldn't switch to preferred model, using {model_name}[/yellow]", "system")
                        else:
                            model_name = self.llm_client.current_model or models[0]
                            stream.add_message(f"[yellow]Preferred model '{preferred_model}' not found[/yellow]", "system")
                    else:
                        model_name = self.llm_client.current_model or models[0]

                    status.update_status(True, model_name)
                    stream.add_message(f"[green]Connected to LM Studio[/green]", "system")
                    stream.add_message(f"[dim]Model: {model_name}[/dim]", "system")
                    stream.add_message(f"[dim]Available: {', '.join(models[:3])}{'...' if len(models) > 3 else ''}[/dim]", "system")
                    stream.add_message("", "system")
                    stream.add_message("[b]Ready for partnership.[/b]", "node")
                else:
                    stream.add_message("[yellow]LM Studio running but no models loaded.[/yellow]", "system")
                    stream.add_message("[dim]Load a model in LM Studio to continue.[/dim]", "system")
                    status.update_status(False, "No model")
            else:
                stream.add_message("[red]Cannot connect to LM Studio.[/red]", "error")
                stream.add_message("[dim]Start LM Studio and enable the local server.[/dim]", "system")
                status.update_status(False)

        except ImportError as e:
            stream.add_message(f"[red]Import error: {e}[/red]", "error")
            stream.add_message("[dim]Make sure you're running from MythOS directory.[/dim]", "system")
            status.update_status(False)
        except Exception as e:
            stream.add_message(f"[red]Connection error: {e}[/red]", "error")
            status.update_status(False)

    async def _initialize_rag(self) -> None:
        """Initialize RAG system and index workspace if needed."""
        stream = self.query_one(NeuralStream)

        try:
            from rag.retriever import rag_retriever
            from rag.local_ingester import local_ingester
            from rag.vector_store import vector_store

            self.rag_retriever = rag_retriever
            self.local_ingester = local_ingester

            stream.add_message("[dim]Initializing RAG system...[/dim]", "system")

            # Initialize RAG components
            await rag_retriever.initialize()

            # Ensure the Node Primer is indexed even if the corpus was indexed earlier.
            # (The corpus auto-index only runs on a totally empty vector store.)
            try:
                primer_path = workspace_root / "Node Primer (v0.1).md"
                if primer_path.exists() and self.db is not None:
                    primer_rel = str(primer_path.relative_to(workspace_root))
                    primer_url = f"file://{primer_rel}"
                    exists = await self.db.get_document_by_url(primer_url)
                    if not exists:
                        stream.add_message("[dim]Indexing Node Primer...[/dim]", "system")
                        await local_ingester.ingest_file(primer_path)
            except Exception:
                pass

            # Check if we have any indexed documents
            stats = await rag_retriever.get_stats()
            total_vectors = stats.get('vector_store', {}).get('total_vectors', 0)

            if total_vectors == 0:
                stream.add_message("[dim]No indexed documents. Indexing MythEngine corpus...[/dim]", "system")
                # Index the corpus (this may take a moment)
                ingest_stats = await local_ingester.ingest_mythengine_corpus()
                stream.add_message(
                    f"[green]Indexed {ingest_stats.get('files_ingested', 0)} files "
                    f"({ingest_stats.get('total_vectors', 0)} vectors)[/green]",
                    "system"
                )
            else:
                stream.add_message(
                    f"[dim]RAG ready: {total_vectors} vectors indexed[/dim]",
                    "system"
                )

            self.rag_initialized = True

        except Exception as e:
            stream.add_message(f"[yellow]RAG initialization skipped: {e}[/yellow]", "system")
            self.rag_retriever = None
            self.rag_initialized = False

    async def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        """Handle submission from ChatInput (Enter or Ctrl+Enter)."""
        self._reset_input_activity()  # Temporal empathy: user is active
        await self._send_message(event.value)
        # Clear the input after submission
        text_input = self.query_one("#chat-input", ChatInput)
        text_input.text = ""

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle typing activity for temporal empathy."""
        self._reset_input_activity()  # User is typing - room wakes up

    async def action_submit_message(self) -> None:
        """Handle chat input from button or binding."""
        text_input = self.query_one("#chat-input", ChatInput)
        message = text_input.text.strip()
        if not message:
            return
        text_input.text = ""
        await self._send_message(message)

    async def _send_message(self, message: str) -> None:
        """Core message sending logic."""
        if not message:
            return

        stream = self.query_one(NeuralStream)

        # Show user message
        stream.add_message(f"[b]Steward:[/b] {message}", "steward")

        # Track in conversation history
        self.conversation_history.append(("steward", message))
        self._trim_ram_history()

        if not self.connected or not self.llm_client:
            stream.add_message("[red]Not connected to Node.[/red]", "error")
            return

        # Show thinking indicator
        stream.add_message("[dim]Node is thinking...[/dim]", "system")

        try:
            # Build dynamic system prompt based on current state
            from config import build_system_prompt, build_system_prompt_from_profile

            # Get current context band for prompt injection
            current_band = self._update_context_band()

            # Determine if this is first time at High/Critical (for acknowledgment)
            first_warning = False
            if "Critical" in current_band and not self.context_critical_acknowledged:
                first_warning = True
            elif "High" in current_band and not self.context_high_acknowledged:
                first_warning = True

            # Use profile-based prompt if available, otherwise fall back to hardcoded
            if self.current_profile:
                system_prompt = build_system_prompt_from_profile(
                    profile=self.current_profile,
                    mode=self.session_mode,
                    lens=self.session_lens,
                    idle=self.idle_mode,
                    context_band=current_band,
                    context_first_warning=first_warning
                )
            else:
                system_prompt = build_system_prompt(
                    mode=self.session_mode,
                    lens=self.session_lens,
                    idle=self.idle_mode,
                    context_band=current_band,
                    context_first_warning=first_warning
                )

            # Check for memory operations and build context
            context_parts: list[str] = []
            sources_used = []

            # Inject recent conversation so "resume" is real, not vibes.
            history_context = self._format_recent_history(max_turns=self.HISTORY_CONTEXT_TURNS, exclude_latest=True)
            if history_context:
                context_parts.append("Recent conversation:\n" + history_context)

            # Try to load memories for context (direct file access, no MCP needed)
            msg_lower = message.lower()

            try:
                # Check if this is a memory store command
                if msg_lower.startswith(('remember:', 'store:', 'save:')):
                    content = message.split(':', 1)[1].strip() if ':' in message else message
                    # Simple entity extraction
                    entity_name = "note"
                    entity_type = "fact"
                    if 'my name is' in content.lower():
                        parts = content.lower().split('my name is')
                        if len(parts) > 1:
                            entity_name = parts[1].strip().split()[0].capitalize()
                            entity_type = "person"

                    success = await self.store_memory_direct(entity_name, entity_type, content)
                    if success:
                        stream.add_message(f"[green]✓ Memory stored: {entity_name}[/green]", "system")
                        stream.add_message(f"[dim]Content: {content[:50]}{'...' if len(content) > 50 else ''}[/dim]", "system")
                        await self._refresh_memory_display()
                    else:
                        stream.add_message("[red]✗ Failed to store memory[/red]", "error")
                    # This command never went to the Node; don't poison "recent conversation" context with it.
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return  # Don't send memory commands to LLM

                # Check if asking about memories
                elif any(p in msg_lower for p in ['what do you remember', 'what did i tell', 'do you know']):
                    memories = await self.read_memories_direct()
                    if memories:
                        mem = "Known memories:\n"
                        for m in memories:
                            mem += f"- {m.get('name', 'unknown')}: {', '.join(m.get('observations', []))}\n"
                        sources_used.append("Memory Store")
                        self.update_memory_display(memories)
                        stream.add_message(f"[dim]Retrieved {len(memories)} memories[/dim]", "system")
                        context_parts.append(mem.strip())

                # Always load memories as background context
                else:
                    memories = await self.read_memories_direct()
                    if memories:
                        mem = "Background context (memories):\n"
                        for m in memories:
                            mem += f"- {m.get('name', 'unknown')}: {', '.join(m.get('observations', []))}\n"
                        sources_used.append("Memory Store")
                        context_parts.append(mem.strip())

            except Exception as e:
                stream.add_message(f"[red]Memory error: {e}[/red]", "error")

            # RAG retrieval - get relevant documents for this query
            # Skip RAG for simple greetings/casual openers
            greeting_patterns = ['hey', 'hi', 'hello', 'yo', 'sup', 'what\'s up', 'howdy', 'greetings']
            is_greeting = any(msg_lower.strip().startswith(g) for g in greeting_patterns) and len(message.split()) < 5

            if hasattr(self, 'rag_initialized') and self.rag_initialized and self.rag_retriever and not is_greeting:
                try:
                    rag_context = await self.rag_retriever.retrieve_context(message)
                    if rag_context and rag_context.strip():
                        context_parts.append("Relevant documents:\n" + rag_context)
                        # Track which files were used (parse from context)
                        import re
                        file_matches = re.findall(r'\[([^\]]+)\]', rag_context)
                        for match in file_matches[:3]:  # Limit to 3 sources shown
                            if match not in sources_used:
                                sources_used.append(match)
                        # Track RAG in context buckets
                        self.rag_chunks_loaded = [(s, "") for s in file_matches]
                except Exception as e:
                    stream.add_message(f"[dim]RAG retrieval skipped: {e}[/dim]", "system")

            context = "\n\n".join([p for p in context_parts if p and p.strip()]).strip()

            # Update context display with RAM vs RAG distinction
            context_widget = self.query_one("#context-status", Static)
            display_lines = []

            # Always show conversation history (it's always in context)
            if self.conversation_history:
                turns = len(self.conversation_history)
                display_lines.append(f"[dim]💬 History ({turns} turns) — RAM[/dim]")

            # Show file-based sources (these cost tokens)
            for source in sources_used:
                if source == "Memory Store":
                    display_lines.append(f"[cyan]📁 Memory/nemo_memory.json[/cyan]")
                else:
                    # RAG document
                    display_lines.append(f"[green]📄 {source}[/green]")

            if display_lines:
                context_widget.update("\n".join(display_lines))
            else:
                context_widget.update("[dim]No context loaded[/dim]")

            # Generate response (pass conversation history for proper turn awareness)
            # Exclude the current message (already in prompt) from history
            prior_history = self.conversation_history[:-1] if self.conversation_history else []
            response = await self.llm_client.generate(
                prompt=message,
                context=context,
                system_prompt=system_prompt,
                stream=False,
                conversation_history=prior_history
            )

            if response:
                stream.add_message(f"[b]Node:[/b] {response}", "node")
                # Track in conversation history
                self.conversation_history.append(("node", response))
                self._trim_ram_history()
                # Track what sources were used
                self.last_context_sources = sources_used

                # Persist conversation for resume feature
                await self._persist_exchange(message, response, context)
            else:
                stream.add_message("[yellow]No response from Node.[/yellow]", "system")

            # Update context band after exchange
            final_band = self._update_context_band()

            # Mark that Node has acknowledged High/Critical (so it won't repeat)
            if "Critical" in final_band:
                self.context_critical_acknowledged = True
                self.context_high_acknowledged = True  # Critical implies High was passed
            elif "High" in final_band:
                self.context_high_acknowledged = True

        except Exception as e:
            stream.add_message(f"[red]Error: {e}[/red]", "error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        stream = self.query_one(NeuralStream)

        # Lens buttons
        if button_id in ("lens-blue", "lens-red", "lens-purple"):
            # Remove active from all lens buttons, add to clicked one
            for btn_id in ("lens-blue", "lens-red", "lens-purple"):
                btn = self.query_one(f"#{btn_id}", Button)
                btn.remove_class("active")
            event.button.add_class("active")

            if button_id == "lens-blue":
                self.session_lens = "Blue"
                stream.add_message("[dim]Lens: Blue (Opaque) - Grounded mode[/dim]", "system")
            elif button_id == "lens-red":
                self.session_lens = "Red"
                stream.add_message("[dim]Lens: Red (Cracked) - Processing mode[/dim]", "system")
            elif button_id == "lens-purple":
                self.session_lens = "Purple"
                stream.add_message("[dim]Lens: Purple (Prismatic) - Symbolic mode[/dim]", "system")

        # Mode buttons
        elif button_id in ("mode-workshop", "mode-sanctuary"):
            # Remove active from all mode buttons, add to clicked one
            for btn_id in ("mode-workshop", "mode-sanctuary"):
                btn = self.query_one(f"#{btn_id}", Button)
                btn.remove_class("active")
            event.button.add_class("active")

            if button_id == "mode-workshop":
                self.remove_class("mode-sanctuary")
                self.add_class("mode-workshop")
                self.session_mode = "Workshop"
                stream.add_message("[dim]Mode: Workshop - Analysis and building[/dim]", "system")
            elif button_id == "mode-sanctuary":
                self.remove_class("mode-workshop")
                self.add_class("mode-sanctuary")
                self.session_mode = "Sanctuary"
                stream.add_message("[dim]Mode: Sanctuary - Rest and reflection[/dim]", "system")

        # Protocol buttons
        elif button_id == "btn-ticket":
            await self.initiate_ticket_weave()
        elif button_id == "btn-sessions":
            self.action_sessions()
        elif button_id == "btn-models":
            self.action_models()
        elif button_id == "btn-profiles":
            self.action_profiles()

    async def on_directory_tree_file_selected(self, event) -> None:
        """Handle file selection in the workspace tree.

        Design principle: 'MythOS doesn't open files. Files open MythOS behaviors.'
        - Preview file content
        - Add to context
        - Show mode/lens suggestion (non-forcing)
        """
        from config import get_file_suggestion

        file_path = str(event.path)
        self.selected_file = file_path
        stream = self.query_one(NeuralStream)

        # Check if it's actually a file (not directory)
        if not event.path.is_file():
            return

        try:
            # Read file content for preview
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Truncate for preview (first 50 lines or 2000 chars)
            lines = content.split('\n')
            preview_lines = lines[:50]
            preview = '\n'.join(preview_lines)
            if len(preview) > 2000:
                preview = preview[:2000] + "\n... [truncated]"
            elif len(lines) > 50:
                preview += "\n... [truncated]"

            # Get relative path for display
            rel_path = event.path.name

            # Show file loaded message
            stream.add_message(f"[cyan]📄 Loaded: {rel_path}[/cyan]", "system")

            # Show preview (collapsed format)
            stream.add_message(f"[dim]Preview ({len(lines)} lines):[/dim]", "system")
            stream.add_message(f"[dim]{preview[:500]}{'...' if len(preview) > 500 else ''}[/dim]", "system")

            # Update context display
            context_widget = self.query_one("#context-status", Static)
            context_widget.update(f"[green]📄 {rel_path}[/green]")

            # Check for mode/lens suggestion
            suggestion = get_file_suggestion(file_path)
            if suggestion:
                hint = suggestion.get('hint', '')
                suggested_mode = suggestion.get('mode')
                suggested_lens = suggestion.get('lens')

                # Show suggestion (non-forcing)
                suggestion_parts = []
                if suggested_mode:
                    suggestion_parts.append(suggested_mode)
                if suggested_lens:
                    suggestion_parts.append(suggested_lens)

                if suggestion_parts:
                    stream.add_message(
                        f"[dim]💡 {hint}[/dim]",
                        "system"
                    )

            # Log the file access
            await self._log_event("file_opened", {"path": file_path, "lines": len(lines)})

        except Exception as e:
            stream.add_message(f"[red]Cannot read file: {e}[/red]", "error")

    def action_open_external(self) -> None:
        """Open the selected file in the system's default editor."""
        import subprocess
        import platform

        stream = self.query_one(NeuralStream)

        if not self.selected_file:
            stream.add_message("[yellow]No file selected. Click a file in the workspace first.[/yellow]", "system")
            return

        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(self.selected_file)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", self.selected_file], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", self.selected_file], check=True)

            rel_path = Path(self.selected_file).name
            stream.add_message(f"[dim]📤 Opened in external editor: {rel_path}[/dim]", "system")

        except Exception as e:
            stream.add_message(f"[red]Cannot open file: {e}[/red]", "error")

    async def initiate_ticket_weave(self) -> None:
        """Prepare and open the ticket weaving modal with Auto-Loom drafting."""
        # Guard against rapid clicks
        if self._weaving_ticket:
            return
        self._weaving_ticket = True

        # Get last few messages for context
        recent_history = self.conversation_history[-10:] if self.conversation_history else []

        # Notify user that weaving is in progress
        self.notify("The Auto-Loom is drafting...", title="Weaving Ticket", severity="information")
        
        # Default fallback values
        draft = {
            "title": "New Pattern",
            "type": "Observation",
            "origin": "Unknown",
            "description": "",
            "reflections": "",
            "drift": ""
        }

        # Try to use Auto-Loom if connected
        if self.connected and self.llm_client and recent_history:
            try:
                auto_draft = await self._draft_ticket_content(recent_history)
                if auto_draft:
                    draft.update(auto_draft)
            except Exception as e:
                self.notify(f"Auto-Loom failed, using manual mode: {e}", severity="warning")
        
        timestamp = datetime.now().isoformat(timespec='seconds')
        
        # Pre-fill template
        template = f"""# 🧾 Pattern-Ticket

## 📌 Ticket Header

**type:** {draft['type']} (e.g., {draft['title']})

**origin:** {draft['origin']}

**description:** {draft['description']}

## 🔁 Reflections

**The Pattern:**
{draft.get('reflections') or '(What is repeating? What is breaking?)'}

**The Drift:**
{draft.get('drift') or '(Where is the conversation pulling toward?)'}

## 🔒 Symbolic Commitments

* [{'x' if draft.get('symbolic_recursion') else ' '}] This ticket may be referenced in future symbolic recursion
* [{'x' if draft.get('is_threshold') else ' '}] This marks a threshold or beginning

## 🌀 Meta
Timestamp: {timestamp}

## 📁 Filed Under
MythOS / Pattern Tickets / NeMo
"""
        self.push_screen(TicketModal(template), self.finalize_ticket_weave)

    async def _draft_ticket_content(self, history: list) -> dict:
        """Use the LLM to draft ticket content from conversation history."""
        import json
        
        # Format history for the prompt
        log = "\n".join([f"{role}: {content}" for role, content in history])
        
        system_prompt = """You are the Archivist of the Myth Engine.
Your role is to identify emergent patterns in conversation.
Analyze the chat log and output a JSON object with these keys:
- 'title': A short, poetic name for the pattern/insight.
- 'type': The category (e.g., 'Symbolic Echo', 'Protocol', 'Friction Point', 'Insight').
- 'origin': The specific quote or user prompt that triggered it.
- 'description': A 1-sentence functional summary of what this pattern does or means.
- 'reflections': A brief observation about what is repeating or breaking.
- 'drift': Where the conversation seems to be pulling toward - the emerging direction or unspoken question.
- 'symbolic_recursion': Boolean - true if this pattern is likely to recur or be referenced in future conversations.
- 'is_threshold': Boolean - true if this marks a significant beginning, turning point, or breakthrough moment.

Output ONLY valid JSON."""

        response = await self.llm_client.generate(
            prompt=f"Chat Log:\n{log}\n\nDraft the Pattern-Ticket JSON:",
            system_prompt=system_prompt,
            context="", # No RAG needed for this meta-task
            stream=False
        )

        if not response:
            return None

        # Clean up response to ensure it's just JSON
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        return json.loads(text)

    def finalize_ticket_weave(self, content: str | None) -> None:
        """Callback: Save the ticket if content returned."""
        # Clear the weaving guard
        self._weaving_ticket = False

        if not content:
            return

        stream = self.query_one(NeuralStream)
        
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            filename = f"Ticket_{timestamp}.md"
            
            # Ensure directory exists (save to MythOS/Pattern Tickets/)
            save_dir = project_root / "Pattern Tickets" / "NeMo"
            save_dir.mkdir(parents=True, exist_ok=True)

            file_path = save_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            stream.add_message(f"[green]Pattern Ticket woven: {filename}[/green]", "system")
            stream.add_message(f"[dim]Saved to MythOS/{save_dir.relative_to(project_root)}[/dim]", "system")

            # Log event
            asyncio.create_task(self._log_event("pattern_ticket_created", {"filename": filename, "path": str(file_path)}))

        except Exception as e:
            stream.add_message(f"[red]Failed to save ticket: {e}[/red]", "error")

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch toggles."""
        if event.switch.id == "toggle-idleness":
            self.idle_mode = event.value
            stream = self.query_one(NeuralStream)

            # Get mode buttons for visual suspension
            try:
                workshop_btn = self.query_one("#mode-workshop", Button)
                sanctuary_btn = self.query_one("#mode-sanctuary", Button)
            except Exception:
                workshop_btn = sanctuary_btn = None

            if self.idle_mode:
                # STATE TRANSITION: Idleness engaged (overrides mode)
                stream.add_message(
                    f"[bold cyan]🕯 Sacred Idleness engaged[/bold cyan] — {self.session_mode} suspended",
                    "system"
                )
                # Dim mode buttons (visual suspension, not removal)
                if workshop_btn:
                    workshop_btn.disabled = True
                if sanctuary_btn:
                    sanctuary_btn.disabled = True
                # Log event
                asyncio.create_task(self._log_event("idleness_toggled", {"state": True, "suspended_mode": self.session_mode}))
            else:
                # STATE TRANSITION: Idleness released (mode auto-restores)
                stream.add_message(
                    f"[dim]🕯 Sacred Idleness released[/dim] — {self.session_mode} restored",
                    "system"
                )
                # Re-enable mode buttons
                if workshop_btn:
                    workshop_btn.disabled = False
                if sanctuary_btn:
                    sanctuary_btn.disabled = False
                # Log event
                asyncio.create_task(self._log_event("idleness_toggled", {"state": False, "restored_mode": self.session_mode}))

    def action_clear_chat(self) -> None:
        """Clear the chat stream and conversation history."""
        from config import get_themed_ascii, DEFAULT_THEME
        stream = self.query_one(NeuralStream)
        for child in list(stream.children):
            child.remove()
        # Re-show ASCII art after clear
        stream.add_message(get_themed_ascii(DEFAULT_THEME), "system")
        stream.add_message("[dim]Chat cleared. Ready for partnership.[/dim]", "system")
        # Clear context tracking
        self.conversation_history = []
        self.rag_chunks_loaded = []
        self.last_context_sources = []
        self.context_high_acknowledged = False
        self.context_critical_acknowledged = False
        self._last_context_band = "~Low"  # Reset transition tracking
        self._update_context_band()
        # Reset context display
        context_widget = self.query_one("#context-status", Static)
        context_widget.update("[dim]No context loaded[/dim]")

    def _trim_ram_history(self) -> None:
        """Keep RAM history bounded (DB remains the source of truth)."""
        max_pairs = max(1, self.MAX_RAM_EXCHANGES)
        max_turns = max_pairs * 2  # steward + node
        if len(self.conversation_history) > max_turns:
            self.conversation_history = self.conversation_history[-max_turns:]

    def _format_recent_history(self, *, max_turns: int, exclude_latest: bool) -> str:
        """Format recent turns for prompt injection (plain, no markup)."""
        turns = list(self.conversation_history)
        if exclude_latest and turns and turns[-1][0] == "steward":
            turns = turns[:-1]
        if max_turns > 0:
            turns = turns[-max_turns:]

        lines: list[str] = []
        for role, content in turns:
            speaker = "Steward" if role == "steward" else ("Node" if role == "node" else role)
            text = (content or "").strip().replace("\n", " ").strip()
            if len(text) > 300:
                text = text[:297] + "..."
            if text:
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)

    async def _persist_exchange(self, user_message: str, ai_response: str, context_used: str) -> None:
        """Write conversation + session metadata so resume works across restarts."""
        if self.db is None:
            return

        model_used = getattr(self.llm_client, "current_model", None)
        if not model_used:
            try:
                model_used = self.query_one(StatusBar).model_name
            except Exception:
                model_used = None
        model_used = model_used or "unknown"

        try:
            await self.db.add_conversation(
                session_id=self.session_id,
                user_message=user_message,
                ai_response=ai_response,
                model_used=model_used,
                context_used=(context_used[:800] + "...") if len(context_used) > 800 else context_used,
            )

            self._exchange_count += 1
            await self.db.update_session(
                self.session_id,
                message_count=self._exchange_count,
                first_message=user_message if self._exchange_count == 1 else None,
                model_used=model_used,
            )
            await self.db.set_preference(self.PREF_LAST_SESSION_KEY, self.session_id)
        except Exception:
            # Persistence should never break the flow.
            pass

    def action_toggle_sidebar(self) -> None:
        """Toggle sidebar visibility."""
        sidebar = self.query_one("#sidebar-left")
        sidebar.display = not sidebar.display

    def action_insert_newline(self) -> None:
        """Insert a newline into the chat input (Ctrl+J)."""
        try:
            chat_input = self.query_one("#chat-input", ChatInput)
            chat_input.insert("\n")
        except Exception:
            pass

    # --- CONTEXT TRACKING (Phase 2) ---

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate: ~4 chars per token."""
        return int(len(text) * self.AVG_TOKENS_PER_CHAR)

    def _calculate_context_load(self) -> tuple[int, float]:
        """
        Calculate estimated context load.
        Returns (estimated_tokens, ratio).
        """
        # System prompt baseline
        total = self.SYSTEM_PROMPT_ESTIMATE

        # Conversation history
        for role, content in self.conversation_history:
            total += self._estimate_tokens(content)

        # RAG chunks (if any loaded)
        for source, content in self.rag_chunks_loaded:
            total += self._estimate_tokens(content)

        # Get context window for current model (dynamic)
        current_model = getattr(self.llm_client, 'current_model', None) if self.llm_client else None
        context_window = self._get_model_context_window(current_model)

        ratio = total / context_window
        return total, ratio

    def _ratio_to_band(self, ratio: float) -> str:
        """Convert ratio to human-readable band with ~approximation."""
        pct = int(ratio * 100)
        if ratio < 0.40:
            return f"~Low ({pct}%)"
        elif ratio < 0.70:
            return f"~Medium ({pct}%)"
        elif ratio < 0.85:
            return f"~High ({pct}%)"
        else:
            return f"~Critical ({pct}%)"

    # ==================== TEMPORAL EMPATHY ====================

    def _reset_input_activity(self) -> None:
        """Reset input timer and restore border if dimmed."""
        self._last_input_time = time.time()
        if self._idle_dim_active:
            self._idle_dim_active = False
            try:
                stream = self.query_one(NeuralStream)
                stream.remove_class("idle-dim")
            except Exception:
                pass

    def _check_idle_state(self) -> None:
        """Check if user has been idle and dim border accordingly.

        Temporal Empathy: The room breathes with the user.
        After IDLE_THRESHOLD seconds of no input, the border softens.
        """
        elapsed = time.time() - self._last_input_time

        if elapsed >= self.IDLE_THRESHOLD and not self._idle_dim_active:
            # User has been idle - dim the border
            self._idle_dim_active = True
            try:
                stream = self.query_one(NeuralStream)
                stream.add_class("idle-dim")
            except Exception:
                pass

    def _update_context_band(self) -> str:
        """Update the context band display and return current band.

        Surfaces transitions at the moment they happen (Pattern Programming invariant:
        'If state changes → it must be observable').
        """
        tokens, ratio = self._calculate_context_load()
        band = self._ratio_to_band(ratio)
        previous_band = self._last_context_band

        # Detect significant transitions and surface them immediately
        if band != previous_band:
            self._surface_context_transition(previous_band, band)
            self._last_context_band = band

        # Update moon glyph in StatusBar
        try:
            status_bar = self.query_one(StatusBar)
            status_bar.update_context_glyph(band)
        except Exception:
            pass

        return band

    def _surface_context_transition(self, from_band: str, to_band: str) -> None:
        """Surface context band transitions to the user immediately.

        Implements: 'Behavior must be a pure function of declared session state.'
        """
        # Extract severity level from band strings (e.g., "~High (75%)" -> "High")
        def extract_level(band: str) -> str:
            if "Critical" in band:
                return "Critical"
            elif "High" in band:
                return "High"
            elif "Medium" in band:
                return "Medium"
            else:
                return "Low"

        from_level = extract_level(from_band)
        to_level = extract_level(to_band)

        # Only surface transitions that cross severity thresholds
        severity_order = ["Low", "Medium", "High", "Critical"]
        from_idx = severity_order.index(from_level) if from_level in severity_order else 0
        to_idx = severity_order.index(to_level) if to_level in severity_order else 0

        if from_idx == to_idx:
            return  # Same severity level, just percentage change

        try:
            stream = self.query_one(NeuralStream)

            if to_idx > from_idx:
                # Escalation
                if to_level == "Critical":
                    stream.add_message(
                        f"[bold red]⚡ Context: {from_level} → {to_level}[/bold red] — Earlier threads may be dropping.",
                        "system"
                    )
                elif to_level == "High":
                    stream.add_message(
                        f"[yellow]⚡ Context: {from_level} → {to_level}[/yellow] — Responses may narrow.",
                        "system"
                    )
                else:
                    stream.add_message(
                        f"[dim]⚡ Context: {from_level} → {to_level}[/dim]",
                        "system"
                    )
            else:
                # De-escalation (rare but possible after clear)
                stream.add_message(
                    f"[dim]⚡ Context: {from_level} → {to_level}[/dim]",
                    "system"
                )

            # Log the transition event
            asyncio.create_task(self._log_event("context_band_transition", {"from": from_level, "to": to_level}))
        except Exception:
            pass  # UI not ready yet

    def _should_warn_context(self) -> bool:
        """Check if context is high enough to warrant a warning."""
        _, ratio = self._calculate_context_load()
        return ratio >= 0.70

    # ==================== PROTOCOL EVENT LOGGING ====================

    async def _log_event(self, event_type: str, metadata: dict = None) -> None:
        """Log a protocol event to SQLite (non-blocking, fail-safe).

        Valid event_types:
            - consent_checkpoint
            - rupture_logged
            - pattern_ticket_created
            - mode_changed
            - lens_changed
            - idleness_toggled
            - context_band_transition
        """
        if self.db is None:
            return  # Database not initialized, skip silently

        try:
            await self.db.log_protocol_event(self.session_id, event_type, metadata)
        except Exception:
            pass  # Non-fatal: don't interrupt UX for logging failures

    # Memory file path - direct file access (no MCP dependency)
    MEMORY_FILE = workspace_root / "Memory" / "nemo_memory.json"

    async def read_memories_direct(self) -> list:
        """Read memories directly from JSON file (no MCP dependency)."""
        try:
            import json
            if self.MEMORY_FILE.exists():
                with open(self.MEMORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('entities', [])
        except Exception as e:
            stream = self.query_one(NeuralStream)
            stream.add_message(f"[red]Memory read error: {e}[/red]", "error")
        return []

    async def store_memory_direct(self, entity_name: str, entity_type: str, observation: str) -> bool:
        """Store memory directly to JSON file (no MCP dependency)."""
        try:
            import json
            from datetime import datetime

            # Ensure directory exists
            self.MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

            # Load existing data or create new
            if self.MEMORY_FILE.exists():
                with open(self.MEMORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'entities': []}

            # Find or create entity
            entities = data.get('entities', [])
            entity = next((e for e in entities if e.get('name', '').lower() == entity_name.lower()), None)

            if entity:
                # Add to existing entity
                if 'observations' not in entity:
                    entity['observations'] = []
                entity['observations'].append(observation)
                entity['updated'] = datetime.now().isoformat()
            else:
                # Create new entity (use 'type' to match existing format)
                entities.append({
                    'name': entity_name,
                    'type': entity_type,
                    'observations': [observation],
                    'created': datetime.now().isoformat(),
                    'updated': datetime.now().isoformat()
                })
                data['entities'] = entities

            # Write back
            with open(self.MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            stream = self.query_one(NeuralStream)
            stream.add_message(f"[red]Memory store error: {e}[/red]", "error")
            return False

    def update_memory_display(self, memories: list = None) -> None:
        """Update the memory panel in the sidebar."""
        try:
            memory_widget = self.query_one("#memory-status", Static)
            if memories:
                lines = []
                for m in memories[:5]:  # Show max 5
                    name = m.get('name', 'unknown')
                    obs = m.get('observations', [])
                    preview = obs[0][:30] + "..." if obs and len(obs[0]) > 30 else (obs[0] if obs else "")
                    lines.append(f"* {name}: {preview}")
                memory_widget.update("\n".join(lines) if lines else "No memories")
            else:
                # Try to load current memories
                asyncio.create_task(self._refresh_memory_display())
        except Exception:
            pass

    async def _refresh_memory_display(self) -> None:
        """Async helper to refresh memory display using direct file access."""
        try:
            memories = await self.read_memories_direct()
            memory_widget = self.query_one("#memory-status", Static)
            if memories:
                lines = []
                for m in memories[:5]:
                    name = m.get('name', 'unknown')
                    obs = m.get('observations', [])
                    preview = obs[0][:30] + "..." if obs and len(obs[0]) > 30 else (obs[0] if obs else "")
                    lines.append(f"* {name}: {preview}")
                memory_widget.update("\n".join(lines))
            else:
                memory_widget.update("No memories stored")
        except Exception:
            pass


if __name__ == "__main__":
    app = MythIDE()
    app.run()
