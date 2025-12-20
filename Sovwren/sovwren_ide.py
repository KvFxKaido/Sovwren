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
from textual.widgets import Header, Footer, Static, Input, Button, DirectoryTree, Label, Switch, TextArea, TabbedContent, TabPane
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
project_root = Path(__file__).parent          # .../Sovwren/Sovwren
workspace_root = project_root.parent          # .../Sovwren
sys.path.insert(0, str(project_root))


# --- UI COMPONENTS ---

class BookmarkModal(Screen):
    """Modal for weaving a Bookmark."""
    CSS = """
    BookmarkModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #bookmark-dialog {
        width: 80%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    #bookmark-editor {
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
        with Container(id="bookmark-dialog"):
            yield Label("[b]Save Bookmark[/b]", classes="panel-header")
            yield TextArea(self.initial_content, id="bookmark-editor", language="markdown")
            with Horizontal(id="dialog-buttons"):
                yield Button("Cancel", id="btn-cancel", variant="error")
                yield Button("Save", id="btn-save", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            editor = self.query_one("#bookmark-editor", TextArea)
            self.dismiss(editor.text)
        elif event.button.id == "btn-cancel":
            self.dismiss(None)


class CommitModal(Screen):
    """Modal for entering git commit message."""
    CSS = """
    CommitModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #commit-dialog {
        width: 60%;
        height: auto;
        max-height: 50%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    #commit-input {
        width: 100%;
        margin: 1 0;
    }
    #commit-buttons {
        height: auto;
        align: right middle;
    }
    #commit-buttons Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="commit-dialog"):
            yield Label("[b]Commit Message[/b]", classes="panel-header")
            yield Input(placeholder="Enter commit message...", id="commit-input")
            with Horizontal(id="commit-buttons"):
                yield Button("Cancel", id="btn-cancel", variant="error")
                yield Button("Commit", id="btn-commit", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-commit":
            input_widget = self.query_one("#commit-input", Input)
            message = input_widget.value.strip()
            if message:
                self.dismiss(message)
            else:
                self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Allow Enter to submit the commit."""
        message = event.value.strip()
        if message:
            self.dismiss(message)


# Profile-specific splash art
# Full versions for splash screen, compact versions for chat window
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
        "ascii_compact": "═══ NEMO ═══",
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
        "ascii_compact": "═══ ORACLE ═══",
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
        # Point to Sovwren workspace
        yield DirectoryTree(str(workspace_root), id="file-tree")
        yield Label("[b]Memory[/b]", classes="panel-header")
        yield Static("No memories loaded", id="memory-status", classes="info-box")
        yield Label("[b]Last Context[/b]", classes="panel-header")
        yield Static("[dim]No context loaded[/dim]", id="context-status", classes="info-box")


class ProtocolDeck(Vertical):
    """Class IV & V: Protocol Invocation & Idleness."""
    def compose(self) -> ComposeResult:
        yield Label("[b]Lens[/b]", classes="panel-header")
        with Horizontal(classes="button-row"):
            yield Button("🔵", id="lens-blue", classes="lens-btn active")
            yield Button("🔴", id="lens-red", classes="lens-btn")
            yield Button("🟣", id="lens-purple", classes="lens-btn")

        yield Label("[b]Actions[/b]", classes="panel-header")
        yield Button("📑 Bookmark", id="btn-bookmark", classes="proto-btn proto-btn-accent")
        yield Button("🧵 Sessions", id="btn-sessions", classes="proto-btn")
        yield Button("🤖 Models", id="btn-models", classes="proto-btn")
        yield Button("🪞 Profiles", id="btn-profiles", classes="proto-btn")

        yield Label("[b]Presence[/b]", classes="panel-header panel-header-spaced")
        with Horizontal(classes="toggle-row"):
            yield Label("🌙", classes="toggle-label")
            yield Switch(value=False, id="toggle-idleness")

        yield Label("[b]Mode[/b]", classes="panel-header")
        with Horizontal(classes="button-row"):
            yield Button("🛠 Workshop", id="mode-workshop", classes="mode-btn active")
            yield Button("🕯 Sanctuary", id="mode-sanctuary", classes="mode-btn")

        yield Label("[b]Git[/b]", classes="panel-header panel-header-spaced")
        with Horizontal(classes="button-row"):
            yield Button("📥", id="btn-git-pull", classes="git-btn")
            yield Button("📝", id="btn-git-commit", classes="git-btn")
            yield Button("📤", id="btn-git-push", classes="git-btn")

        yield Label("[b]Search[/b]", classes="panel-header panel-header-spaced")
        with Horizontal(classes="toggle-row"):
            yield Label("🌐", classes="toggle-label")
            yield Switch(value=False, id="toggle-search-gate")

        yield Label("[b]Debug[/b]", classes="panel-header panel-header-spaced")
        with Horizontal(classes="toggle-row"):
            yield Label("🔍", classes="toggle-label")
            yield Switch(value=False, id="toggle-rag-debug")


class NeuralStream(ScrollableContainer):
    """The Chat Window."""
    def compose(self) -> ComposeResult:
        # Show themed ASCII art on startup
        from config import get_themed_ascii, DEFAULT_THEME
        yield Static(get_themed_ascii(DEFAULT_THEME), classes="message system")
        yield Static("[dim]Sovwren initialized. Connecting to Node...[/dim]", classes="message system")

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
    profile_name = reactive("NeMo")
    search_gate = reactive("Local")  # "Local" or "Web (Provider)"

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

    def _get_search_indicator(self) -> str:
        """Get search gate indicator."""
        if self.search_gate == "Local":
            return "🔒"  # Closed gate
        return "🌐"  # Open gate (web enabled)

    def _build_status_text(self) -> str:
        """Build the full status text string."""
        status = "Connected" if self.connected else "Disconnected"
        # Escape brackets for Rich markup (otherwise [NeMo] is treated as a style tag)
        return f"\\[{self.profile_name}] Node: {self.model_name} | {status}"

    def compose(self) -> ComposeResult:
        with Horizontal(id="status-bar-content"):
            yield Label(self._get_context_glyph(), id="context-glyph")
            yield Label(self._get_search_indicator(), id="search-glyph")
            yield Label(self._build_status_text(), id="status-text")

    def update_status(self, connected: bool, model: str = ""):
        self.connected = connected
        self.model_name = model or ("Ready" if connected else "Not connected")
        self.query_one("#status-text", Label).update(self._build_status_text())

    def update_profile(self, profile_name: str):
        """Update the profile name in status bar."""
        self.profile_name = profile_name
        try:
            self.query_one("#status-text", Label).update(self._build_status_text())
        except Exception:
            pass

    def update_context_glyph(self, band: str):
        """Update the moon glyph based on context band."""
        self.context_band = band
        try:
            self.query_one("#context-glyph", Label).update(self._get_context_glyph())
        except Exception:
            pass

    def update_search_gate(self, status: str):
        """Update the search gate indicator (Friction Class VI visibility)."""
        self.search_gate = status
        try:
            self.query_one("#search-glyph", Label).update(self._get_search_indicator())
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


# --- TABBED EDITOR ---

class EditorTab(TabPane):
    """A single file tab in the editor."""

    def __init__(self, file_path: str, content: str = "", title: str = None):
        self.file_path = file_path
        self.original_content = content
        self._is_dirty = False

        # Use filename as tab title
        display_title = title or Path(file_path).name
        super().__init__(display_title, id=f"tab-{hash(file_path)}")

    def compose(self) -> ComposeResult:
        # Detect language from extension
        ext = Path(self.file_path).suffix.lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".json": "json",
            ".md": "markdown",
            ".css": "css",
            ".html": "html",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".sql": "sql",
        }
        language = lang_map.get(ext)

        yield TextArea(
            self.original_content,
            id=f"editor-{hash(self.file_path)}",
            language=language,
            show_line_numbers=True,
        )

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    @is_dirty.setter
    def is_dirty(self, value: bool) -> None:
        self._is_dirty = value
        # Update tab title with dirty indicator
        name = Path(self.file_path).name
        if value:
            self.update(f"● {name}")
        else:
            self.update(f"{name}")

    def get_content(self) -> str:
        """Get current editor content."""
        try:
            editor = self.query_one(TextArea)
            return editor.text
        except Exception:
            return self.original_content

    def mark_saved(self) -> None:
        """Mark as saved, update original content."""
        self.original_content = self.get_content()
        self.is_dirty = False


class TabbedEditor(Vertical):
    """Multi-tab code editor panel."""

    def __init__(self):
        super().__init__()
        self.open_files: dict[str, EditorTab] = {}  # path -> tab
        self.active_file: str = None

    def compose(self) -> ComposeResult:
        yield Label("[b]Editor[/b]", classes="panel-header")
        with Horizontal(id="editor-toolbar"):
            yield Button("💾 Save", id="btn-save", classes="editor-btn")
            yield Button("✕ Close", id="btn-close-tab", classes="editor-btn")
            yield Static("", id="editor-status")
        yield TabbedContent(id="editor-tabs")

    async def open_file(self, file_path: str) -> None:
        """Open a file in a new tab (or focus existing)."""
        # Normalize path
        file_path = str(Path(file_path).resolve())

        tabs = self.query_one("#editor-tabs", TabbedContent)

        # If already open, just focus it
        if file_path in self.open_files:
            tab = self.open_files[file_path]
            tabs.active = tab.id
            self.active_file = file_path
            self._update_status()
            return

        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            self.app.notify(f"Cannot open file: {e}", severity="error")
            return

        # Create new tab
        tab = EditorTab(file_path, content)
        self.open_files[file_path] = tab

        # Add the tab using proper API
        await tabs.add_pane(tab)
        tabs.active = tab.id
        self.active_file = file_path
        self._update_status()

    async def close_file(self, file_path: str = None) -> bool:
        """Close a file tab. Returns False if cancelled due to unsaved changes."""
        file_path = file_path or self.active_file
        if not file_path or file_path not in self.open_files:
            return True

        tab = self.open_files[file_path]

        # Check for unsaved changes
        if tab.is_dirty:
            # For now, just warn - could add confirmation dialog
            self.app.notify("Unsaved changes! Save first or changes will be lost.", severity="warning")
            # Still close for now - can enhance later

        # Remove tab using proper API
        tabs = self.query_one("#editor-tabs", TabbedContent)
        await tabs.remove_pane(tab.id)
        del self.open_files[file_path]

        # Update active file
        if self.open_files:
            self.active_file = list(self.open_files.keys())[0]
        else:
            self.active_file = None

        self._update_status()
        return True

    def save_current(self) -> bool:
        """Save the currently active file."""
        if not self.active_file or self.active_file not in self.open_files:
            self.notify("No file to save", severity="warning")
            return False

        tab = self.open_files[self.active_file]
        content = tab.get_content()

        try:
            with open(self.active_file, 'w', encoding='utf-8') as f:
                f.write(content)
            tab.mark_saved()
            self.notify(f"Saved: {Path(self.active_file).name}", severity="information")
            self._update_status()
            return True
        except Exception as e:
            self.notify(f"Save failed: {e}", severity="error")
            return False

    def _update_status(self) -> None:
        """Update the editor status bar."""
        try:
            status = self.query_one("#editor-status", Static)
            if self.active_file:
                name = Path(self.active_file).name
                tab = self.open_files.get(self.active_file)
                dirty = "●" if tab and tab.is_dirty else ""
                status.update(f"{dirty} {name}")
            else:
                status.update("[dim]No file open[/dim]")
        except Exception:
            pass

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Track dirty state when content changes."""
        # Find which tab this belongs to
        for path, tab in self.open_files.items():
            try:
                editor = tab.query_one(TextArea)
                if editor.text != tab.original_content:
                    tab.is_dirty = True
                else:
                    tab.is_dirty = False
            except Exception:
                pass
        self._update_status()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Track which file is active."""
        for path, tab in self.open_files.items():
            if tab.id == event.tab.id:
                self.active_file = path
                self._update_status()
                break


# --- MAIN APP ---

class SovwrenIDE(App):
    CSS = """
    /* AMOLED Theme: True black, soft text, quiet accents
       Rule: "Did this make me notice the interface less?" */

    Screen {
        layout: vertical;
        background: #000000;
    }

    /* Layout Containers - Three Column: Tree | Editor | Chat */
    #main-layout { height: 1fr; }
    #sidebar-left { width: 18%; min-width: 20; height: 100%; border-right: solid #1a1a1a; background: #000000; }
    #editor-panel { width: 40%; height: 100%; border-right: solid #1a1a1a; background: #000000; }
    #chat-panel { width: 1fr; height: 100%; background: #000000; }

    /* Right Panel Layout - ensure ProtocolDeck doesn't overflow */
    ProtocolDeck { height: auto; max-height: 50%; overflow-y: auto; }
    NeuralStream { height: 1fr; min-height: 30%; }

    /* Tabbed Editor */
    TabbedEditor { height: 1fr; }
    #editor-tabs { height: 1fr; background: #000000; }
    #editor-tabs ContentSwitcher { height: 1fr; }
    #editor-tabs TabPane { height: 100%; padding: 0; }
    #editor-tabs TextArea { height: 100%; background: #050505; border: none; }
    #editor-toolbar {
        height: 4;
        background: #0a0a0a;
        border-bottom: solid #1a1a1a;
        align: left middle;
        padding: 0 1;
    }
    .editor-btn {
        min-width: 12;
        height: 3;
        margin-right: 1;
        content-align: center middle;
    }
    #editor-status {
        width: 1fr;
        text-align: right;
        color: #606060;
    }

    /* Tab styling */
    #editor-tabs Tabs {
        background: #0a0a0a;
        height: 2;
    }
    #editor-tabs Tab {
        background: #0a0a0a;
        color: #606060;
        padding: 0 2;
    }
    #editor-tabs Tab.-active {
        background: #1a1a1a;
        color: #a0a0a0;
    }
    #editor-tabs Tab:hover {
        background: #151515;
    }

    /* Class II: File Tree */
    #file-tree { height: 60%; background: #000000; }
    .panel-header {
        padding: 0 1;
        color: #808080;
        text-align: center;
        background: #0a0a0a;
        text-style: bold;
    }
    /* Micro-zoning: extra breathing room between Actions and State sections */
    .panel-header-spaced { margin-top: 1; }
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

    /* Git buttons */
    .git-btn { min-width: 6; margin: 0; }

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
    .hint { color: #3a3a3a; text-style: italic; }  /* Ephemeral scaffolding: faint whisper */
    .card { color: #808080; margin: 1 0; }  /* Session Resume Card */

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
        width: 100%;
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
        ("ctrl+s", "save_file", "Save"),
        ("ctrl+w", "close_tab", "Close Tab"),
        ("f1", "profiles", "Profiles"),
        ("f2", "models", "Models"),
        ("f3", "consent_check", "Consent"),
        ("f4", "log_rupture", "Rupture"),
        ("f5", "toggle_search_gate", "Search Gate"),
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
        self.rag_debug_enabled = False  # RAG Debug Mode toggle

        # Search Gate (Friction Class VI)
        self.search_manager = None  # Initialized on mount
        self.search_gate_enabled = False
        self.last_search_results = []  # Store recent search results for bookmark context
        self.last_search_query = ""    # The query that produced those results

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

        # Bookmark weaving guard
        self._weaving_bookmark = False

        # Temporal empathy: track input activity for border dimming
        self._last_input_time = time.time()
        self._idle_dim_active = False
        self.IDLE_THRESHOLD = 45  # seconds before border dims (midpoint of 30-60)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-layout"):
            # Left: File Tree
            with Vertical(id="sidebar-left"):
                yield WorkspaceTree()

            # Center: Tabbed Editor
            with Vertical(id="editor-panel"):
                yield TabbedEditor()

            # Right: Chat + Controls
            with Vertical(id="chat-panel"):
                yield ProtocolDeck()
                yield NeuralStream()
                with Container(id="input-container"):
                    yield ChatInput(id="chat-input", show_line_numbers=False)
                yield StatusBar()

        yield Footer()

    async def on_mount(self) -> None:
        self.title = "Sovwren IDE v0.1"
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

        # Initialize Search Gate (Friction Class VI)
        await self._initialize_search_gate()

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

            # Update status bar with profile name
            try:
                status_bar = self.query_one(StatusBar)
                status_bar.update_profile(profile.get("name", profile_name))
            except Exception:
                pass

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

    def _format_session_card(self, session: dict, conversations: list) -> str:
        """Format a visual Session Card for resume display.

        Creates a ritual of continuity — returning to a place, not loading a file.
        """
        from datetime import datetime

        # Parse session data
        name = session.get("name") or session.get("first_message_preview") or "Unnamed session"
        if len(name) > 50:
            name = name[:47] + "..."

        message_count = session.get("message_count", 0)
        last_active = session.get("last_active", "")

        # Format timestamp
        time_str = ""
        if last_active:
            try:
                # Parse ISO format from SQLite
                dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
                time_str = dt.strftime("%b %d, %I:%M %p").replace(" 0", " ").lstrip("0")
            except Exception:
                time_str = last_active[:16] if len(last_active) > 16 else last_active

        # Build the card
        lines = []
        lines.append("[dim]┌─ Returning ─────────────────────────────────┐[/dim]")
        lines.append(f"[dim]│[/dim] [bold]{name}[/bold]")

        # Stats line
        stats_parts = []
        if time_str:
            stats_parts.append(f"📅 {time_str}")
        if message_count:
            exchange_word = "exchange" if message_count == 1 else "exchanges"
            stats_parts.append(f"💬 {message_count} {exchange_word}")
        if stats_parts:
            lines.append(f"[dim]│[/dim] [dim]{' · '.join(stats_parts)}[/dim]")

        # Last 2-3 exchanges (condensed)
        if conversations:
            lines.append("[dim]├─────────────────────────────────────────────┤[/dim]")
            # Show last 3 exchanges max, condensed
            recent = conversations[-3:]
            for conv in recent:
                user_msg = (conv.get("user_message") or "")[:60]
                if len(conv.get("user_message", "")) > 60:
                    user_msg += "..."
                ai_msg = (conv.get("ai_response") or "")[:60]
                if len(conv.get("ai_response", "")) > 60:
                    ai_msg += "..."
                lines.append(f"[dim]│[/dim] [steward]› {user_msg}[/steward]")
                lines.append(f"[dim]│[/dim] [#b08ad0]‹ {ai_msg}[/#b08ad0]")

        lines.append("[dim]└─────────────────────────────────────────────┘[/dim]")

        return "\n".join(lines)

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

        # Display Session Card — ritual of continuity, not just "file loaded"
        try:
            stream = self.query_one(NeuralStream)
            card = self._format_session_card(session, conversations)
            stream.add_message(card, "card")
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

    def action_toggle_search_gate(self) -> None:
        """Toggle Search Gate (F5). Friction Class VI - consent for web search."""
        if self.search_manager is None:
            stream = self.query_one(NeuralStream)
            stream.add_message("[yellow]Search Gate not available (no providers configured)[/yellow]", "system")
            return

        # Toggle the gate
        new_state = self.search_manager.toggle_gate()
        self.search_gate_enabled = new_state

        # Update UI
        stream = self.query_one(NeuralStream)
        status_bar = self.query_one(StatusBar)
        status_bar.update_search_gate(self.search_manager.state.status_text())

        # Sync the toggle switch
        try:
            switch = self.query_one("#toggle-search-gate", Switch)
            switch.value = new_state
        except Exception:
            pass

        if new_state:
            provider = self.search_manager.state.provider
            stream.add_message(f"[green]Search Gate opened ({provider})[/green]", "system")
        else:
            stream.add_message("[dim]Search Gate closed (local-only)[/dim]", "system")

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

            # Show new profile's ASCII art (compact version for chat window)
            splash_data = SPLASH_ART.get(profile_key, SPLASH_ART.get("nemo"))
            if splash_data:
                ascii_art = splash_data.get("ascii_compact", splash_data.get("ascii", ""))
                stream.add_message(ascii_art, "system")
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
            stream.add_message("[dim]Make sure you're running from Sovwren directory.[/dim]", "system")
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
                stream.add_message("[dim]No indexed documents. Indexing Sovwren corpus...[/dim]", "system")
                # Index the corpus (this may take a moment)
                ingest_stats = await local_ingester.ingest_sovwren_corpus()
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

    async def _initialize_search_gate(self) -> None:
        """Initialize Search Gate (Friction Class VI).

        The Search Gate defaults to closed (local-only).
        Web search requires explicit consent via toggle.
        """
        stream = self.query_one(NeuralStream)

        try:
            from search import search_manager

            self.search_manager = search_manager

            if search_manager.is_available:
                providers = ", ".join(search_manager.available_providers)
                stream.add_message(f"[dim]Search Gate ready: {providers}[/dim]", "system")
            else:
                stream.add_message("[dim]Search Gate: No providers configured (set GEMINI_API_KEY)[/dim]", "system")

            # Update status bar
            status_bar = self.query_one(StatusBar)
            status_bar.update_search_gate(search_manager.state.status_text())

        except Exception as e:
            stream.add_message(f"[yellow]Search Gate skipped: {e}[/yellow]", "system")
            self.search_manager = None

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
        stream.add_message(f"[b]›[/b] {message}", "steward")

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

            # Search Gate (Friction Class VI) - web search when gate is open
            if self.search_gate_enabled and self.search_manager and not is_greeting:
                try:
                    stream.add_message("[dim]🌐 Searching web...[/dim]", "system")
                    search_results, search_error = await self.search_manager.search(message, max_results=3)

                    if search_error:
                        stream.add_message(f"[yellow]Search: {search_error}[/yellow]", "system")
                    elif search_results:
                        # Store results for bookmark context
                        self.last_search_results = search_results
                        self.last_search_query = message

                        # Inject search results into context (Librarian Pattern)
                        search_context = self.search_manager.format_for_context(search_results)
                        context_parts.append(search_context)
                        sources_used.append(f"Web ({len(search_results)} sources)")

                        # Show citations in chat
                        citations = self.search_manager.format_citations(search_results)
                        stream.add_message(f"[dim]Sources found:[/dim]\n{citations}", "system")
                    else:
                        stream.add_message("[dim]Search returned no results[/dim]", "system")
                except Exception as e:
                    stream.add_message(f"[yellow]Search failed: {e}[/yellow]", "system")

            if hasattr(self, 'rag_initialized') and self.rag_initialized and self.rag_retriever and not is_greeting:
                try:
                    # Call with debug=True if RAG debug mode is enabled
                    if self.rag_debug_enabled:
                        rag_context, rag_debug_info = await self.rag_retriever.retrieve_context(
                            message, debug=True
                        )
                    else:
                        rag_context = await self.rag_retriever.retrieve_context(message)
                        rag_debug_info = None

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

                    # Display RAG debug info if enabled
                    if self.rag_debug_enabled and rag_debug_info:
                        stream.add_message("[dim]───── RAG Debug ─────[/dim]", "hint")
                        chunks = rag_debug_info.get('chunks_found', 0)
                        total_ms = rag_debug_info.get('total_time_ms', 0)
                        stream.add_message(f"[dim]📊 {chunks} chunks | {total_ms}ms[/dim]", "hint")
                        sources = rag_debug_info.get('sources', [])
                        scores = rag_debug_info.get('scores', [])
                        for i, (src, score) in enumerate(zip(sources, scores)):
                            # Truncate long source names
                            src_display = src[:40] + "..." if len(src) > 40 else src
                            stream.add_message(f"[dim]  {i+1}. {src_display} ({score})[/dim]", "hint")
                        ctx_chars = rag_debug_info.get('context_chars', 0)
                        has_conv = "conv" if rag_debug_info.get('has_conversation') else ""
                        has_docs = "docs" if rag_debug_info.get('has_documents') else ""
                        parts = [p for p in [has_conv, has_docs] if p]
                        stream.add_message(f"[dim]💾 {ctx_chars} chars | {' + '.join(parts) if parts else 'empty'}[/dim]", "hint")

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
                stream.add_message(f"[b]‹[/b] {response}", "node")
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
                stream.add_message("[dim]🔵 Grounded[/dim]", "system")
            elif button_id == "lens-red":
                self.session_lens = "Red"
                stream.add_message("[dim]🔴 Processing[/dim]", "system")
            elif button_id == "lens-purple":
                self.session_lens = "Purple"
                stream.add_message("[dim]🟣 Symbolic[/dim]", "system")
                # Ephemeral scaffolding: show one-time hint for first Purple activation
                from config import get_hint_message
                hint = get_hint_message("purple_first")
                if hint:
                    stream.add_message(f"    ↳ {hint}", "hint")

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
                stream.add_message("[dim]🛠 Workshop[/dim]", "system")
            elif button_id == "mode-sanctuary":
                self.remove_class("mode-workshop")
                self.add_class("mode-sanctuary")
                self.session_mode = "Sanctuary"
                stream.add_message("[dim]🕯 Sanctuary[/dim]", "system")
                # Ephemeral scaffolding: show one-time hint for first Sanctuary activation
                from config import get_hint_message
                hint = get_hint_message("sanctuary_first")
                if hint:
                    stream.add_message(f"    ↳ {hint}", "hint")

        # Protocol buttons
        elif button_id == "btn-bookmark":
            await self.initiate_bookmark_weave()
        elif button_id == "btn-sessions":
            self.action_sessions()
        elif button_id == "btn-models":
            self.action_models()
        elif button_id == "btn-profiles":
            self.action_profiles()

        # Editor buttons
        elif button_id == "btn-save":
            self.action_save_file()
        elif button_id == "btn-close-tab":
            await self.action_close_tab()

        # Git buttons
        elif button_id == "btn-git-pull":
            await self._git_pull()
        elif button_id == "btn-git-commit":
            await self._git_commit()
        elif button_id == "btn-git-push":
            await self._git_push()

    async def on_directory_tree_file_selected(self, event) -> None:
        """Handle file selection in the workspace tree.

        Opens the file in the tabbed editor for editing.
        Also notifies the chat stream and shows mode/lens suggestions.
        """
        from config import get_file_suggestion

        file_path = str(event.path)
        self.selected_file = file_path

        # Check if it's actually a file (not directory)
        if not event.path.is_file():
            return

        # Open in tabbed editor
        try:
            editor = self.query_one(TabbedEditor)
            await editor.open_file(file_path)
        except Exception as e:
            self.notify(f"Cannot open file: {e}", severity="error")
            return

        # Get relative path for display
        rel_path = event.path.name

        # Notify chat stream
        try:
            stream = self.query_one(NeuralStream)
            stream.add_message(f"[cyan]📄 Opened: {rel_path}[/cyan]", "system")

            # Check for mode/lens suggestion
            suggestion = get_file_suggestion(file_path)
            if suggestion:
                hint = suggestion.get('hint', '')
                if hint:
                    stream.add_message(f"[dim]💡 {hint}[/dim]", "system")
        except Exception:
            pass

        # Update context display
        try:
            context_widget = self.query_one("#context-status", Static)
            context_widget.update(f"[green]📄 {rel_path}[/green]")
        except Exception:
            pass

        # Log the file access
        await self._log_event("file_opened", {"path": file_path})

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

    def action_save_file(self) -> None:
        """Save the current file in the editor (Ctrl+S)."""
        try:
            editor = self.query_one(TabbedEditor)
            editor.save_current()
        except Exception as e:
            self.notify(f"Save failed: {e}", severity="error")

    async def action_close_tab(self) -> None:
        """Close the current tab in the editor (Ctrl+W)."""
        try:
            editor = self.query_one(TabbedEditor)
            await editor.close_file()
        except Exception as e:
            self.notify(f"Close failed: {e}", severity="error")

    async def initiate_bookmark_weave(self) -> None:
        """Prepare and open the bookmark weaving modal with Auto-Loom drafting."""
        # Guard against rapid clicks
        if self._weaving_bookmark:
            return
        self._weaving_bookmark = True

        # Get last few messages for context
        recent_history = self.conversation_history[-10:] if self.conversation_history else []

        # Notify user that drafting is in progress
        self.notify("Drafting bookmark...", severity="information")

        # Default fallback values
        draft = {
            "title": "Session",
            "description": "",
            "reflections": "",
            "drift": ""
        }

        # Try to use Auto-Loom if connected
        if self.connected and self.llm_client and recent_history:
            try:
                auto_draft = await self._draft_bookmark_content(recent_history)
                if auto_draft:
                    draft.update(auto_draft)
            except Exception as e:
                self.notify(f"Auto-draft failed: {e}", severity="warning")
        
        date_str = datetime.now().strftime("%Y-%m-%d")

        # Build sources section if search results exist
        sources_section = ""
        if self.last_search_results:
            citations = "\n".join(r.to_citation() for r in self.last_search_results)
            sources_section = f"""
## Sources

Query: "{self.last_search_query}"

{citations}
"""

        # Pre-fill template
        template = f"""# {date_str} — {draft['title']}

{draft['description']}

## Context

{draft.get('reflections') or '(What was happening?)'}

## Notes

{draft.get('drift') or '(What emerged?)'}
{sources_section}"""
        self.push_screen(BookmarkModal(template), self.finalize_bookmark_weave)

    async def _draft_bookmark_content(self, history: list) -> dict:
        """Use the LLM to draft bookmark content from conversation history."""
        import json

        # Format history for the prompt
        log = "\n".join([f"{role}: {content}" for role, content in history])

        system_prompt = """Summarize this conversation for a bookmark.
Output a JSON object with these keys:
- 'title': A short name for what happened (3-6 words).
- 'description': One sentence summary of the session.
- 'reflections': Brief context - what was the user working on?
- 'drift': What emerged or was accomplished?

Output ONLY valid JSON."""

        response = await self.llm_client.generate(
            prompt=f"Chat Log:\n{log}\n\nDraft the bookmark JSON:",
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

    def finalize_bookmark_weave(self, content: str | None) -> None:
        """Callback: Save the bookmark if content returned."""
        # Clear the weaving guard
        self._weaving_bookmark = False

        if not content:
            return

        stream = self.query_one(NeuralStream)
        
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y-%m-%d")
            filename = f"{timestamp}.md"
            
            # Ensure directory exists (save to Sovwren/Bookmarks/)
            save_dir = project_root / "Bookmarks"
            save_dir.mkdir(parents=True, exist_ok=True)

            file_path = save_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            stream.add_message(f"[green]Bookmark saved: {filename}[/green]", "system")
            stream.add_message(f"[dim]Saved to {save_dir.relative_to(project_root)}[/dim]", "system")

            # Log event
            asyncio.create_task(self._log_event("bookmark_created", {"filename": filename, "path": str(file_path)}))

        except Exception as e:
            stream.add_message(f"[red]Failed to save bookmark: {e}[/red]", "error")

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
                    f"[bold cyan]🕯 Idle[/bold cyan] — {self.session_mode} suspended",
                    "system"
                )
                # Ephemeral scaffolding: show one-time hint for first Idle activation
                from config import get_hint_message
                hint = get_hint_message("idle_first")
                if hint:
                    stream.add_message(f"    ↳ {hint}", "hint")
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
                    f"[dim]🕯 Idle off[/dim] — {self.session_mode} restored",
                    "system"
                )
                # Re-enable mode buttons
                if workshop_btn:
                    workshop_btn.disabled = False
                if sanctuary_btn:
                    sanctuary_btn.disabled = False
                # Log event
                asyncio.create_task(self._log_event("idleness_toggled", {"state": False, "restored_mode": self.session_mode}))

        elif event.switch.id == "toggle-rag-debug":
            self.rag_debug_enabled = event.value
            stream = self.query_one(NeuralStream)
            if self.rag_debug_enabled:
                stream.add_message("[cyan]🔍 RAG Debug: On[/cyan]", "system")
            else:
                stream.add_message("[dim]🔍 RAG Debug: Off[/dim]", "system")

        elif event.switch.id == "toggle-search-gate":
            # Friction Class VI: Search Gate consent toggle
            if self.search_manager is None:
                stream = self.query_one(NeuralStream)
                stream.add_message("[yellow]Search Gate not available[/yellow]", "system")
                # Reset switch to off
                event.switch.value = False
                return

            stream = self.query_one(NeuralStream)
            if event.value:
                # Opening the gate
                self.search_manager.open_gate()
                self.search_gate_enabled = True
                provider = self.search_manager.state.provider
                stream.add_message(f"[green]🌐 Search Gate opened ({provider})[/green]", "system")
            else:
                # Closing the gate
                self.search_manager.close_gate()
                self.search_gate_enabled = False
                stream.add_message("[dim]🔒 Search Gate closed (local-only)[/dim]", "system")

            # Update status bar
            status_bar = self.query_one(StatusBar)
            status_bar.update_search_gate(self.search_manager.state.status_text())

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
            - bookmark_created
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

    # ==================== GIT OPERATIONS ====================

    async def _git_pull(self) -> None:
        """Pull latest changes from remote."""
        import subprocess
        stream = self.query_one(NeuralStream)
        stream.add_message("[dim]📥 Pulling from remote...[/dim]", "system")

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["git", "pull"],
                cwd=str(workspace_root),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout.strip() or "Already up to date."
                stream.add_message(f"[green]✓ {output}[/green]", "system")
            else:
                error = result.stderr.strip() or result.stdout.strip() or "Pull failed"
                stream.add_message(f"[red]✗ {error}[/red]", "error")
        except Exception as e:
            stream.add_message(f"[red]Git error: {e}[/red]", "error")

    async def _git_commit(self) -> None:
        """Open commit modal and commit staged/all changes."""
        import subprocess
        stream = self.query_one(NeuralStream)

        # First check if there are changes to commit
        try:
            status_result = await asyncio.to_thread(
                subprocess.run,
                ["git", "status", "--porcelain"],
                cwd=str(workspace_root),
                capture_output=True,
                text=True
            )
            if not status_result.stdout.strip():
                stream.add_message("[dim]No changes to commit.[/dim]", "system")
                return
        except Exception as e:
            stream.add_message(f"[red]Git error: {e}[/red]", "error")
            return

        # Show commit modal
        message = await self.push_screen_wait(CommitModal())
        if not message:
            stream.add_message("[dim]Commit cancelled.[/dim]", "system")
            return

        stream.add_message(f"[dim]📝 Committing: {message}[/dim]", "system")

        try:
            # Stage all changes
            await asyncio.to_thread(
                subprocess.run,
                ["git", "add", "-A"],
                cwd=str(workspace_root),
                capture_output=True
            )

            # Commit with message
            result = await asyncio.to_thread(
                subprocess.run,
                ["git", "commit", "-m", message],
                cwd=str(workspace_root),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Extract short info from output
                lines = result.stdout.strip().split('\n')
                summary = lines[0] if lines else "Committed"
                stream.add_message(f"[green]✓ {summary}[/green]", "system")
            else:
                error = result.stderr.strip() or result.stdout.strip() or "Commit failed"
                stream.add_message(f"[red]✗ {error}[/red]", "error")
        except Exception as e:
            stream.add_message(f"[red]Git error: {e}[/red]", "error")

    async def _git_push(self) -> None:
        """Push commits to remote."""
        import subprocess
        stream = self.query_one(NeuralStream)
        stream.add_message("[dim]📤 Pushing to remote...[/dim]", "system")

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["git", "push"],
                cwd=str(workspace_root),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                output = result.stderr.strip() or result.stdout.strip() or "Pushed successfully"
                # Git push outputs to stderr for progress
                if "up-to-date" in output.lower() or "Everything up-to-date" in output:
                    stream.add_message("[dim]Already up to date.[/dim]", "system")
                else:
                    stream.add_message(f"[green]✓ Pushed[/green]", "system")
            else:
                error = result.stderr.strip() or result.stdout.strip() or "Push failed"
                stream.add_message(f"[red]✗ {error}[/red]", "error")
        except Exception as e:
            stream.add_message(f"[red]Git error: {e}[/red]", "error")


if __name__ == "__main__":
    app = SovwrenIDE()
    app.run()
