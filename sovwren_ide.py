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
from textual.widgets import Header, Footer, Static, Input, Button, DirectoryTree, Label, Switch, TextArea, TabbedContent, TabPane, Collapsible, OptionList
from textual.screen import Screen
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message
from textual import events
import asyncio
import os
import sys
import time
import uuid
import shutil
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# Add project root to path for imports
project_root = Path(__file__).parent          # .../Sovwren
workspace_root = project_root / "workspace"   # .../Sovwren/workspace
workspace_root.mkdir(exist_ok=True)           # Ensure it exists
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


class FileImportModal(Screen):
    """Consent gate: import external files into workspace/imports/."""

    def __init__(self, files: list[Path]):
        super().__init__()
        self.files = files

    def compose(self) -> ComposeResult:
        yield Static("[b]Import files into workspace?[/b]")
        yield Static(
            "[dim]These files are outside `workspace/`. Sovwren will copy them into `workspace/imports/` and insert @refs.[/dim]"
        )
        for p in self.files[:8]:
            yield Static(f"• {p}")
        if len(self.files) > 8:
            yield Static(f"[dim]...and {len(self.files) - 8} more[/dim]")
        with Horizontal(id="dialog-buttons"):
            yield Button("Cancel", id="btn-import-cancel", variant="error")
            yield Button("Copy into workspace", id="btn-import-copy", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-import-copy":
            self.dismiss({"action": "copy"})
        else:
            self.dismiss({"action": "cancel"})


class ImportDestinationModal(Screen):
    """Modal for choosing where to save imported files in workspace."""

    CSS = """
    ImportDestinationModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #import-dest-dialog {
        width: 60%;
        height: 60%;
        background: #000000;
        border: solid #1a1a1a;
        padding: 1;
    }
    #import-dest-list {
        height: 1fr;
        margin: 1 0;
        border: solid #1a1a1a;
        background: #050505;
    }
    #import-new-folder {
        width: 100%;
        margin-bottom: 1;
    }
    #import-dest-buttons {
        height: auto;
        align: right middle;
    }
    #import-dest-buttons Button {
        margin-left: 1;
    }
    """

    def __init__(self, files: list[Path], folders: list[str]):
        super().__init__()
        self.files = files
        self.folders = folders

    def compose(self) -> ComposeResult:
        file_names = [f.name for f in self.files]
        file_list = ", ".join(file_names[:3])
        if len(file_names) > 3:
            file_list += f" +{len(file_names) - 3} more"

        with Container(id="import-dest-dialog"):
            yield Label("[b]Import Files[/b]", classes="panel-header")
            yield Static(f"[dim]Files: {file_list}[/dim]")
            yield Static("[dim]Select destination folder:[/dim]")
            yield OptionList(*self.folders, id="import-dest-list")
            yield Input(placeholder="Or create new folder...", id="import-new-folder")
            with Horizontal(id="import-dest-buttons"):
                yield Button("Cancel", id="btn-import-dest-cancel")
                yield Button("Import", id="btn-import-dest-confirm", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-import-dest-confirm":
            # Check for new folder first
            try:
                new_folder_input = self.query_one("#import-new-folder", Input)
                if new_folder_input.value.strip():
                    self.dismiss({"folder": new_folder_input.value.strip(), "files": self.files})
                    return
            except Exception:
                pass

            # Otherwise use selected folder
            try:
                folder_list = self.query_one("#import-dest-list", OptionList)
                if folder_list.highlighted is not None:
                    option = folder_list.get_option_at_index(folder_list.highlighted)
                    self.dismiss({"folder": str(option.prompt), "files": self.files})
                    return
            except Exception:
                pass
            self.dismiss(None)
        else:
            self.dismiss(None)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Double-click or Enter on folder selects it."""
        self.dismiss({"folder": str(event.option.prompt), "files": self.files})


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
    "sovwren": {
        "ascii": r"""
███████╗ ██████╗ ██╗   ██╗██╗    ██╗██████╗ ███████╗███╗   ██╗
██╔════╝██╔═══██╗██║   ██║██║    ██║██╔══██╗██╔════╝████╗  ██║
███████╗██║   ██║██║   ██║██║ █╗ ██║██████╔╝█████╗  ██╔██╗ ██║
╚════██║██║   ██║╚██╗ ██╔╝██║███╗██║██╔══██╗██╔══╝  ██║╚██╗██║
███████║╚██████╔╝ ╚████╔╝ ╚███╔███╔╝██║  ██║███████╗██║ ╚████║
╚══════╝ ╚═════╝   ╚═══╝   ╚══╝╚══╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝
        """,
        "ascii_compact": "═══ SOVWREN ═══",
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
    #splash-hint {
        text-align: center;
        width: 100%;
        margin-top: 2;
        color: #404040;
    }
    """

    def __init__(self, profile: str = "sovwren"):
        super().__init__()
        self.profile = profile
        self.splash_data = SPLASH_ART.get(profile, SPLASH_ART["sovwren"])

    def compose(self) -> ComposeResult:
        ascii_art = self.splash_data.get("ascii", "")

        yield Static(ascii_art, id="splash-art")
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
        align: center middle;  /* Center instead of right to avoid cutoff */
    }
    #session-buttons Button {
        margin-left: 1;
        min-width: 8;  /* Compact buttons for narrow windows */
        max-width: 12;
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
    """Truth Strip companion: essential controls visible, rest collapsed."""

    def compose(self) -> ComposeResult:
        # Essential controls - always visible (Truth Strip answers)
        yield Label("[b]Mode[/b]", classes="panel-header")
        with Horizontal(classes="button-row"):
            workshop_btn = Button("🛠 Workshop", id="mode-workshop", classes="mode-btn active")
            workshop_btn.tooltip = "Task-focused, direct output"
            yield workshop_btn
            sanctuary_btn = Button("🕯 Sanctuary", id="mode-sanctuary", classes="mode-btn")
            sanctuary_btn.tooltip = "Reflective, pressure-free"
            yield sanctuary_btn

        yield Label("[b]Gates[/b]", classes="panel-header panel-header-spaced")
        with Horizontal(classes="toggle-row"):
            yield Label("🌐", classes="toggle-label")
            yield Switch(value=False, id="toggle-search-gate")
            yield Label("☁️", classes="toggle-label")
            yield Switch(value=False, id="toggle-council-gate")

        # Secondary controls - collapsed by default
        with Collapsible(title="⋮ More", collapsed=True, id="settings-drawer"):
            yield Label("[b]Lens[/b]", classes="panel-header")
            with Horizontal(classes="button-row"):
                blue_btn = Button("🔵", id="lens-blue", classes="lens-btn active")
                blue_btn.tooltip = "Blue - Analytical"
                yield blue_btn
                red_btn = Button("🔴", id="lens-red", classes="lens-btn")
                red_btn.tooltip = "Red - Direct"
                yield red_btn
                purple_btn = Button("🟣", id="lens-purple", classes="lens-btn")
                purple_btn.tooltip = "Purple - Reflective"
                yield purple_btn

            yield Label("[b]Initiative[/b]", classes="panel-header panel-header-spaced")
            with Horizontal(classes="button-row"):
                init_btn = Button("Init: N", id="btn-initiative-cycle", classes="action-btn")
                init_btn.tooltip = "Cycle initiative (Low/Normal/High)"
                yield init_btn
                init_default_btn = Button("★ Default", id="btn-initiative-default", classes="action-btn")
                init_default_btn.tooltip = "Save current initiative as default"
                yield init_default_btn

            yield Label("[b]Actions[/b]", classes="panel-header")
            with Horizontal(classes="button-row"):
                bookmark_btn = Button("📑", id="btn-bookmark", classes="action-btn action-btn-accent")
                bookmark_btn.tooltip = "Bookmark"
                yield bookmark_btn
                sessions_btn = Button("🧵", id="btn-sessions", classes="action-btn")
                sessions_btn.tooltip = "Sessions"
                yield sessions_btn
                models_btn = Button("🤖", id="btn-models", classes="action-btn")
                models_btn.tooltip = "Models"
                yield models_btn
                profiles_btn = Button("🪞", id="btn-profiles", classes="action-btn")
                profiles_btn.tooltip = "Profiles"
                yield profiles_btn

            yield Label("[b]Presence[/b]", classes="panel-header panel-header-spaced")
            with Horizontal(classes="toggle-row"):
                yield Label("🌙 Idle", classes="toggle-label")
                yield Switch(value=False, id="toggle-idleness")

            yield Label("[b]Git[/b]", classes="panel-header panel-header-spaced")
            with Horizontal(classes="button-row"):
                pull_btn = Button("📥", id="btn-git-pull", classes="git-btn")
                pull_btn.tooltip = "Git Pull"
                yield pull_btn
                commit_btn = Button("📝", id="btn-git-commit", classes="git-btn")
                commit_btn.tooltip = "Git Commit"
                yield commit_btn
                push_btn = Button("📤", id="btn-git-push", classes="git-btn")
                push_btn.tooltip = "Git Push"
                yield push_btn

            yield Label("[b]Debug[/b]", classes="panel-header panel-header-spaced")
            with Horizontal(classes="toggle-row"):
                yield Label("🔍 RAG", classes="toggle-label")
                yield Switch(value=False, id="toggle-rag-debug")
            with Horizontal(classes="toggle-row"):
                yield Label("🕐 Time", classes="toggle-label")
                yield Switch(value=True, id="toggle-timestamps")
            with Horizontal(classes="toggle-row"):
                yield Label("📄 Auto", classes="toggle-label")
                yield Switch(value=False, id="toggle-auto-load-refs")


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


class BottomDock(Vertical):
    """Bottom dock for Tall layout - Files, Context, Controls as tabs.
    
    Philosophy: Bottom dock preserves reading width and aligns with scroll direction.
    "Appear, do work, leave." - not permanent co-presence.
    """

    def compose(self) -> ComposeResult:
        with TabbedContent(id="dock-tabs"):
            with TabPane("📁 Files", id="dock-files"):
                yield DirectoryTree(str(workspace_root), id="dock-file-tree")
            
            with TabPane("✍ Editor", id="dock-editor"):
                with Horizontal(id="dock-editor-toolbar"):
                    yield Button("💾 Save", id="btn-dock-save", classes="editor-btn")
                    yield Button("⬆ Expand", id="btn-dock-expand", classes="editor-btn")
                    yield Static("[dim]No file loaded[/dim]", id="dock-editor-status")
                yield TextArea("", id="dock-editor-textarea", show_line_numbers=True)

            with TabPane("📊 Monitor", id="dock-monitor"):
                yield Label("[b]Model[/b]", classes="panel-header")
                yield Static("", id="monitor-model")
                yield Static("", id="monitor-request")
                yield Static("", id="monitor-context")

                yield Label("[b]System[/b]", classes="panel-header panel-header-spaced")
                yield Static("", id="monitor-system")
                yield Static("", id="monitor-disk")

                yield Label("[b]Consent[/b]", classes="panel-header panel-header-spaced")
                yield Static("", id="monitor-consent")
                yield Static("", id="monitor-refs")

            with TabPane("📋 Context", id="dock-context"):
                yield Static("[dim]No context loaded[/dim]", id="dock-context-status")
                yield Static("", id="dock-memory-status")
             
            with TabPane("⚙️ Controls", id="dock-controls"):
                # Mode buttons (essential)
                yield Label("[b]Mode[/b]", classes="panel-header")
                with Horizontal(classes="button-row"):
                    yield Button("🛠 Workshop", id="dock-mode-workshop", classes="mode-btn active")
                    yield Button("🕯 Sanctuary", id="dock-mode-sanctuary", classes="mode-btn")
                
                # Gates (essential)
                yield Label("[b]Gates[/b]", classes="panel-header")
                with Horizontal(classes="toggle-row"):
                    yield Label("🌐", classes="toggle-label")
                    yield Switch(value=False, id="dock-toggle-search-gate")
                    yield Label("☁️", classes="toggle-label")
                    yield Switch(value=False, id="dock-toggle-council-gate")
                
                # Lens
                yield Label("[b]Lens[/b]", classes="panel-header")
                with Horizontal(classes="button-row"):
                    yield Button("🔵", id="dock-lens-blue", classes="lens-btn active")
                    yield Button("🔴", id="dock-lens-red", classes="lens-btn")
                    yield Button("🟣", id="dock-lens-purple", classes="lens-btn")

                # Initiative
                yield Label("[b]Initiative[/b]", classes="panel-header")
                with Horizontal(classes="button-row"):
                    yield Button("Init: N", id="dock-btn-initiative-cycle", classes="action-btn")
                    yield Button("★ Default", id="dock-btn-initiative-default", classes="action-btn")
                
                # Actions
                yield Label("[b]Actions[/b]", classes="panel-header")
                with Horizontal(classes="button-row"):
                    yield Button("📑 Bookmark", id="dock-bookmark-btn")

                # Display
                yield Label("[b]Display[/b]", classes="panel-header")
                with Horizontal(classes="toggle-row"):
                    yield Label("🕐 Timestamps", classes="toggle-label")
                    yield Switch(value=True, id="dock-toggle-timestamps")
                with Horizontal(classes="toggle-row"):
                    yield Label("📄 Auto-load @refs", classes="toggle-label")
                    yield Switch(value=False, id="dock-toggle-auto-load-refs")

    def update_context_display(self, context_text: str):
        """Update the context status in the dock."""
        try:
            self.query_one("#dock-context-status", Static).update(context_text)
        except Exception:
            pass

    def update_memory_display(self, memory_text: str):
        """Update the memory status in the dock."""
        try:
            self.query_one("#dock-memory-status", Static).update(memory_text)
        except Exception:
            pass


class StatusBar(Static):
    """Truth Strip: answers Who, What, Cost in one glance."""
    connected = reactive(False)
    model_name = reactive("Not connected")
    context_band = reactive("Unknown")
    profile_name = reactive("Sovwren")
    search_gate = reactive("Local")  # "Local" or "Web (Provider)"
    council_gate = reactive("Off")  # "Off" or model shortname
    mode = reactive("Workshop")  # "Workshop" or "Sanctuary"
    lens = reactive("Blue")  # "Blue", "Red", or "Purple"
    social_carryover = reactive(True)  # True = warm, False = neutral
    initiative = reactive("Normal")  # "Low", "Normal", or "High"

    # Moon phases for context load: empty → filling → half → full
    CONTEXT_GLYPHS = {
        "Low": "○",      # Empty moon - plenty of space
        "Medium": "◔",   # Quarter - filling up
        "High": "◑",     # Half - getting full
        "Critical": "●", # Full moon - at capacity
    }

    # Lens glyphs for compact display
    LENS_GLYPHS = {
        "Blue": "🔵",
        "Red": "🔴",
        "Purple": "🟣",
    }

    INITIATIVE_GLYPHS = {
        "Low": "L",
        "Normal": "N",
        "High": "H",
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

    def _get_lens_glyph(self) -> str:
        """Get lens glyph for compact display."""
        return self.LENS_GLYPHS.get(self.lens, "🔵")

    def _get_initiative_glyph(self) -> str:
        """Get initiative glyph for compact display."""
        return self.INITIATIVE_GLYPHS.get(self.initiative, "N")

    def _get_search_indicator(self) -> str:
        """Get search gate indicator."""
        if self.search_gate == "Local":
            return "🔒"  # Closed gate
        return "🌐"  # Open gate (web enabled)

    def _get_council_indicator(self) -> str:
        """Get council gate indicator."""
        if self.council_gate == "Off":
            return ""  # Hidden when off
        return "☁️"  # Cloud when enabled

    def _get_mode_indicator(self) -> str:
        """Get mode indicator."""
        if self.mode == "Workshop":
            return "🛠"
        return "🕯"

    def _get_social_indicator(self) -> str:
        """Get social carryover indicator."""
        if self.social_carryover:
            return "🤝"  # Warm - relationship maintained
        return "🔲"  # Neutral - task context only

    def _build_status_text(self) -> str:
        """Build Truth Strip: Mode | Lens | Node | Connected."""
        status = "Connected" if self.connected else "Disconnected"
        init = self.INITIATIVE_GLYPHS.get(self.initiative, "N")
        return f"{self.mode} | Init:{init} | {self.profile_name}: {self.model_name} | {status}"

    def compose(self) -> ComposeResult:
        # Truth Strip layout: [Mode] [Lens] [Social] [Context●] [🔒/🌐] [☁️] [Node info]
        with Horizontal(id="status-bar-content"):
            yield Label(self._get_mode_indicator(), id="mode-glyph")
            yield Label(self._get_lens_glyph(), id="lens-glyph")
            yield Label(self._get_social_indicator(), id="social-glyph")
            yield Label(self._get_initiative_glyph(), id="initiative-glyph")
            yield Label(self._get_context_glyph(), id="context-glyph")
            yield Label(self._get_search_indicator(), id="search-glyph")
            yield Label(self._get_council_indicator(), id="council-glyph")
            yield Label(self._build_status_text(), id="status-text")

    def update_status(self, connected: bool, model: str = ""):
        self.connected = connected
        self.model_name = model or ("Ready" if connected else "Not connected")
        self._refresh_status_text()

    def update_profile(self, profile_name: str):
        """Update the profile name in status bar."""
        self.profile_name = profile_name
        self._refresh_status_text()

    def update_mode(self, mode: str):
        """Update the mode in Truth Strip."""
        self.mode = mode
        try:
            self.query_one("#mode-glyph", Label).update(self._get_mode_indicator())
            self._refresh_status_text()
        except Exception:
            pass

    def update_lens(self, lens: str):
        """Update the lens in Truth Strip."""
        self.lens = lens
        try:
            self.query_one("#lens-glyph", Label).update(self._get_lens_glyph())
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

    def update_council_gate(self, status: str):
        """Update the council gate indicator (Friction Class VI extension)."""
        self.council_gate = status
        try:
            self.query_one("#council-glyph", Label).update(self._get_council_indicator())
        except Exception:
            pass

    def update_social_carryover(self, enabled: bool):
        """Update the social carryover indicator."""
        self.social_carryover = enabled
        try:
            self.query_one("#social-glyph", Label).update(self._get_social_indicator())
        except Exception:
            pass

    def update_initiative(self, initiative: str):
        """Update the initiative indicator."""
        self.initiative = initiative
        try:
            self.query_one("#initiative-glyph", Label).update(self._get_initiative_glyph())
            self._refresh_status_text()
        except Exception:
            pass

    def _refresh_status_text(self):
        """Refresh the status text label."""
        try:
            self.query_one("#status-text", Label).update(self._build_status_text())
        except Exception:
            pass


class ChatInput(TextArea):
    """Custom TextArea that submits on Enter."""

    # Prevent TextArea's default bindings from showing in Footer
    BINDINGS = []

    MAX_MENTION_SUGGESTIONS = 12

    # Available slash commands with descriptions
    SLASH_COMMANDS = [
        ("/help", "Show all keybindings and commands"),
        ("/clear", "Clear chat"),
        ("/save", "Save current file"),
        ("/bookmark", "Save bookmark [name]"),
        ("/session", "Session info"),
        ("/context", "Context info"),
        ("/models", "Open model picker"),
        ("/profiles", "Open profile picker"),
        ("/monitor", "Open Monitor tab"),
        ("/editor", "Open Editor tab"),
        ("/council", "Consult cloud model <query>"),
        ("/seat", "Switch Council model [model]"),
        ("/confirm-yes", "Approve pending action"),
        ("/confirm-no", "Cancel pending action"),
    ]

    class Submitted(Message):
        """Fired when user submits the message."""
        def __init__(self, value: str) -> None:
            self.value = value
            super().__init__()

    def _get_cursor_offset(self) -> int:
        """Return cursor position as a character offset into self.text."""
        text = self.text or ""
        row, col = self.cursor_location
        row = max(0, row)
        col = max(0, col)

        lines = text.split("\n")
        if not lines:
            return 0
        if row >= len(lines):
            return len(text)

        offset = sum(len(lines[i]) + 1 for i in range(row)) + min(col, len(lines[row]))
        return max(0, min(offset, len(text)))

    def _offset_to_location(self, offset: int) -> tuple[int, int]:
        """Convert a character offset into a (row, col) location."""
        text = self.text or ""
        offset = max(0, min(offset, len(text)))
        before = text[:offset]
        row = before.count("\n")
        last_newline = before.rfind("\n")
        col = offset if last_newline == -1 else offset - (last_newline + 1)
        return row, col

    def _current_mention_span(self) -> tuple[int, int, str] | None:
        """Return (start_offset, end_offset, query) for an active @mention token."""
        text = self.text or ""
        cursor = self._get_cursor_offset()

        start = text.rfind("@", 0, cursor + 1)
        if start == -1:
            return None

        if start > 0 and not text[start - 1].isspace():
            return None

        if any(ch.isspace() for ch in text[start:cursor]):
            return None

        end = cursor
        while end < len(text) and not text[end].isspace():
            end += 1

        query = text[start + 1:cursor]
        return start, end, query

    def _current_slash_span(self) -> tuple[int, int, str] | None:
        """Return (start_offset, end_offset, query) for an active /command token.

        Only triggers at the start of input (no text before the /).
        """
        text = self.text or ""
        cursor = self._get_cursor_offset()

        # Only trigger if / is at the very start of the input
        if not text.startswith("/"):
            return None

        # Check if cursor is still within the first "word" (the command)
        # Commands end at whitespace
        end = 0
        while end < len(text) and not text[end].isspace():
            end += 1

        # Only show suggestions if cursor is within the command portion
        if cursor > end:
            return None

        query = text[1:cursor]  # Everything after / up to cursor
        return 0, end, query

    def _set_mention_visibility(self, visible: bool) -> None:
        try:
            suggestions = self.app.query_one("#mention-suggestions", OptionList)
            suggestions.display = visible
        except Exception:
            pass

    def _update_mention_suggestions(self) -> None:
        """Update suggestion list based on current cursor token.

        Checks for slash commands first (at start of input), then @mentions.
        """
        # Track what type of suggestion is active for accept logic
        self._suggestion_type = None

        # Check for slash command first (takes priority)
        slash_span = self._current_slash_span()
        if slash_span is not None:
            _, _, query = slash_span
            query_norm = (query or "").strip().lower()

            # Filter commands by query
            if query_norm:
                matches = [
                    f"{cmd}  [dim]{desc}[/dim]"
                    for cmd, desc in self.SLASH_COMMANDS
                    if query_norm in cmd.lower()
                ]
            else:
                matches = [
                    f"{cmd}  [dim]{desc}[/dim]"
                    for cmd, desc in self.SLASH_COMMANDS
                ]

            if matches:
                try:
                    suggestions = self.app.query_one("#mention-suggestions", OptionList)
                    suggestions.clear_options()
                    suggestions.add_options(matches)
                    suggestions.highlighted = 0
                    suggestions.display = True
                    self._suggestion_type = "slash"
                except Exception:
                    pass
                return
            else:
                self._set_mention_visibility(False)
                return

        # Check for @mention
        mention_span = self._current_mention_span()
        if mention_span is not None:
            _, _, query = mention_span
            query_norm = (query or "").strip().lower()

            file_index = getattr(self.app, "_workspace_file_index", None) or []
            if not file_index:
                self._set_mention_visibility(False)
                return

            if query_norm:
                matches = [p for p in file_index if query_norm in p.lower()]
            else:
                matches = list(file_index)

            matches = matches[: self.MAX_MENTION_SUGGESTIONS]
            if matches:
                try:
                    suggestions = self.app.query_one("#mention-suggestions", OptionList)
                    suggestions.clear_options()
                    suggestions.add_options(matches)
                    suggestions.highlighted = 0
                    suggestions.display = True
                    self._suggestion_type = "mention"
                except Exception:
                    pass
                return

        # No active trigger
        self._set_mention_visibility(False)

    def _accept_mention_suggestion(self) -> bool:
        """Insert the currently highlighted suggestion into the input.

        Handles both slash commands and @mentions based on _suggestion_type.
        """
        suggestion_type = getattr(self, "_suggestion_type", None)

        try:
            suggestions = self.app.query_one("#mention-suggestions", OptionList)
            if not suggestions.display:
                return False
            option = suggestions.highlighted_option
            if option is None:
                return False
            selected = str(option.prompt)
        except Exception:
            return False

        if suggestion_type == "slash":
            # Slash command: extract just the command (before the description)
            span = self._current_slash_span()
            if span is None:
                return False
            start, end, _ = span
            # Parse command from "/<cmd>  [dim]desc[/dim]"
            command = selected.split("  ")[0].strip()
            # For commands that take arguments, add a space; otherwise just the command
            needs_arg = command in ("/council", "/seat", "/bookmark")
            replacement = f"{command} " if needs_arg else command
            start_loc = self._offset_to_location(start)
            end_loc = self._offset_to_location(end)
            self.replace(replacement, start=start_loc, end=end_loc)
            self._set_mention_visibility(False)
            return True

        elif suggestion_type == "mention":
            # @mention: insert the file path
            span = self._current_mention_span()
            if span is None:
                return False
            start, end, _ = span
            start_loc = self._offset_to_location(start)
            end_loc = self._offset_to_location(end)
            self.replace(f"@{selected} ", start=start_loc, end=end_loc)
            self._set_mention_visibility(False)
            return True

        return False

    def _move_mention_highlight(self, delta: int) -> bool:
        """Move the highlighted suggestion up/down if suggestions are visible."""
        try:
            suggestions = self.app.query_one("#mention-suggestions", OptionList)
            if not suggestions.display or suggestions.option_count == 0:
                return False
            idx = suggestions.highlighted if suggestions.highlighted is not None else 0
            idx = max(0, min(idx + delta, suggestions.option_count - 1))
            suggestions.highlighted = idx
            suggestions.scroll_to_highlight()
            return True
        except Exception:
            return False

    def _extract_pasted_file_paths(self, pasted: str) -> list[Path]:
        """Extract file paths from a paste payload (Windows drag-drop typically pastes quoted paths)."""
        import shlex

        raw = (pasted or "").strip()
        if not raw:
            return []

        # Normalize newlines and split into tokens with Windows-friendly quoting.
        raw = raw.replace("\r\n", "\n").replace("\r", "\n")
        tokens: list[str] = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                tokens.extend(shlex.split(line, posix=False))
            except Exception:
                tokens.extend(line.split())

        if not tokens:
            return []

        paths: list[Path] = []
        for token in tokens:
            t = token.strip().strip('"').strip("'")
            if not t:
                continue
            p = Path(t)
            try:
                if p.is_file():
                    paths.append(p.resolve())
            except Exception:
                continue

        # Only treat as "file drop" if every token was a valid file.
        if len(paths) != len(tokens):
            return []
        return paths

    def _on_paste(self, event: events.Paste) -> None:
        """Handle paste, treating pure file-path pastes as @workspace-relative references.

        If pasted paths are outside `workspace/`, request explicit consent to copy them in.
        """
        pasted = getattr(event, "text", "") or ""
        files = self._extract_pasted_file_paths(pasted)
        if not files:
            return super()._on_paste(event)

        in_refs: list[str] = []
        external_files: list[Path] = []
        for file_path in files:
            try:
                rel = file_path.relative_to(workspace_root).as_posix()
                in_refs.append(f"@{rel}")
            except Exception:
                external_files.append(file_path)

        # Insert references at cursor. Keep it explicit; no silent copying/importing.
        event.stop()
        event.prevent_default()
        if in_refs:
            self.insert(" ".join(in_refs) + " ")
        self._set_mention_visibility(False)

        if external_files:
            try:
                self.app.request_workspace_import(external_files)
            except Exception:
                self.app.notify("Dropped file(s) are outside workspace; not attached", severity="warning")
        elif in_refs:
            self.app.notify(f"Attached {len(in_refs)} file(s)", severity="information")

    def _on_key(self, event: events.Key) -> None:
        """Handle Enter for submit."""
        # If mention suggestions are visible, they own a few keys.
        if event.key in ("down", "up"):
            moved = self._move_mention_highlight(1 if event.key == "down" else -1)
            if moved:
                event.stop()
                event.prevent_default()
                return
        # Tab accepts suggestion (standard autocomplete behavior)
        if event.key == "tab":
            if self._accept_mention_suggestion():
                event.stop()
                event.prevent_default()
                return
        # Escape dismisses suggestions
        if event.key == "escape":
            self._set_mention_visibility(False)

        # Enter = dismiss suggestions and submit (not accept)
        if event.key == "enter":
            self._set_mention_visibility(False)
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

        # Update mentions after edits (typing/backspace etc).
        if event.key in ("@", "backspace", "delete", "space") or (len(event.key) == 1):
            self._update_mention_suggestions()


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
        with Horizontal(id="editor-toolbar"):
            save_btn = Button("💾", id="btn-save", classes="editor-btn")
            save_btn.tooltip = "Save (Ctrl+S)"
            yield save_btn
            close_btn = Button("✕", id="btn-close-tab", classes="editor-btn")
            close_btn.tooltip = "Close Tab (Ctrl+W)"
            yield close_btn
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
        align: center top;
        background: #000000;
        /* Dark minimal scrollbar - nearly invisible until needed */
        scrollbar-background: #000000;
        scrollbar-background-hover: #000000;
        scrollbar-background-active: #000000;
        scrollbar-color: #1a1a1a;
        scrollbar-color-hover: #2a2a2a;
        scrollbar-color-active: #3a3a3a;
        scrollbar-corner-color: #000000;
    }

    /* PORTRAIT-FIRST LAYOUT: Spine is canonical, sidebars are summoned */
    #main-layout { height: 1fr; align: center top; }
    #sidebar-left { display: none; width: 18%; min-width: 20; height: 100%; border-right: solid #1a1a1a; background: #000000; }
    #editor-panel { display: none; width: 40%; height: 100%; border-right: solid #1a1a1a; background: #000000; }
    #chat-panel { width: 100%; max-width: 80; height: 100%; background: #000000; }

    /* Spine container - primary cognitive workspace */
    #spine { height: 1fr; width: 100%; }

    /* Spine Content Switching (Tall layout) */
    /* Chat content (NeuralStream + input) - visible by default */
    #chat-content { height: 1fr; display: block; }
    /* Inline spine editor for Tall layout - hidden by default */
    #spine-editor { height: 1fr; display: none; }
    #spine-editor TextArea { height: 100%; background: #050505; border: none; }
    #spine-editor-toolbar {
        height: 3;
        background: #0a0a0a;
        border-bottom: solid #1a1a1a;
        align: left middle;
        padding: 0 1;
    }
    #spine-editor-status { width: 1fr; text-align: right; color: #606060; }

    /* Visibility is controlled via direct class on the containers themselves */
    #chat-content.hidden { display: none; }
    #spine-editor.visible { display: block; }



    /* Bottom Dock - secondary intelligence (Tall layout) */
    #bottom-dock {
        height: auto;
        max-height: 30%;
        width: 100%;
        background: #050505;
        border-top: solid #1a1a1a;
        display: none;  /* Hidden by default */
    }
    #bottom-dock Tabs { background: #0a0a0a; height: 2; }
    #bottom-dock Tab { background: #0a0a0a; color: #606060; padding: 0 2; }
    #bottom-dock Tab.-active { background: #1a1a1a; color: #a0a0a0; }
    #bottom-dock TabPane { padding: 1; }

    /* Dock Editor */
    #dock-editor-toolbar {
        height: 3;
        background: #0a0a0a;
        border-bottom: solid #1a1a1a;
        align: left middle;
        padding: 0 1;
    }
    #dock-editor-status { width: 1fr; text-align: right; color: #606060; }
    #dock-editor TextArea { height: 1fr; background: #050505; border: none; }

    /* Landscape: same spine, more air around it
       Rule: "Landscape stretches space, not functionality." */
    .landscape #main-layout { padding: 0 2; }
    .landscape #chat-panel { max-width: 100; }
    .portrait #main-layout { padding: 0; }

    /* BottomDock - toggle-based visibility (Ctrl+B), not layout-based */
    .dock-visible #bottom-dock { display: block; }

    /* Dock expansion: give the dock the spine and hide chat */
    .dock-expanded #chat-content { display: none; }
    .dock-expanded #spine-editor { display: none; }
    .dock-expanded #bottom-dock { height: 1fr; max-height: 1fr; }
    .dock-expanded #bottom-dock TabPane { height: 1fr; }
    .dock-expanded #dock-editor-textarea { height: 1fr; }


    /* Right Panel Layout - ProtocolDeck with collapsible drawer */
    ProtocolDeck {
        height: auto;
        max-height: 60%;
        overflow-y: auto;
        scrollbar-background: #000000;
        scrollbar-background-hover: #000000;
        scrollbar-background-active: #000000;
        scrollbar-color: #1a1a1a;
        scrollbar-color-hover: #2a2a2a;
        scrollbar-color-active: #3a3a3a;
    }
    /* Collapsible drawer styling */
    #settings-drawer {
        background: #050505;
        border: solid #1a1a1a;
        margin-top: 1;
    }
    #settings-drawer CollapsibleTitle {
        color: #606060;
        background: #0a0a0a;
    }
    #settings-drawer CollapsibleTitle:hover {
        color: #909090;
        background: #151515;
    }
    NeuralStream { height: 1fr; min-height: 30%; }

    /* Tabbed Editor */
    TabbedEditor { height: 1fr; }
    #editor-tabs { height: 1fr; background: #000000; }
    #editor-tabs ContentSwitcher { height: 1fr; }
    #editor-tabs TabPane { height: 100%; padding: 0; }
    #editor-tabs TextArea { height: 100%; background: #050505; border: none; }
    #editor-toolbar {
        height: 3;
        background: #0a0a0a;
        border-bottom: solid #1a1a1a;
        align: left middle;
        padding: 0 1;
    }
    .editor-btn {
        min-width: 5;
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

    /* Switch widgets (toggles) - AMOLED styling */
    Switch {
        background: #1a1a1a;
        border: none;
        height: 1;
        width: 4;
        margin-right: 2;
    }
    Switch > .switch--slider {
        background: #606060;
    }
    Switch:hover > .switch--slider {
        background: #808080;
    }
    Switch.-on > .switch--slider {
        background: #4a7ab0;
    }
    Switch.-on:hover > .switch--slider {
        background: #5a8ac0;
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
    #dock-lens-blue.active { color: #4a7ab0; border: solid #4a7ab0; }
    #dock-lens-red.active { color: #b04a4a; border: solid #b04a4a; }
    #dock-lens-purple.active { color: #7a4ab0; border: solid #7a4ab0; }

    /* Mode buttons */
    .mode-btn { min-width: 8; margin: 0; }
    #mode-workshop.active { color: #4a7ab0; border: solid #4a7ab0; }
    #mode-sanctuary.active { color: #8a6ab0; border: solid #8a6ab0; }
    #dock-mode-workshop.active { color: #4a7ab0; border: solid #4a7ab0; }
    #dock-mode-sanctuary.active { color: #8a6ab0; border: solid #8a6ab0; }

    /* Git buttons */
    .git-btn { min-width: 6; margin: 0; }

    /* Action buttons - compact icon row */
    .action-btn { min-width: 6; margin: 0; }
    .action-btn-accent {
        color: #b0954a;
        border: solid #b0954a;
    }

    /* Chat Area */
    NeuralStream {
        background: #000000;
        padding: 0 1;
        border: solid #1a1a1a;
        scrollbar-background: #000000;
        scrollbar-background-hover: #000000;
        scrollbar-background-active: #000000;
        scrollbar-color: #1a1a1a;
        scrollbar-color-hover: #2a2a2a;
        scrollbar-color-active: #3a3a3a;
    }

    /* Universal scrollbar fallback for any scrollable widget */
    * {
        scrollbar-background: #000000;
        scrollbar-background-hover: #000000;
        scrollbar-background-active: #000000;
        scrollbar-color: #1a1a1a;
        scrollbar-color-hover: #2a2a2a;
        scrollbar-color-active: #3a3a3a;
        scrollbar-corner-color: #000000;
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
        layout: horizontal;
    }
    #btn-attach, #btn-dock-toggle {
        width: 3;
        height: 1;
        min-width: 3;
        background: #000000;
        border: none;
        color: #505050;
        text-align: center;
        margin-top: 1;
    }
    #btn-attach:hover, #btn-dock-toggle:hover {
        color: #808080;
    }
    #btn-attach:focus, #btn-dock-toggle:focus,
    #btn-attach.-active, #btn-dock-toggle.-active {
        background: #000000;
        border: none;
        text-style: none;
    }
    #mention-suggestions {
        display: none;
        height: auto;
        max-height: 8;
        background: #050505;
        border: solid #1a1a1a;
    }
    #mention-suggestions Option {
        padding: 0 1;
    }
    #chat-input {
        width: 1fr;
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
    /* Truth Strip glyphs - fixed width to prevent expansion */
    #mode-glyph, #lens-glyph, #social-glyph, #initiative-glyph, #search-glyph, #council-glyph {
        width: auto;
        margin-right: 1;
        color: #909090;
    }
    #context-glyph {
        width: auto;
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

    /* Node voice inherits Mode accent: "the room colors the voice" */
    .mode-workshop .node {
        color: #6a9ad0;  /* Muted blue — Workshop's analytical tone */
    }
    .mode-sanctuary .node {
        color: #b08ad0;  /* Soft violet — Sanctuary's reflective tone */
    }

    /* Scrollbar thumb follows focus: picks up mode accent on hover/drag */
    .mode-workshop * {
        scrollbar-color-hover: #3a5a7a;  /* Muted blue tint */
        scrollbar-color-active: #4a7ab0;  /* Workshop accent */
    }
    .mode-sanctuary * {
        scrollbar-color-hover: #5a4a6a;  /* Muted violet tint */
        scrollbar-color-active: #8a6ab0;  /* Sanctuary accent */
    }

    /* Header/Footer */
    Header {
        background: #000000;
        color: #606060;
    }
    Footer {
        background: #000000;
        color: #505050;
        dock: bottom;
        height: 1;
        margin-top: 1;
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

    # Essential bindings shown in footer (trim to avoid "icon salad")
    # All bindings still work — /help lists them all
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+s", "save_file", "Save"),
        ("ctrl+l", "clear_chat", "Clear"),
        ("f3", "consent_check", "Consent"),
        ("f1", "show_help", "Help"),
        # Hidden bindings (work but don't clutter footer)
        Binding("ctrl+b", "toggle_dock", "Toggle Dock", show=False),
        Binding("ctrl+r", "sessions", "Sessions", show=False),
        Binding("ctrl+w", "close_tab", "Close Tab", show=False),
        Binding("f2", "models", "Models", show=False),
        Binding("f4", "log_rupture", "Rupture", show=False),
        Binding("f5", "toggle_search_gate", "Search Gate", show=False),
        Binding("f6", "toggle_council_gate", "Council Gate", show=False),
        Binding("f7", "profiles", "Profiles", show=False),
        Binding("ctrl+o", "open_external", "Open in Editor", show=False),
        Binding("ctrl+j", "insert_newline", "Newline", show=False),
        Binding("ctrl+k", "toggle_social_carryover", "Social Carryover", show=False),
        Binding("ctrl+i", "cycle_initiative", "Cycle Initiative", show=False),
        Binding("ctrl+shift+i", "set_initiative_default", "Set Initiative Default", show=False),
        # Spine switching (works in both portrait and landscape)
        Binding("alt+1", "spine_chat", "Chat Spine", show=False),
        Binding("alt+2", "spine_editor", "Editor Spine", show=False),
        Binding("alt+3", "spine_log", "Log Spine", show=False),
        # F-keys as a fallback for terminals that swallow Alt+number
        Binding("f9", "spine_chat", "Chat Spine", show=False),
        Binding("f10", "spine_editor", "Editor Spine", show=False),
        Binding("f11", "spine_log", "Log Spine", show=False),
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
    PREF_LAST_MODEL_KEY = "last_model"  # Preference key for model persistence
    PREF_INITIATIVE_DEFAULT_KEY = "initiative_default"  # Preference key for initiative default (Low/Normal/High)
    PREF_LAST_MODE_KEY = "last_mode"  # Preference key for mode persistence (Workshop/Sanctuary)
    PREF_LAST_LENS_KEY = "last_lens"  # Preference key for lens persistence (Blue/Red/Purple)
    PREF_SHOW_TIMESTAMPS_KEY = "show_timestamps"  # Preference key for timestamp visibility (default: True)
    PREF_AUTO_LOAD_REFS_KEY = "auto_load_refs"  # Preference key for auto-loading @refs (default: False)

    # Verb patterns that authorize @ref file loading (Monday's rule: "Verbs authorize access")
    REF_LOAD_VERBS = [
        "look at", "looking at",
        "read", "reading",
        "review", "reviewing",
        "analyze", "analyzing", "analyse", "analysing",
        "check", "checking",
        "examine", "examining",
        "inspect", "inspecting",
        "see", "seeing",
        "view", "viewing",
        "use", "using",
        "open", "opening",
        "show me", "showing",
    ]

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
        self.current_profile_name = "sovwren"  # Profile key string
        self.assistant_display_name = os.environ.get("SOVWREN_ASSISTANT_NAME", "Sovwren")
        self.session_mode = "Workshop"
        self.session_lens = "Blue"
        self.idle_mode = False
        self.rag_debug_enabled = False  # RAG Debug Mode toggle
        self.show_timestamps = True     # Message timestamps (default ON per Monday's spec)
        self.social_carryover = True    # Social Carryover: warm (True) or neutral (False)
        self.auto_load_refs = False     # Auto-load @refs without consent prompt (default OFF)

        # Pending @ref load consent flow
        self._pending_ref_load: dict | None = None  # {"refs": [...], "message": "..."}
        self._ref_context_injection: str | None = None  # File contents to inject as context

        # Session management (initialized properly in _start_new_session/_resume_session)
        self.db = None
        self.session_id = None
        self._exchange_count = 0

        # Search Gate (Friction Class VI)
        self.search_manager = None  # Initialized on mount
        self.search_gate_enabled = False
        self.last_search_results = []  # Store recent search results for bookmark context
        self.last_search_query = ""    # The query that produced those results

        # Council Gate (Friction Class VI extension - cloud consultation)
        self.council_client = None  # Initialized on mount
        self.council_gate_enabled = False
        self.council_model = None  # Current Council model shortname
        self._pending_council: dict | None = None  # pending /council requiring explicit confirm
        self._pending_confirm: dict | None = None  # pending high-impact operation requiring explicit confirm

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

        # Layout system (Tall Layout Spec)
        self._current_layout = "wide"  # "wide", "tall", "compact"
        self._layout_override = None   # None = auto-detect, "wide"/"tall"/"compact" = forced
        self._current_spine = "chat"   # "chat", "editor", "log" (for Tall layout spine switching)
        self._spine_editor_file = None  # File path currently open in spine editor
        self._spine_editor_original = ""  # Original content for dirty tracking
        self._sidebar_hidden = False
        self._dock_hidden = False
        self._syncing_switches = False

        # Dock editor state
        self._dock_editor_file = None
        self._dock_editor_original = ""

        # Initiative (global default + per-session override)
        self._initiative_default = "Normal"   # Persisted preference
        self._initiative_current = "Normal"   # Session preference (desired)
        self._initiative_overridden = False   # True if changed this session
        self._initiative_forced_low = False   # Idle forces effective Low, restores automatically

        # Monitor: local model request health (minimal, truthful)
        self._llm_inflight = False
        self._last_llm_latency_ms: float | None = None
        self._last_llm_tokens_est: int | None = None
        self._last_llm_tps_est: float | None = None
        self._last_llm_error: str | None = None

    def _update_last_context_displays(self, text: str) -> None:
        """Update both sidebar and Tall-layout dock context panels."""
        try:
            self.query_one("#context-status", Static).update(text)
        except Exception:
            pass
        try:
            self.query_one("#dock-context-status", Static).update(text)
        except Exception:
            pass



    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-layout"):
            # Left: File Tree (hidden in Tall layout)
            with Vertical(id="sidebar-left"):
                yield WorkspaceTree()

            # Center: Tabbed Editor (hidden in Tall layout)
            with Vertical(id="editor-panel"):
                yield TabbedEditor()

            # Right: Chat + Controls (becomes full-width spine in Tall layout)
            with Vertical(id="chat-panel"):
                # Chat content (shown in spine-chat mode)
                with Vertical(id="chat-content"):
                    yield NeuralStream()
                    yield OptionList(id="mention-suggestions")
                    with Container(id="input-container"):
                        yield Button("+", id="btn-attach")
                        yield ChatInput(id="chat-input", show_line_numbers=False)
                        yield Button("☰", id="btn-dock-toggle")
                # Inline spine editor (shown in spine-editor mode, Tall layout only)
                with Vertical(id="spine-editor"):
                    with Horizontal(id="spine-editor-toolbar"):
                        yield Button("💾", id="btn-spine-save", classes="editor-btn")
                        yield Button("✕ Close", id="btn-spine-close", classes="editor-btn")
                        yield Static("", id="spine-editor-status")
                    yield TextArea("", id="spine-editor-textarea", show_line_numbers=True)
                yield StatusBar()
                # Bottom Dock (Tall/Compact; shares spine width/centering)
                yield BottomDock(id="bottom-dock")

        yield Footer()


    async def on_mount(self) -> None:
        self.title = "Sovwren v0.1"
        self.sub_title = ""

        # Set initial mode for border color
        self.add_class("mode-workshop")

        # Set initial layout (Portrait-first: on_resize will detect landscape)
        self.add_class("portrait")

        # Set initial spine mode (Chat visible, Editor hidden)
        self.add_class("spine-chat")

        # Temporal empathy: start idle check timer (checks every 5 seconds)
        self.set_interval(5.0, self._check_idle_state)
        self.set_interval(1.0, self._update_monitor_panel)

        # Workspace file index (for @mentions in chat)
        self._workspace_file_index: list[str] = []
        self._build_workspace_file_index()

        # Initialize database early so we can read profile preference
        try:
            from core.database import Database
            self.db = Database()
            await self.db.initialize()
        except Exception:
            self.db = None

        # Assistant display name (user override)
        if self.db:
            try:
                saved_name = await self.db.get_preference("assistant_name", default=None)
                if saved_name and isinstance(saved_name, str) and saved_name.strip():
                    self.assistant_display_name = saved_name.strip()
            except Exception:
                pass

        try:
            self.query_one(StatusBar).update_profile(self.assistant_display_name)
        except Exception:
            pass

        # Load saved profile preference (default to sovwren)
        splash_profile = "sovwren"
        if self.db:
            try:
                saved_profile = await self.db.get_preference(self.PREF_LAST_PROFILE_KEY, default="sovwren")
                if saved_profile and saved_profile in SPLASH_ART:
                    splash_profile = saved_profile
                    self.current_profile_name = saved_profile
            except Exception:
                pass

            # Load initiative default (Low/Normal/High)
            try:
                saved_initiative = await self.db.get_preference(self.PREF_INITIATIVE_DEFAULT_KEY, default="Normal")
                if saved_initiative in ("Low", "Normal", "High"):
                    self._initiative_default = saved_initiative
                    self._initiative_current = saved_initiative
            except Exception:
                pass

            # Load last mode (Workshop/Sanctuary)
            try:
                saved_mode = await self.db.get_preference(self.PREF_LAST_MODE_KEY, default=None)
                if saved_mode in ("Workshop", "Sanctuary"):
                    self.session_mode = saved_mode
            except Exception:
                pass

            # Load last lens (Blue/Red/Purple)
            try:
                saved_lens = await self.db.get_preference(self.PREF_LAST_LENS_KEY, default=None)
                if saved_lens in ("Blue", "Red", "Purple"):
                    self.session_lens = saved_lens
            except Exception:
                pass

            # Load timestamp preference (default ON)
            try:
                saved_ts = await self.db.get_preference(self.PREF_SHOW_TIMESTAMPS_KEY, default="true")
                self.show_timestamps = saved_ts.lower() == "true"
            except Exception:
                pass

            # Load auto-load refs preference (default OFF)
            try:
                saved_auto = await self.db.get_preference(self.PREF_AUTO_LOAD_REFS_KEY, default="false")
                self.auto_load_refs = saved_auto.lower() == "true"
            except Exception:
                pass

        # Apply restored mode to UI (class + buttons)
        self._apply_mode_to_ui(self.session_mode)
        self._apply_lens_to_ui(self.session_lens)

        # Apply restored timestamp preference to toggles
        try:
            self.query_one("#toggle-timestamps", Switch).value = self.show_timestamps
        except Exception:
            pass
        try:
            self.query_one("#dock-toggle-timestamps", Switch).value = self.show_timestamps
        except Exception:
            pass

        # Apply restored auto-load refs preference to toggles
        try:
            self.query_one("#toggle-auto-load-refs", Switch).value = self.auto_load_refs
        except Exception:
            pass
        try:
            self.query_one("#dock-toggle-auto-load-refs", Switch).value = self.auto_load_refs
        except Exception:
            pass

        # Initialize initiative UI (Truth Strip + buttons)
        self._apply_initiative_mode_defaults()

        # Show ritual entry splash with saved profile (threshold moment)
        # On dismiss, continue to _post_splash_startup
        self.push_screen(SplashScreen(profile=splash_profile), callback=self._post_splash_startup)

    def _build_workspace_file_index(self) -> None:
        """Build a workspace-relative file list for @mention suggestions."""
        try:
            paths: list[str] = []
            for p in workspace_root.rglob("*"):
                if p.is_file():
                    paths.append(p.relative_to(workspace_root).as_posix())
            self._workspace_file_index = sorted(paths)
        except Exception:
            self._workspace_file_index = []

    def _format_bytes(self, n: int | None) -> str:
        if n is None:
            return "?"
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(max(0, n))
        for unit in units:
            if size < 1024 or unit == units[-1]:
                if unit in ("B", "KB"):
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _update_monitor_panel(self) -> None:
        """Update the dock monitor panel (best-effort; never throws)."""
        try:
            backend = "LM Studio" if self.current_backend == "lmstudio" else "Ollama"
            model = ""
            try:
                model = getattr(self.llm_client, "current_model", "") if self.llm_client else ""
            except Exception:
                model = ""

            connected = "Connected" if self.connected else "Disconnected"
            inflight = "in-flight" if self._llm_inflight else "idle"
            latency = f"{self._last_llm_latency_ms}ms" if self._last_llm_latency_ms is not None else "—"
            tps = f"~{self._last_llm_tps_est}/s" if self._last_llm_tps_est is not None else "—"
            err = f" | err: {self._last_llm_error}" if self._last_llm_error else ""

            try:
                self.query_one("#monitor-model", Static).update(f"{backend} | {connected} | {model or 'No model'}")
            except Exception:
                pass
            try:
                self.query_one("#monitor-request", Static).update(f"Request: {inflight} | last: {latency} | t/s: {tps}{err}")
            except Exception:
                pass

            try:
                band = getattr(self, "_last_context_band", "Unknown")
                self.query_one("#monitor-context", Static).update(f"Context: {band}")
            except Exception:
                pass

            # System stats via psutil (optional but expected)
            cpu_text = "CPU: ?"
            ram_text = "RAM: ?"
            try:
                import psutil  # type: ignore

                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                cpu_text = f"CPU: {cpu:.0f}%"
                ram_text = f"RAM: {self._format_bytes(mem.used)} / {self._format_bytes(mem.total)}"
            except Exception:
                pass

            try:
                self.query_one("#monitor-system", Static).update(f"{cpu_text} | {ram_text}")
            except Exception:
                pass

            disk_free = None
            disk_total = None
            try:
                usage = shutil.disk_usage(workspace_root)
                disk_free = usage.free
                disk_total = usage.total
            except Exception:
                pass

            try:
                if disk_free is not None and disk_total is not None:
                    self.query_one("#monitor-disk", Static).update(
                        f"Disk (workspace): {self._format_bytes(disk_free)} free / {self._format_bytes(disk_total)}"
                    )
                else:
                    self.query_one("#monitor-disk", Static).update("Disk (workspace): ?")
            except Exception:
                pass

            # Consent lights / references
            try:
                search = "On" if getattr(self, "search_gate_enabled", False) else "Off"
                council = "On" if getattr(self, "council_gate_enabled", False) else "Off"
                self.query_one("#monitor-consent", Static).update(f"Search Gate: {search} | Council Gate: {council}")
            except Exception:
                pass

            try:
                chat_input = self.query_one("#chat-input", ChatInput)
                refs = [t for t in (chat_input.text or "").split() if t.startswith("@")]
                imports_dir = workspace_root / "imports"
                imported_count = 0
                try:
                    if imports_dir.exists():
                        imported_count = sum(1 for p in imports_dir.rglob("*") if p.is_file())
                except Exception:
                    imported_count = 0
                self.query_one("#monitor-refs", Static).update(f"Refs in input: {len(refs)} | Imports: {imported_count}")
            except Exception:
                pass
        except Exception:
            return

    def _add_to_workspace_file_index(self, rel_posix: str) -> None:
        """Insert a new file into the mention index (keeps list sorted)."""
        if not rel_posix:
            return
        if not hasattr(self, "_workspace_file_index") or self._workspace_file_index is None:
            self._workspace_file_index = []
        if rel_posix in self._workspace_file_index:
            return
        self._workspace_file_index.append(rel_posix)
        self._workspace_file_index.sort()

    def request_workspace_import(self, external_files: list[Path]) -> None:
        """Prompt for consent to copy external files into workspace/imports/."""
        files = [Path(p) for p in (external_files or [])]
        files = [p for p in files if p.exists() and p.is_file()]
        if not files:
            self.notify("No valid files to import", severity="warning")
            return
        self.push_screen(FileImportModal(files), callback=lambda result: self._handle_file_import_result(result, files))

    def _handle_file_import_result(self, result, files: list[Path]) -> None:
        if not result or result.get("action") != "copy":
            self.notify("Import canceled", severity="information")
            return
        asyncio.create_task(self._import_files_into_workspace(files))

    async def _import_files_into_workspace(self, files: list[Path]) -> None:
        """Copy external files into workspace/imports/ and insert @refs into chat input."""
        dest_dir = workspace_root / "imports"
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.notify(f"Import failed: {e}", severity="error")
            return

        imported_refs: list[str] = []
        for src in files:
            try:
                base = src.name
                dest = dest_dir / base
                if dest.exists():
                    stem = dest.stem
                    suffix = dest.suffix
                    n = 2
                    while True:
                        candidate = dest_dir / f"{stem}-{n}{suffix}"
                        if not candidate.exists():
                            dest = candidate
                            break
                        n += 1

                shutil.copy2(src, dest)
                rel = dest.relative_to(workspace_root).as_posix()
                imported_refs.append(f"@{rel}")
                self._add_to_workspace_file_index(rel)
            except Exception as e:
                self.notify(f"Import failed: {src.name} ({e})", severity="error")

        if not imported_refs:
            return

        try:
            chat_input = self.query_one("#chat-input", ChatInput)
            chat_input.insert(" ".join(imported_refs) + " ")
            chat_input.focus()
        except Exception:
            pass

        self.notify(f"Imported {len(imported_refs)} file(s) into workspace/imports/", severity="information")


    def _post_splash_startup(self, result) -> None:
        """Continue startup after splash dismisses."""
        # Run the async startup in a task
        asyncio.create_task(self._initialize_app())

    # --- LAYOUT SYSTEM (Slack-Based Detection) ---

    # Layout constants (in terminal columns)
    SPINE_WIDTH = 80           # Portrait spine width
    LANDSCAPE_SPINE = 100      # Landscape spine width
    LANDSCAPE_PADDING = 4      # Landscape adds 2 cols padding each side

    # Hysteresis thresholds (slack = available width beyond portrait spine)
    # Enter landscape when there's room for wider spine + padding
    LANDSCAPE_ENTER_SLACK = 28  # Need 28 cols slack to enter (80 + 28 = 108)
    LANDSCAPE_EXIT_SLACK = 16   # Stay until slack drops below 16 (80 + 16 = 96)

    def on_resize(self, event) -> None:
        """Apply portrait/landscape class based on available slack.

        Slack-based detection (not aspect ratio):
        - Portrait is the default, always safe
        - Landscape activates only when there's enough room for air
        - Hysteresis prevents flicker during resize

        This aligns with: "Landscape adds air, not features."
        """
        available_slack = self.size.width - self.SPINE_WIDTH
        current_layout = "landscape" if self.has_class("landscape") else "portrait"

        if current_layout == "portrait" and available_slack >= self.LANDSCAPE_ENTER_SLACK:
            # Enough room for landscape — switch
            self.remove_class("portrait")
            self.add_class("landscape")
        elif current_layout == "landscape" and available_slack <= self.LANDSCAPE_EXIT_SLACK:
            # Not enough room anymore — fall back to portrait
            self.remove_class("landscape")
            self.add_class("portrait")
        # Otherwise: hold current state (hysteresis zone)

    def action_toggle_dock(self) -> None:
        """Ctrl+B: Toggle the bottom dock visibility."""
        if self.has_class("dock-visible"):
            self.remove_class("dock-visible")
        else:
            self.add_class("dock-visible")

    def _effective_initiative(self) -> str:
        """Get effective initiative, respecting temporary Idle forcing."""
        if self.idle_mode or self._initiative_forced_low:
            return "Low"
        return self._initiative_current

    def _refresh_initiative_ui(self) -> None:
        """Sync initiative indicators/buttons to current effective state."""
        effective = self._effective_initiative()
        glyph = StatusBar.INITIATIVE_GLYPHS.get(effective, "N")

        try:
            self.query_one(StatusBar).update_initiative(effective)
        except Exception:
            pass

        for btn_id in ("btn-initiative-cycle", "dock-btn-initiative-cycle"):
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                btn.label = f"Init: {glyph}"
            except Exception:
                pass

    def _apply_mode_to_ui(self, mode: str) -> None:
        """Apply mode state to UI (class + buttons + Truth Strip)."""
        # Update CSS class for border color
        if mode == "Workshop":
            self.remove_class("mode-sanctuary")
            self.add_class("mode-workshop")
        else:
            self.remove_class("mode-workshop")
            self.add_class("mode-sanctuary")

        # Update button active states
        for btn_id in ("mode-workshop", "mode-sanctuary", "dock-mode-workshop", "dock-mode-sanctuary"):
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                if (mode == "Workshop" and "workshop" in btn_id) or (mode == "Sanctuary" and "sanctuary" in btn_id):
                    btn.add_class("active")
                else:
                    btn.remove_class("active")
            except Exception:
                pass

        # Update Truth Strip
        try:
            self.query_one(StatusBar).update_mode(mode)
        except Exception:
            pass

    def _apply_lens_to_ui(self, lens: str) -> None:
        """Apply lens state to UI (buttons + Truth Strip)."""
        lens_map = {"Blue": "lens-blue", "Red": "lens-red", "Purple": "lens-purple"}
        target_id = lens_map.get(lens, "lens-blue")

        # Update button active states
        for btn_id in ("lens-blue", "lens-red", "lens-purple", "dock-lens-blue", "dock-lens-red", "dock-lens-purple"):
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                base_id = btn_id.replace("dock-", "")
                if base_id == target_id:
                    btn.add_class("active")
                else:
                    btn.remove_class("active")
            except Exception:
                pass

        # Update Truth Strip
        try:
            self.query_one(StatusBar).update_lens(lens)
        except Exception:
            pass

    def _apply_initiative_mode_defaults(self) -> None:
        """Apply mode-driven initiative defaults unless user overrode this session."""
        if self._initiative_overridden:
            return

        if self.session_mode == "Sanctuary":
            self._initiative_current = "Low"
        else:
            self._initiative_current = self._initiative_default

        self._refresh_initiative_ui()

    def action_cycle_initiative(self) -> None:
        """Cycle initiative: Low → Normal → High."""
        levels = ("Low", "Normal", "High")
        current = self._initiative_current if self._initiative_current in levels else "Normal"
        idx = levels.index(current)
        self._initiative_current = levels[(idx + 1) % len(levels)]
        self._initiative_overridden = True
        self._refresh_initiative_ui()

        if self._effective_initiative() != self._initiative_current:
            self.notify(f"Initiative queued: {self._initiative_current} (Idle forcing Low)", severity="information")
        else:
            self.notify(f"Initiative: {self._initiative_current}", severity="information")

    async def action_set_initiative_default(self) -> None:
        """Persist the current initiative as the global default."""
        if self._initiative_current not in ("Low", "Normal", "High"):
            self.notify("Invalid initiative value", severity="error")
            return

        self._initiative_default = self._initiative_current
        try:
            if self.db:
                await self.db.set_preference(self.PREF_INITIATIVE_DEFAULT_KEY, self._initiative_default)
        except Exception:
            pass

        self.notify(f"Initiative default saved: {self._initiative_default}", severity="information")

    def switch_spine(self, spine: str) -> None:
        """Switch spine content in Tall layout between chat and editor.
        
        This is the core of 'One Spine, Many Organs' — only one thing visible at a time.
        Uses Textual's display property directly for reliable visibility toggling.
        """
        if spine == self._current_spine:
            return

        self._current_spine = spine

        # Toggle visibility using Textual's display property
        try:
            chat_content = self.query_one("#chat-content")
            spine_editor = self.query_one("#spine-editor")

            if spine == "editor":
                chat_content.display = False
                spine_editor.display = True
            else:  # "chat" or any other
                chat_content.display = True
                spine_editor.display = False
        except Exception as e:
            self.notify(f"Spine switch error: {e}", severity="error")

    def action_spine_chat(self) -> None:
        """Alt+1 (or F9): Switch to Chat spine."""

        # Check if spine editor has unsaved changes
        if self._spine_editor_file:
            try:
                textarea = self.query_one("#spine-editor-textarea", TextArea)
                if textarea.text != self._spine_editor_original:
                    self.notify("⚠️ Unsaved changes! Save with 💾 or close to discard", severity="warning")
                    return
            except Exception:
                pass

        self.switch_spine("chat")
        self._spine_editor_file = None
        self.notify("🗨️ Chat", severity="information")

    def action_spine_editor(self) -> None:
        """Alt+2 (or F10): Switch to Editor spine."""

        if self._spine_editor_file:
            # Already have a file open, just switch to editor
            self.switch_spine("editor")
            self.notify(f"📝 {Path(self._spine_editor_file).name}", severity="information")
        else:
            # If a file is highlighted in the tree, open it in the spine editor
            if self.selected_file and Path(self.selected_file).is_file():
                asyncio.create_task(self.open_file_in_spine(self.selected_file))
                return

            # No file selected/open, prompt to select from dock
            try:
                stream = self.query_one(NeuralStream)
                stream.add_message("[dim]Select a file from Files tab in dock[/dim]", "hint")
            except Exception:
                pass

    async def open_file_in_spine(self, file_path: str) -> None:
        """Open a file in the inline spine editor (Tall layout)."""
        file_path = str(Path(file_path).resolve())

        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            self.notify(f"Cannot open file: {e}", severity="error")
            return

        # Store for dirty tracking
        self._spine_editor_file = file_path
        self._spine_editor_original = content

        # Update spine editor textarea
        try:
            textarea = self.query_one("#spine-editor-textarea", TextArea)
            textarea.load_text(content)
            
            # Detect language for syntax highlighting
            ext = Path(file_path).suffix.lower()
            lang_map = {
                ".py": "python", ".js": "javascript", ".ts": "typescript",
                ".json": "json", ".md": "markdown", ".css": "css",
                ".html": "html", ".yaml": "yaml", ".yml": "yaml",
            }
            if ext in lang_map:
                textarea.language = lang_map[ext]

            # Update status
            status = self.query_one("#spine-editor-status", Static)
            status.update(f"{Path(file_path).name}")
        except Exception as e:
            self.notify(f"Error loading file: {e}", severity="error")
            return

        # Switch to editor spine
        self.switch_spine("editor")
        self.notify(f"📝 {Path(file_path).name}", severity="information")

    def action_spine_log(self) -> None:
        """Alt+3 (or F11): Switch to Log/Debug spine (Tall layout)."""
        if self._current_layout == "wide":
            return
        # Log spine not implemented yet, show hint
        try:
            stream = self.query_one(NeuralStream)
            stream.add_message("[dim]Log spine: Debug panel in bottom dock (⋮ More → Debug)[/dim]", "hint")
        except Exception:
            pass

    # --- FILE SELECTION HANDLERS ---

    def on_directory_tree_node_selected(self, event) -> None:
        """Track the currently highlighted node so spine/editor actions can use it."""
        try:
            path = getattr(event, "path", None)
            if path is None:
                return
            path_str = str(path)
            if Path(path_str).is_file():
                self.selected_file = path_str
        except Exception:
            pass

    async def on_directory_tree_file_selected(self, event) -> None:
        """Handle file selection from DirectoryTree (both sidebar and dock)."""
        from config import get_file_suggestion
        file_path = str(event.path)
        self.selected_file = file_path

        # Check if file (not directory)
        if not Path(file_path).is_file():
            return

        # Load into dock editor (scrollable, editable)
        await self.open_file_in_dock_editor(file_path)

        rel_path = Path(file_path).name

        # Notify chat stream + show suggestions
        try:
            stream = self.query_one(NeuralStream)
            stream.add_message(f"[cyan]📄 Opened: {rel_path}[/cyan]", "system")

            suggestion = get_file_suggestion(file_path)
            if suggestion:
                hint = suggestion.get("hint", "")
                if hint:
                    stream.add_message(f"[dim]💡 {hint}[/dim]", "system")
        except Exception:
            pass

        # Update context display (if present)
        try:
            context_widget = self.query_one("#context-status", Static)
            context_widget.update(f"[green]📄 {rel_path}[/green]")
        except Exception:
            pass

        # Log the file access
        try:
            await self._log_event("file_opened", {"path": file_path})
        except Exception:
            pass

    async def _save_spine_editor(self) -> None:
        """Save the current spine editor file."""
        if not self._spine_editor_file:
            self.notify("No file to save", severity="warning")
            return

        try:
            textarea = self.query_one("#spine-editor-textarea", TextArea)
            content = textarea.text

            with open(self._spine_editor_file, 'w', encoding='utf-8') as f:
                f.write(content)

            self._spine_editor_original = content
            self.notify(f"Saved: {Path(self._spine_editor_file).name}", severity="information")
        except Exception as e:
            self.notify(f"Save failed: {e}", severity="error")

    def _close_spine_editor(self) -> None:
        """Close the spine editor and return to chat spine."""
        # Check for unsaved changes
        if self._spine_editor_file:
            try:
                textarea = self.query_one("#spine-editor-textarea", TextArea)
                if textarea.text != self._spine_editor_original:
                    self.notify("⚠️ Unsaved changes will be lost", severity="warning")
            except Exception:
                pass

        # Clear state and switch back to chat
        self._spine_editor_file = None
        self._spine_editor_original = ""
        self.switch_spine("chat")
        self.notify("🗨️ Chat", severity="information")

    async def open_file_in_dock_editor(self, file_path: str) -> None:
        """Load a file into the dock editor TextArea."""
        file_path = str(Path(file_path).resolve())

        # Guard against discarding unsaved changes
        if self._dock_editor_file:
            try:
                textarea = self.query_one("#dock-editor-textarea", TextArea)
                if textarea.text != self._dock_editor_original:
                    self.notify("Unsaved changes in dock editor — save before switching files", severity="warning")
                    return
            except Exception:
                pass

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            self.notify(f"Cannot open file: {e}", severity="error")
            return

        self._dock_editor_file = file_path
        self._dock_editor_original = content

        try:
            textarea = self.query_one("#dock-editor-textarea", TextArea)
            textarea.load_text(content)

            ext = Path(file_path).suffix.lower()
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
            }
            if ext in lang_map:
                textarea.language = lang_map[ext]

            status = self.query_one("#dock-editor-status", Static)
            status.update(f"{Path(file_path).name}")
        except Exception:
            pass

        # Make sure the dock is visible and on the Editor tab
        self.add_class("dock-visible")
        try:
            dock_tabs = self.query_one("#dock-tabs", TabbedContent)
            dock_tabs.active = "dock-editor"
        except Exception:
            pass

    async def _save_dock_editor(self) -> None:
        """Save the current dock editor file."""
        if not self._dock_editor_file:
            self.notify("No dock file to save", severity="warning")
            return

        try:
            textarea = self.query_one("#dock-editor-textarea", TextArea)
            content = textarea.text

            with open(self._dock_editor_file, "w", encoding="utf-8") as f:
                f.write(content)

            self._dock_editor_original = content
            self.notify(f"Saved: {Path(self._dock_editor_file).name}", severity="information")
        except Exception as e:
            self.notify(f"Save failed: {e}", severity="error")

    def _toggle_dock_expanded(self) -> None:
        """Toggle dock expansion (hides chat, gives dock the spine)."""
        self.add_class("dock-visible")
        if self.has_class("dock-expanded"):
            self.remove_class("dock-expanded")
            label = "⬆ Expand"
        else:
            self.add_class("dock-expanded")
            label = "⬇ Collapse"

        try:
            btn = self.query_one("#btn-dock-expand", Button)
            btn.label = label
        except Exception:
            pass


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

        # Initialize Council Gate (Friction Class VI extension)
        await self._initialize_council_gate()

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
            stream.add_message(f"[dim]Profile loaded: {profile_name}[/dim]", "system")

            # Update status bar with profile name
            try:
                status_bar = self.query_one(StatusBar)
                status_bar.update_profile(self.assistant_display_name)
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

    def action_show_help(self) -> None:
        """Show all keybindings and commands (F1 or /help)."""
        stream = self.query_one(NeuralStream)
        stream.add_message("[bold cyan]═══ HELP ═══[/bold cyan]", "system")

        # Keybindings
        stream.add_message("[bold]Keybindings:[/bold]", "system")
        stream.add_message("[dim]  Ctrl+Q   Quit[/dim]", "system")
        stream.add_message("[dim]  Ctrl+S   Save file[/dim]", "system")
        stream.add_message("[dim]  Ctrl+L   Clear chat[/dim]", "system")
        stream.add_message("[dim]  Ctrl+W   Close tab[/dim]", "system")
        stream.add_message("[dim]  Ctrl+B   Toggle panels (Wide: sidebar, Tall: dock)[/dim]", "system")
        stream.add_message("[dim]  Ctrl+R   Sessions[/dim]", "system")
        stream.add_message("[dim]  Ctrl+O   Open in external editor[/dim]", "system")
        stream.add_message("[dim]  Ctrl+J   Insert newline[/dim]", "system")
        stream.add_message("[dim]  Ctrl+K   Toggle social carryover (warm/neutral)[/dim]", "system")
        stream.add_message("[dim]  F1       This help[/dim]", "system")
        stream.add_message("[dim]  F2       Models[/dim]", "system")
        stream.add_message("[dim]  F3       Consent checkpoint[/dim]", "system")
        stream.add_message("[dim]  F4       Log rupture[/dim]", "system")
        stream.add_message("[dim]  F5       Toggle web search[/dim]", "system")
        stream.add_message("[dim]  F6       Toggle cloud council[/dim]", "system")
        stream.add_message("[dim]  F7       Profiles[/dim]", "system")
        stream.add_message("[dim]  F8       Toggle layout override[/dim]", "system")
        stream.add_message("[dim]  Alt+1    Tall: Chat spine[/dim]", "system")
        stream.add_message("[dim]  Alt+2    Tall: Editor spine[/dim]", "system")
        stream.add_message("[dim]  Alt+3    Tall: Log spine (hint)[/dim]", "system")
        stream.add_message("[dim]  F9/F10/F11  Tall: Spine fallback keys[/dim]", "system")

        # Slash commands
        stream.add_message("[bold]Commands:[/bold]", "system")
        stream.add_message("[dim]  /help              Show this help[/dim]", "system")
        stream.add_message("[dim]  /clear             Clear chat[/dim]", "system")
        stream.add_message("[dim]  /save              Save current file[/dim]", "system")
        stream.add_message("[dim]  /bookmark [name]   Save bookmark[/dim]", "system")
        stream.add_message("[dim]  /session           Session info[/dim]", "system")
        stream.add_message("[dim]  /context           Context info[/dim]", "system")
        stream.add_message("[dim]  /models            Open model picker[/dim]", "system")
        stream.add_message("[dim]  /profiles          Open profile picker[/dim]", "system")
        stream.add_message("[dim]  /monitor           Open Monitor tab[/dim]", "system")
        stream.add_message("[dim]  /editor            Open Editor tab[/dim]", "system")
        stream.add_message("[dim]  /council <query>   Consult cloud model[/dim]", "system")
        stream.add_message("[dim]  /seat [model]      Switch Council model[/dim]", "system")
        stream.add_message("[dim]  /confirm-yes       Approve pending action[/dim]", "system")
        stream.add_message("[dim]  /confirm-no        Cancel pending action[/dim]", "system")

    def action_toggle_search_gate(self) -> None:
        """Toggle Search Gate (F5). Friction Class VI - consent for web search."""
        if self.search_manager is None:
            stream = self.query_one(NeuralStream)
            stream.add_message("[yellow]Search Gate not available (no providers configured)[/yellow]", "system")
            return

        # Toggle the switch - the handler shows messages, so just flip it
        try:
            switch = self.query_one("#toggle-search-gate", Switch)
            # Setting value triggers on_switch_changed which handles everything
            switch.value = not self.search_gate_enabled
        except Exception:
            pass

    def action_toggle_council_gate(self) -> None:
        """Toggle Council Gate (F6). Friction Class VI extension - consent for cloud consultation."""
        if self.council_client is None:
            stream = self.query_one(NeuralStream)
            stream.add_message("[yellow]Council Gate not available (not initialized)[/yellow]", "system")
            return

        # Toggle the switch - the handler shows messages, so just flip it
        try:
            switch = self.query_one("#toggle-council-gate", Switch)
            # Setting value triggers on_switch_changed which handles everything
            switch.value = not self.council_gate_enabled
        except Exception:
            pass

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
            await self._queue_session_delete_confirm(result["session_id"], reopen_picker=True)
            return

        if result.get("action") == "delete_all":
            await self._queue_delete_all_sessions_confirm()
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

    async def _queue_session_delete_confirm(self, session_id: str, *, reopen_picker: bool) -> None:
        """Require explicit confirmation before deleting a session."""
        if self.db is None:
            return

        stream = self.query_one(NeuralStream)
        try:
            info = await self.db.get_session(session_id)
        except Exception:
            info = None

        name = None
        msg_count = None
        last_active = None
        if info:
            name = info.get("name") or info.get("first_message_preview")
            msg_count = info.get("message_count")
            last_active = info.get("last_active")

        summary_bits = [f"id={session_id}"]
        if name:
            summary_bits.append(f"name=\"{name}\"")
        if msg_count is not None:
            summary_bits.append(f"messages={msg_count}")
        if last_active:
            summary_bits.append(f"last_active={last_active}")

        stream.add_message("[yellow]Confirm session delete[/yellow]", "system")
        stream.add_message(f"[dim]{' | '.join(summary_bits)}[/dim]", "system")
        stream.add_message("[dim]This is destructive and cannot be undone.[/dim]", "system")
        stream.add_message("[yellow]Type /confirm-yes to delete, or /confirm-no to cancel.[/yellow]", "system")

        self._pending_confirm = {
            "kind": "delete_session",
            "payload": {"session_id": session_id, "reopen_picker": reopen_picker},
            "created_at": time.time(),
            "expires_at": time.time() + 60,
        }

    async def _queue_delete_all_sessions_confirm(self) -> None:
        """Require explicit confirmation before deleting all sessions."""
        if self.db is None:
            return

        stream = self.query_one(NeuralStream)
        try:
            total_count = await self.db.count_sessions()
        except Exception:
            total_count = None

        stream.add_message("[bold red]Confirm DELETE ALL sessions[/bold red]", "system")
        if total_count is not None:
            stream.add_message(f"[dim]Sessions with messages: {total_count}[/dim]", "system")
        stream.add_message("[dim]This is destructive and cannot be undone.[/dim]", "system")
        stream.add_message("[yellow]Type /confirm-yes to delete ALL, or /confirm-no to cancel.[/yellow]", "system")

        self._pending_confirm = {
            "kind": "delete_all_sessions",
            "payload": {},
            "created_at": time.time(),
            "expires_at": time.time() + 60,
        }

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
            splash_data = SPLASH_ART.get(profile_key, SPLASH_ART.get("sovwren"))
            if splash_data:
                ascii_art = splash_data.get("ascii_compact", splash_data.get("ascii", ""))
                stream.add_message(ascii_art, "system")

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
                        # Persist model choice for next startup
                        if self.db:
                            try:
                                await self.db.set_preference(self.PREF_LAST_MODEL_KEY, new_model)
                            except Exception:
                                pass  # Silent fail — persistence is non-critical
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

    # ==================== ATTACH FILE / IMPORT ====================

    def _open_attach_modal(self) -> None:
        """Open system file picker to import files into workspace."""
        # Create hidden tk root for file dialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        # Open file picker
        file_paths = filedialog.askopenfilenames(
            title="Select files to import into workspace",
            parent=root
        )
        root.destroy()

        if not file_paths:
            return  # User cancelled

        files = [Path(f) for f in file_paths]

        # Get list of subfolders in workspace for destination picker
        folders = ["(root)"]  # Root workspace option
        try:
            for item in workspace_root.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    folders.append(item.name)
        except Exception:
            pass

        self.push_screen(ImportDestinationModal(files=files, folders=folders), self._on_import_destination_selected)

    def _on_import_destination_selected(self, result: dict | None) -> None:
        """Handle import destination selection - copy files and insert @refs."""
        if not result or "files" not in result:
            return

        files: list[Path] = result["files"]
        folder_name: str = result.get("folder", "(root)")

        # Determine destination directory
        if folder_name == "(root)":
            dest_dir = workspace_root
        else:
            dest_dir = workspace_root / folder_name
            dest_dir.mkdir(exist_ok=True)

        # Copy files and collect refs
        refs = []
        for file_path in files:
            try:
                dest_path = dest_dir / file_path.name
                # Handle name collision
                if dest_path.exists():
                    stem = file_path.stem
                    suffix = file_path.suffix
                    counter = 1
                    while dest_path.exists():
                        dest_path = dest_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

                shutil.copy2(file_path, dest_path)
                rel_path = dest_path.relative_to(workspace_root).as_posix()
                refs.append(f"@{rel_path}")
            except Exception as e:
                self.notify(f"Failed to copy {file_path.name}: {e}", severity="error")

        if refs:
            try:
                chat_input = self.query_one("#chat-input", ChatInput)
                chat_input.insert(" ".join(refs) + " ")
                chat_input.focus()
                # Rebuild file index to include new files
                self._build_workspace_file_index()
            except Exception:
                pass

    async def _handle_council_command(self, message: str) -> None:
        """Handle /council command for cloud model consultation.

        Usage: /council <query>
        Sends the query to the Council (cloud model) with current context.
        """
        stream = self.query_one(NeuralStream)

        # Extract query from command
        query = message[8:].strip() if len(message) > 8 else ""  # Remove "/council "

        if not query:
            stream.add_message("[yellow]/council requires a query. Usage: /council <your question>[/yellow]", "system")
            # Remove from conversation history
            if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                self.conversation_history.pop()
            return

        # Check if Council is available
        if self.council_client is None:
            stream.add_message("[yellow]Council not available. Set OPENROUTER_API_KEY environment variable.[/yellow]", "system")
            return

        # Check if Council Gate is open (consent)
        if not self.council_gate_enabled:
            stream.add_message("[yellow]Council Gate is closed. Enable it with F6 or the ☁️ toggle.[/yellow]", "system")
            return

        try:
            # Get active file content if editor has a file open
            active_file = None
            try:
                from textual.widgets import TabbedContent
                tabbed = self.query_one("#tabbed-editor", TabbedContent)
                if tabbed.active:
                    # Get current tab's file content
                    active_pane = tabbed.get_pane(tabbed.active)
                    if active_pane:
                        text_area = active_pane.query_one("TextArea")
                        if text_area:
                            # Get file extension from tab id
                            ext = "." + tabbed.active.split(".")[-1] if "." in tabbed.active else ""
                            active_file = (ext, text_area.text[:2000])
            except Exception:
                pass  # No active file, that's fine

            # Build a redacted brief and require explicit per-operation consent.
            from config import prepare_council_brief

            brief, meta = prepare_council_brief(
                mode=self.session_mode,
                lens=self.session_lens,
                context_band=self._last_context_band,
                recent_turns=[{"role": r, "content": c} for r, c in self.conversation_history[-5:]],
                user_query=query,
                request_type="general",
                active_file=active_file,
                node_assessment=None,
            )

            # Store pending request (expires quickly to prevent accidental later sends)
            self._pending_council = {
                "query": query,
                "brief": brief,
                "meta": meta,
                "created_at": time.time(),
                "expires_at": time.time() + 60,
            }

            # Preview (redacted) and request explicit confirmation
            turns = meta.get("turns_included", 0)
            redactions = meta.get("redaction", {}).get("redactions", 0)
            file_note = "(none)"
            if meta.get("active_file_included"):
                ext = meta.get("active_file_extension") or ""
                truncated = " (truncated)" if meta.get("active_file_truncated") else ""
                file_note = f"{ext or 'file'}{truncated}"

            stream.add_message("[#d4a574]☁️ Council Preview (redacted):[/#d4a574]", "system")
            stream.add_message(
                f"[dim]Turns: {turns} | Active file: {file_note} | Redactions: {redactions} | Expires: 60s[/dim]",
                "system",
            )
            preview = brief[:1200] + ("\n... (preview truncated)" if len(brief) > 1200 else "")
            stream.add_message(f"[dim]{preview}[/dim]", "system")
            stream.add_message("[yellow]Type /council-yes to send, or /council-no to cancel.[/yellow]", "system")
            return

        except Exception as e:
            stream.add_message(f"[red]Council error: {e}[/red]", "error")

    def _handle_seat_command(self, message: str) -> None:
        """Handle /seat command for Council model switching.

        Usage:
            /seat              - List available Council models
            /seat <model>      - Switch to specified model (partial match supported)

        Examples:
            /seat gemini-flash
            /seat deepseek
            /seat gpt-oss
        """
        stream = self.query_one(NeuralStream)

        # Extract model name from command
        parts = message.split(maxsplit=1)
        model_arg = parts[1].strip() if len(parts) > 1 else ""

        # Check if Council is available
        if self.council_client is None:
            stream.add_message("[yellow]Council not initialized.[/yellow]", "system")
            return

        # If no argument, list available models
        if not model_arg:
            models = self.council_client.models
            current = self.council_client.current_model_shortname
            provider = self.council_client.provider

            stream.add_message(f"[b]Council Seats ({provider}):[/b]", "system")
            for shortname, model_id in models.items():
                marker = " [cyan]← current[/cyan]" if shortname == current else ""
                stream.add_message(f"  • {shortname}: {model_id}{marker}", "system")
            stream.add_message("[dim]Usage: /seat <model_name>[/dim]", "system")
            return

        # Try to switch to the specified model
        # First try exact match
        if self.council_client.switch_model(model_arg):
            new_model = self.council_client.current_model
            self.council_model = self.council_client.current_model_shortname
            stream.add_message(f"[green]Council Seat assigned to: {new_model}[/green]", "system")

            # Update status bar if Council is enabled
            if self.council_gate_enabled:
                status_bar = self.query_one(StatusBar)
                status_bar.update_council_gate(self.council_model)
            return

        # Try partial match
        models = self.council_client.models
        matches = [k for k in models.keys() if model_arg.lower() in k.lower()]

        if len(matches) == 1:
            self.council_client.switch_model(matches[0])
            new_model = self.council_client.current_model
            self.council_model = self.council_client.current_model_shortname
            stream.add_message(f"[green]Council Seat assigned to: {new_model}[/green]", "system")

            if self.council_gate_enabled:
                status_bar = self.query_one(StatusBar)
                status_bar.update_council_gate(self.council_model)
        elif len(matches) > 1:
            stream.add_message(f"[yellow]Multiple matches: {', '.join(matches)}[/yellow]", "system")
        else:
            available = ", ".join(models.keys())
            stream.add_message(f"[yellow]Model '{model_arg}' not found. Available: {available}[/yellow]", "system")

    async def _handle_council_consent(self, approved: bool) -> None:
        """Handle /council-yes and /council-no confirmation commands."""
        stream = self.query_one(NeuralStream)

        pending = self._pending_council
        if not pending:
            stream.add_message("[yellow]No pending Council request.[/yellow]", "system")
            return

        if time.time() > pending.get("expires_at", 0):
            self._pending_council = None
            stream.add_message("[yellow]Pending Council request expired. Re-run /council.[/yellow]", "system")
            return

        if not approved:
            self._pending_council = None
            stream.add_message("[dim]☁️ Council request cancelled.[/dim]", "system")
            return

        if self.council_client is None:
            self._pending_council = None
            stream.add_message("[yellow]Council not available.[/yellow]", "system")
            return

        if not self.council_gate_enabled:
            self._pending_council = None
            stream.add_message("[yellow]Council Gate is closed.[/yellow]", "system")
            return

        # Show consultation indicator
        stream.add_message("[dim]☁️ Consulting Council...[/dim]", "system")

        query = pending.get("query", "")
        brief = pending.get("brief", "")
        self._pending_council = None

        try:
            response = await self.council_client.consult(brief)
            if response:
                ts_prefix = f"[dim]{datetime.now().strftime('%H:%M')}[/dim] " if self.show_timestamps else ""
                stream.add_message(f"{ts_prefix}[#d4a574]☁️ Council ({self.council_model or 'cloud'}):[/#d4a574]", "system")
                stream.add_message(f"[#e0d4c8]{response}[/#e0d4c8]", "council")
                self.conversation_history.append(("council", f"[Council response to '{query}']: {response[:500]}..."))
            else:
                stream.add_message("[red]Council returned no response.[/red]", "error")
        except Exception as e:
            stream.add_message(f"[red]Council error: {e}[/red]", "error")

    async def _handle_confirm(self, approved: bool) -> None:
        """Handle /confirm-yes and /confirm-no for high-impact operations."""
        stream = self.query_one(NeuralStream)

        pending = self._pending_confirm
        if not pending:
            stream.add_message("[yellow]No pending operation to confirm.[/yellow]", "system")
            return

        if time.time() > pending.get("expires_at", 0):
            self._pending_confirm = None
            stream.add_message("[yellow]Pending operation expired. Re-run the action.[/yellow]", "system")
            return

        if not approved:
            self._pending_confirm = None
            stream.add_message("[dim]Operation cancelled.[/dim]", "system")
            return

        kind = pending.get("kind")
        payload = pending.get("payload", {}) or {}
        self._pending_confirm = None

        try:
            if kind == "git":
                op = payload.get("op")
                if op == "pull":
                    await self._git_pull()
                elif op == "push":
                    await self._git_push()
                elif op == "commit":
                    message = payload.get("message")
                    if not message:
                        stream.add_message("[red]Missing commit message.[/red]", "error")
                        return
                    await self._git_commit_execute(message)
                else:
                    stream.add_message("[red]Unknown git operation.[/red]", "error")
                    return

            elif kind == "delete_session":
                session_id = payload.get("session_id")
                reopen = bool(payload.get("reopen_picker"))
                if session_id:
                    await self._delete_session(session_id)
                    if reopen:
                        await self._open_session_picker()
                else:
                    stream.add_message("[red]Missing session id.[/red]", "error")

            elif kind == "delete_all_sessions":
                await self._delete_all_sessions()

            else:
                stream.add_message("[red]Unknown operation kind.[/red]", "error")

        except Exception as e:
            stream.add_message(f"[red]Operation failed: {e}[/red]", "error")

    async def _handle_ref_load_consent(self, approved: bool) -> None:
        """Handle /load-yes and /load-no for @ref file loading consent."""
        stream = self.query_one(NeuralStream)

        pending = self._pending_ref_load
        if not pending:
            stream.add_message("[yellow]No pending @ref load request.[/yellow]", "system")
            return

        if not approved:
            self._pending_ref_load = None
            stream.add_message("[dim]@ref loading cancelled.[/dim]", "system")
            return

        refs = pending.get("refs", [])
        original_message = pending.get("message", "")
        self._pending_ref_load = None

        # Load files into context injection
        await self._load_refs_into_context(refs, stream)

        # Now send the original message (ref detection will be skipped since _ref_context_injection is set)
        await self._send_message(original_message)

    def _extract_refs_from_message(self, message: str) -> list[str]:
        """Extract @ref tokens from a message."""
        import re
        # Match @followed by path-like characters (no spaces)
        refs = re.findall(r'@([\w./\\-]+)', message)
        return [f"@{r}" for r in refs]

    def _message_has_load_verb(self, message: str) -> bool:
        """Check if message contains a verb that authorizes @ref loading."""
        msg_lower = message.lower()
        for verb in self.REF_LOAD_VERBS:
            if verb in msg_lower:
                return True
        return False

    async def _load_refs_into_context(self, refs: list[str], stream) -> None:
        """Load @ref file contents into context injection for the next message."""
        context_parts: list[str] = []
        loaded_files: list[str] = []

        for ref in refs:
            rel_path = ref.lstrip("@")
            file_path = workspace_root / rel_path

            if not file_path.exists():
                stream.add_message(f"[yellow]@{rel_path} not found, skipping.[/yellow]", "system")
                continue

            if not file_path.is_file():
                stream.add_message(f"[yellow]@{rel_path} is not a file, skipping.[/yellow]", "system")
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                if len(content) > 50000:  # ~12k tokens limit per file
                    content = content[:50000] + "\n... (truncated)"
                    stream.add_message(f"[dim]@{rel_path} truncated (>50KB).[/dim]", "system")

                context_parts.append(f"=== File: {rel_path} ===\n{content}\n=== End: {rel_path} ===")
                loaded_files.append(rel_path)
            except Exception as e:
                stream.add_message(f"[yellow]Failed to read @{rel_path}: {e}[/yellow]", "system")

        if loaded_files:
            stream.add_message(f"[dim]📄 Loaded: {', '.join(loaded_files)}[/dim]", "system")

        if context_parts:
            self._ref_context_injection = "\n\n".join(context_parts)
        else:
            self._ref_context_injection = None

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

                    # Model selection priority:
                    # 1. Saved last_model (if available in backend)
                    # 2. Profile's preferred_model (if available in backend)
                    # 3. First available model
                    
                    target_model = None
                    model_source = None
                    
                    # Check for saved model from last session
                    if self.db:
                        try:
                            saved_model = await self.db.get_preference(self.PREF_LAST_MODEL_KEY)
                            if saved_model:
                                # Look for exact or partial match
                                matching = [m for m in models if saved_model.lower() in m.lower() or m.lower() in saved_model.lower()]
                                if matching:
                                    target_model = matching[0]
                                    model_source = "saved"
                        except Exception:
                            pass
                    
                    # Fall back to profile's preferred model
                    if not target_model and self.current_profile:
                        preferred_model = self.current_profile.get("preferred_model")
                        if preferred_model:
                            matching = [m for m in models if preferred_model.lower() in m.lower()]
                            if matching:
                                target_model = matching[0]
                                model_source = "preferred"
                            else:
                                stream.add_message(f"[yellow]Preferred model '{preferred_model}' not found[/yellow]", "system")
                    
                    # Try to switch to target model
                    if target_model:
                        label = "last used" if model_source == "saved" else "preferred"
                        stream.add_message(f"[dim]Switching to {label} model: {target_model}[/dim]", "system")
                        success = await self.llm_client.switch_model(target_model)
                        if success:
                            model_name = self.llm_client.current_model
                        else:
                            model_name = self.llm_client.current_model or models[0]
                            stream.add_message(f"[yellow]Couldn't switch to {label} model, using {model_name}[/yellow]", "system")
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
                stream.add_message("[dim]Search Gate: No providers available[/dim]", "system")

            # Update status bar
            status_bar = self.query_one(StatusBar)
            status_bar.update_search_gate(search_manager.state.status_text())

        except Exception as e:
            stream.add_message(f"[yellow]Search Gate skipped: {e}[/yellow]", "system")
            self.search_manager = None

    async def _initialize_council_gate(self) -> None:
        """Initialize Council Gate (Friction Class VI extension).

        The Council Gate defaults to closed (local-only).
        Cloud consultation requires explicit consent via toggle.

        Supports two backends:
        - Ollama Cloud (default): Uses local Ollama to route to cloud models
        - OpenRouter: Requires API key, provides access to GPT-4, Claude, etc.
        """
        stream = self.query_one(NeuralStream)

        try:
            from llm.council_client import council_client
            from config import COUNCIL_PROVIDER, COUNCIL_DEFAULT_MODEL

            self.council_client = council_client
            self.council_model = COUNCIL_DEFAULT_MODEL

            if council_client.is_available():
                provider_name = "Ollama Cloud" if COUNCIL_PROVIDER == "ollama" else "OpenRouter"
                model_name = council_client.current_model or COUNCIL_DEFAULT_MODEL
                stream.add_message(f"[dim]Council Gate ready: {provider_name} ({model_name})[/dim]", "system")
            else:
                if COUNCIL_PROVIDER == "ollama":
                    stream.add_message("[dim]Council Gate: Ollama (will connect when enabled)[/dim]", "system")
                else:
                    stream.add_message("[dim]Council Gate: No API key (set OPENROUTER_API_KEY)[/dim]", "system")

        except Exception as e:
            stream.add_message(f"[yellow]Council Gate skipped: {e}[/yellow]", "system")
            self.council_client = None

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
        try:
            if getattr(getattr(event, "text_area", None), "id", None) == "chat-input":
                event.text_area._update_mention_suggestions()
        except Exception:
            pass

    async def action_submit_message(self) -> None:
        """Handle chat input from button or binding."""
        text_input = self.query_one("#chat-input", ChatInput)
        message = text_input.text.strip()
        if not message:
            return
        text_input.text = ""
        await self._send_message(message)

    async def _send_message(self, message: str) -> None:
        """Core message sending logic with verb-gated @ref resolution."""
        if not message:
            return

        stream = self.query_one(NeuralStream)

        # Verb-gated @ref resolution (Monday's rule: "Verbs authorize access")
        # Skip if files already loaded (consent flow completed)
        if not self._ref_context_injection:
            refs = self._extract_refs_from_message(message)
            if refs and self._message_has_load_verb(message):
                if self.auto_load_refs:
                    # Auto-load enabled: load files silently
                    await self._load_refs_into_context(refs, stream)
                else:
                    # Consent required: prompt and defer
                    ref_list = ", ".join(refs)
                    stream.add_message(f"[dim]📄 {ref_list} referenced.[/dim]", "system")
                    stream.add_message("[yellow]Load into context? [/load-yes] [/load-no][/yellow]", "system")
                    self._pending_ref_load = {"refs": refs, "message": message}
                    return

        # Show user message (with timestamp if enabled)
        ts_prefix = f"[dim]{datetime.now().strftime('%H:%M')}[/dim] " if self.show_timestamps else ""
        stream.add_message(f"{ts_prefix}[b]›[/b] {message}", "steward")

        # Track in conversation history
        self.conversation_history.append(("steward", message))
        self._trim_ram_history()

        if not self.connected or not self.llm_client:
            stream.add_message("[red]Not connected to Node.[/red]", "error")
            return

        # Show thinking indicator
        stream.add_message("[dim]Node is thinking...[/dim]", "system")

        response = None
        start_time = time.perf_counter()

        try:
            self._llm_inflight = True
            self._last_llm_error = None

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
                    initiative=self._effective_initiative(),
                    context_band=current_band,
                    context_first_warning=first_warning,
                    social_carryover=self.social_carryover
                )
            else:
                system_prompt = build_system_prompt(
                    mode=self.session_mode,
                    lens=self.session_lens,
                    idle=self.idle_mode,
                    initiative=self._effective_initiative(),
                    context_band=current_band,
                    context_first_warning=first_warning
                )

            # Check for memory operations and build context
            context_parts: list[str] = []
            sources_used = []

            # Inject @ref file contents if loaded (verb-gated resolution)
            if self._ref_context_injection:
                context_parts.append("Referenced files:\n" + self._ref_context_injection)
                sources_used.append("@refs")
                self._ref_context_injection = None  # Clear after use

            # Inject recent conversation so "resume" is real, not vibes.
            history_context = self._format_recent_history(max_turns=self.HISTORY_CONTEXT_TURNS, exclude_latest=True)
            if history_context:
                context_parts.append("Recent conversation:\n" + history_context)

            # Try to load memories for context (direct file access, no MCP needed)
            msg_lower = message.lower()

            try:
                # Council consent confirmations (handled locally; never sent to Node)
                if msg_lower in ("/council-yes", "/council-no"):
                    await self._handle_council_consent(approved=(msg_lower == "/council-yes"))
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # Generic confirmations for destructive operations
                if msg_lower in ("/confirm-yes", "/confirm-no"):
                    await self._handle_confirm(approved=(msg_lower == "/confirm-yes"))
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # @ref load consent confirmations
                if msg_lower in ("/load-yes", "/load-no"):
                    await self._handle_ref_load_consent(approved=(msg_lower == "/load-yes"))
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # Help command
                if msg_lower == "/help":
                    self.action_show_help()
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # Clear command
                if msg_lower == "/clear":
                    self.action_clear_chat()
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # Save command
                if msg_lower == "/save":
                    self.action_save_file()
                    stream.add_message("[dim]File saved.[/dim]", "system")
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # Models command
                if msg_lower == "/models":
                    self.action_models()
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # Profiles command
                if msg_lower == "/profiles":
                    self.action_profiles()
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # Monitor command - focus dock Monitor tab
                if msg_lower == "/monitor":
                    self.add_class("dock-visible")
                    try:
                        dock_tabs = self.query_one("#dock-tabs", TabbedContent)
                        dock_tabs.active = "dock-monitor"
                        stream.add_message("[dim]Monitor opened.[/dim]", "system")
                    except Exception:
                        stream.add_message("[yellow]Dock not available.[/yellow]", "system")
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # Editor command - focus dock Editor tab
                if msg_lower == "/editor":
                    self.add_class("dock-visible")
                    try:
                        dock_tabs = self.query_one("#dock-tabs", TabbedContent)
                        dock_tabs.active = "dock-editor"
                        stream.add_message("[dim]Editor opened.[/dim]", "system")
                    except Exception:
                        stream.add_message("[yellow]Dock not available.[/yellow]", "system")
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # Session command - show session info
                if msg_lower == "/session":
                    session_name = self.session_name or "Unnamed"
                    session_id = self.session_id or "None"
                    exchanges = self._exchange_count if hasattr(self, '_exchange_count') else 0
                    stream.add_message(f"[dim]Session: {session_name}[/dim]", "system")
                    stream.add_message(f"[dim]ID: {session_id[:8]}... | Exchanges: {exchanges}[/dim]", "system")
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # Context command - show context info
                if msg_lower == "/context":
                    history_turns = len(self.conversation_history)
                    band = self._context_band if hasattr(self, '_context_band') else "unknown"
                    rag_chunks = len(self.rag_chunks_loaded) if hasattr(self, 'rag_chunks_loaded') else 0
                    stream.add_message(f"[dim]Context band: {band}[/dim]", "system")
                    stream.add_message(f"[dim]History: {history_turns} turns | RAG chunks: {rag_chunks}[/dim]", "system")
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

                # Bookmark command - with optional name
                if msg_lower.startswith("/bookmark"):
                    # Extract optional name from /bookmark <name>
                    parts = message.split(maxsplit=1)
                    bookmark_name = parts[1] if len(parts) > 1 else None
                    await self.initiate_bookmark_weave(preset_name=bookmark_name)
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return

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

                # Check if this is a /council command
                elif msg_lower.startswith('/council'):
                    await self._handle_council_command(message)
                    return  # Council command handled separately

                # Check if this is a /seat command (Council model switching)
                elif msg_lower.startswith('/seat'):
                    self._handle_seat_command(message)
                    # Remove from conversation history
                    if self.conversation_history and self.conversation_history[-1] == ("steward", message):
                        self.conversation_history.pop()
                    return  # Seat command handled

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
            display_lines = []

            # Always show conversation history (it's always in context)
            if self.conversation_history:
                turns = len(self.conversation_history)
                display_lines.append(f"[dim]💬 History ({turns} turns) — RAM[/dim]")

            # Show file-based sources (these cost tokens)
            for source in sources_used:
                if source == "Memory Store":
                    display_lines.append(f"[cyan]📁 Memory/memory.json[/cyan]")
                else:
                    # RAG document
                    display_lines.append(f"[green]📄 {source}[/green]")

            if display_lines:
                self._update_last_context_displays("\n".join(display_lines))
            else:
                self._update_last_context_displays("[dim]No context loaded[/dim]")

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
                # Strip reasoning traces for clean display
                display_text, reasoning_text = self._strip_reasoning_traces(response)
                ts_prefix = f"[dim]{datetime.now().strftime('%H:%M')}[/dim] " if self.show_timestamps else ""
                stream.add_message(f"{ts_prefix}[b]‹[/b] {display_text}", "node")
                
                # Show hint if reasoning was stripped
                if reasoning_text:
                    stream.add_message("[dim italic]💭 Reasoning trace hidden[/dim italic]", "system")
                
                # Track full response in conversation history (preserves reasoning for context)
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
            self._last_llm_error = str(e)
            stream.add_message(f"[red]Error: {e}[/red]", "error")
        finally:
            try:
                elapsed = max(0.0, time.perf_counter() - start_time)
                self._last_llm_latency_ms = round(elapsed * 1000.0, 1)
                if response:
                    tokens_est = int(len(response) * self.AVG_TOKENS_PER_CHAR)
                    self._last_llm_tokens_est = tokens_est
                    self._last_llm_tps_est = round(tokens_est / elapsed, 1) if elapsed > 0 else None
                else:
                    self._last_llm_tokens_est = None
                    self._last_llm_tps_est = None
            except Exception:
                pass
            self._llm_inflight = False
            self._update_monitor_panel()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        stream = self.query_one(NeuralStream)

        # Attach file button
        if button_id == "btn-attach":
            self._open_attach_modal()
            return

        # Dock toggle button
        if button_id == "btn-dock-toggle":
            self.action_toggle_dock()
            return

        # Spine editor buttons (Tall layout)
        if button_id == "btn-spine-save":
            await self._save_spine_editor()
            return
        if button_id == "btn-spine-close":
            self._close_spine_editor()
            return

        # Dock editor buttons
        if button_id == "btn-dock-save":
            await self._save_dock_editor()
            return
        if button_id == "btn-dock-expand":
            self._toggle_dock_expanded()
            return

        # Initiative buttons
        if button_id in ("btn-initiative-cycle", "dock-btn-initiative-cycle"):
            self.action_cycle_initiative()
            return
        if button_id in ("btn-initiative-default", "dock-btn-initiative-default"):
            await self.action_set_initiative_default()
            return

        # Lens buttons
        if button_id in (
            "lens-blue",
            "lens-red",
            "lens-purple",
            "dock-lens-blue",
            "dock-lens-red",
            "dock-lens-purple",
        ):
            # Remove active from all lens buttons (both main + dock), add to clicked one
            for btn_id in (
                "lens-blue",
                "lens-red",
                "lens-purple",
                "dock-lens-blue",
                "dock-lens-red",
                "dock-lens-purple",
            ):
                try:
                    btn = self.query_one(f"#{btn_id}", Button)
                    btn.remove_class("active")
                except Exception:
                    pass
            event.button.add_class("active")

            lens_id = button_id.replace("dock-", "")

            if lens_id == "lens-blue":
                self.session_lens = "Blue"
                stream.add_message("[dim]🔵 Grounded[/dim]", "system")
            elif lens_id == "lens-red":
                self.session_lens = "Red"
                stream.add_message("[dim]🔴 Processing[/dim]", "system")
            elif lens_id == "lens-purple":
                self.session_lens = "Purple"
                stream.add_message("[dim]🟣 Symbolic[/dim]", "system")
                # Ephemeral scaffolding: show one-time hint for first Purple activation
                from config import get_hint_message
                hint = get_hint_message("purple_first")
                if hint:
                    stream.add_message(f"    ↳ {hint}", "hint")

            # Keep the other set visually in sync
            try:
                counterpart_id = f"dock-{lens_id}" if not button_id.startswith("dock-") else lens_id
                self.query_one(f"#{counterpart_id}", Button).add_class("active")
            except Exception:
                pass
            # Update Truth Strip
            self.query_one(StatusBar).update_lens(self.session_lens)
            # Persist lens preference
            if self.db:
                asyncio.create_task(self.db.set_preference(self.PREF_LAST_LENS_KEY, self.session_lens))

        # Mode buttons
        elif button_id in ("mode-workshop", "mode-sanctuary", "dock-mode-workshop", "dock-mode-sanctuary"):
            # Remove active from all mode buttons (both main + dock), add to clicked one
            for btn_id in ("mode-workshop", "mode-sanctuary", "dock-mode-workshop", "dock-mode-sanctuary"):
                try:
                    btn = self.query_one(f"#{btn_id}", Button)
                    btn.remove_class("active")
                except Exception:
                    pass
            event.button.add_class("active")

            mode_id = button_id.replace("dock-", "")

            if mode_id == "mode-workshop":
                self.remove_class("mode-sanctuary")
                self.add_class("mode-workshop")
                self.session_mode = "Workshop"
                stream.add_message("[dim]🛠 Workshop[/dim]", "system")
            elif mode_id == "mode-sanctuary":
                self.remove_class("mode-workshop")
                self.add_class("mode-sanctuary")
                self.session_mode = "Sanctuary"
                stream.add_message("[dim]🕯 Sanctuary[/dim]", "system")
                # Ephemeral scaffolding: show one-time hint for first Sanctuary activation
                from config import get_hint_message
                hint = get_hint_message("sanctuary_first")
                if hint:
                    stream.add_message(f"    ↳ {hint}", "hint")

            # Keep the other set visually in sync
            try:
                counterpart_id = f"dock-{mode_id}" if not button_id.startswith("dock-") else mode_id
                self.query_one(f"#{counterpart_id}", Button).add_class("active")
            except Exception:
                pass
            # Update Truth Strip
            self.query_one(StatusBar).update_mode(self.session_mode)
            self._apply_initiative_mode_defaults()
            # Persist mode preference
            if self.db:
                asyncio.create_task(self.db.set_preference(self.PREF_LAST_MODE_KEY, self.session_mode))

        # Protocol buttons
        elif button_id in ("btn-bookmark", "dock-bookmark-btn"):
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
            await self._queue_git_confirm("pull")
        elif button_id == "btn-git-commit":
            await self._queue_git_confirm("commit")
        elif button_id == "btn-git-push":
            await self._queue_git_confirm("push")

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

    async def initiate_bookmark_weave(self, preset_name: str | None = None) -> None:
        """Prepare and open the bookmark weaving modal with Auto-Loom drafting.

        Args:
            preset_name: Optional name to use as the bookmark title instead of auto-drafting.
        """
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
            "title": preset_name or "Session",
            "description": "",
            "reflections": "",
            "drift": ""
        }

        # Try to use Auto-Loom if connected
        if self.connected and self.llm_client and recent_history:
            try:
                auto_draft = await self._draft_bookmark_content(recent_history)
                if auto_draft:
                    # Preserve preset_name if provided
                    if preset_name:
                        auto_draft.pop("title", None)
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
            
            # Ensure directory exists (save to workspace/bookmarks/)
            save_dir = workspace_root / "bookmarks"
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
        if self._syncing_switches:
            return

        if event.switch.id == "toggle-idleness":
            self.idle_mode = event.value
            stream = self.query_one(NeuralStream)

            # Get mode buttons for visual suspension
            try:
                workshop_btn = self.query_one("#mode-workshop", Button)
                sanctuary_btn = self.query_one("#mode-sanctuary", Button)
            except Exception:
                workshop_btn = sanctuary_btn = None
            try:
                dock_workshop_btn = self.query_one("#dock-mode-workshop", Button)
                dock_sanctuary_btn = self.query_one("#dock-mode-sanctuary", Button)
            except Exception:
                dock_workshop_btn = dock_sanctuary_btn = None

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
                if dock_workshop_btn:
                    dock_workshop_btn.disabled = True
                if dock_sanctuary_btn:
                    dock_sanctuary_btn.disabled = True
                # Log event
                asyncio.create_task(self._log_event("idleness_toggled", {"state": True, "suspended_mode": self.session_mode}))
                # If we're already in the dimmed-idle window, force initiative Low immediately
                if self._idle_dim_active and not self._initiative_forced_low:
                    self._initiative_forced_low = True
                self._refresh_initiative_ui()
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
                if dock_workshop_btn:
                    dock_workshop_btn.disabled = False
                if dock_sanctuary_btn:
                    dock_sanctuary_btn.disabled = False
                # Log event
                asyncio.create_task(self._log_event("idleness_toggled", {"state": False, "restored_mode": self.session_mode}))
                if self._initiative_forced_low:
                    self._initiative_forced_low = False
                self._refresh_initiative_ui()

        elif event.switch.id == "toggle-rag-debug":
            self.rag_debug_enabled = event.value
            stream = self.query_one(NeuralStream)
            if self.rag_debug_enabled:
                stream.add_message("[cyan]🔍 RAG Debug: On[/cyan]", "system")
            else:
                stream.add_message("[dim]🔍 RAG Debug: Off[/dim]", "system")

        elif event.switch.id in ("toggle-timestamps", "dock-toggle-timestamps"):
            self.show_timestamps = event.value
            # Sync both switches
            self._syncing_switches = True
            try:
                self.query_one("#toggle-timestamps", Switch).value = event.value
            except Exception:
                pass
            try:
                self.query_one("#dock-toggle-timestamps", Switch).value = event.value
            except Exception:
                pass
            self._syncing_switches = False
            # Persist preference
            if self.db:
                asyncio.create_task(self.db.set_preference(self.PREF_SHOW_TIMESTAMPS_KEY, str(event.value).lower()))

        elif event.switch.id in ("toggle-auto-load-refs", "dock-toggle-auto-load-refs"):
            self.auto_load_refs = event.value
            # Sync both switches
            self._syncing_switches = True
            try:
                self.query_one("#toggle-auto-load-refs", Switch).value = event.value
            except Exception:
                pass
            try:
                self.query_one("#dock-toggle-auto-load-refs", Switch).value = event.value
            except Exception:
                pass
            self._syncing_switches = False
            # Persist preference
            if self.db:
                asyncio.create_task(self.db.set_preference(self.PREF_AUTO_LOAD_REFS_KEY, str(event.value).lower()))
            # Notify user
            stream = self.query_one(NeuralStream)
            if self.auto_load_refs:
                stream.add_message("[dim]📄 Auto-load @refs: On (verbs will load files without asking)[/dim]", "system")
            else:
                stream.add_message("[dim]📄 Auto-load @refs: Off (will ask before loading)[/dim]", "system")

        elif event.switch.id in ("toggle-search-gate", "dock-toggle-search-gate"):
            # Friction Class VI: Search Gate consent toggle
            if self.search_manager is None:
                stream = self.query_one(NeuralStream)
                stream.add_message("[yellow]Search Gate not available[/yellow]", "system")
                # Reset both switches to off
                self._syncing_switches = True
                try:
                    event.switch.value = False
                    try:
                        self.query_one("#toggle-search-gate", Switch).value = False
                    except Exception:
                        pass
                    try:
                        self.query_one("#dock-toggle-search-gate", Switch).value = False
                    except Exception:
                        pass
                finally:
                    self._syncing_switches = False
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

            # Keep both switches visually in sync
            self._syncing_switches = True
            try:
                try:
                    self.query_one("#toggle-search-gate", Switch).value = self.search_gate_enabled
                except Exception:
                    pass
                try:
                    self.query_one("#dock-toggle-search-gate", Switch).value = self.search_gate_enabled
                except Exception:
                    pass
            finally:
                self._syncing_switches = False

        elif event.switch.id in ("toggle-council-gate", "dock-toggle-council-gate"):
            # Friction Class VI extension: Council Gate consent toggle
            if self.council_client is None:
                stream = self.query_one(NeuralStream)
                stream.add_message("[yellow]Council Gate not available (no API key)[/yellow]", "system")
                # Reset both switches to off
                self._syncing_switches = True
                try:
                    event.switch.value = False
                    try:
                        self.query_one("#toggle-council-gate", Switch).value = False
                    except Exception:
                        pass
                    try:
                        self.query_one("#dock-toggle-council-gate", Switch).value = False
                    except Exception:
                        pass
                finally:
                    self._syncing_switches = False
                return

            stream = self.query_one(NeuralStream)
            status_bar = self.query_one(StatusBar)
            if event.value:
                # Opening the gate
                self.council_gate_enabled = True
                model_name = self.council_model or "default"
                status_bar.update_council_gate(model_name)
                stream.add_message(f"[green]☁️ Council Gate opened ({model_name})[/green]", "system")
            else:
                # Closing the gate
                self.council_gate_enabled = False
                status_bar.update_council_gate("Off")
                stream.add_message("[dim]☁️ Council Gate closed (local-only)[/dim]", "system")

            # Keep both switches visually in sync
            self._syncing_switches = True
            try:
                try:
                    self.query_one("#toggle-council-gate", Switch).value = self.council_gate_enabled
                except Exception:
                    pass
                try:
                    self.query_one("#dock-toggle-council-gate", Switch).value = self.council_gate_enabled
                except Exception:
                    pass
            finally:
                self._syncing_switches = False

    def action_clear_chat(self) -> None:
        """Clear the chat stream and conversation history."""
        from config import get_themed_ascii, DEFAULT_THEME
        stream = self.query_one(NeuralStream)
        for child in list(stream.children):
            child.remove()
        # Re-show ASCII art after clear
        stream.add_message(get_themed_ascii(DEFAULT_THEME), "system")
        stream.add_message("[dim]Chat cleared.[/dim]", "system")
        # Clear context tracking
        self.conversation_history = []
        self.rag_chunks_loaded = []
        self.last_context_sources = []
        self.context_high_acknowledged = False
        self.context_critical_acknowledged = False
        self._last_context_band = "~Low"  # Reset transition tracking
        self._update_context_band()
        # Reset context display
        self._update_last_context_displays("[dim]No context loaded[/dim]")

    def action_toggle_social_carryover(self) -> None:
        """Toggle Social Carryover (warm vs neutral stance).
        
        When On (warm): conversational stance, matching energy, core behavior active
        When Off (neutral): neutral stance replaces warmth sections
        
        Key insight: "Posture lives in what you inject, not what the model remembers."
        History is preserved; only warmth framing changes.
        """
        self.social_carryover = not self.social_carryover
        stream = self.query_one(NeuralStream)
        status_bar = self.query_one(StatusBar)
        status_bar.update_social_carryover(self.social_carryover)
        
        if self.social_carryover:
            stream.add_message("[dim]🤝 Social Carryover: On — warmth maintained[/dim]", "system")
        else:
            stream.add_message("[cyan]🔲 Social Carryover: Off — neutral ground[/cyan]", "system")

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
            if role == "council":
                continue  # Don't inject Council content as plain context by default.
            speaker = "Steward" if role == "steward" else ("Node" if role == "node" else role)
            text = (content or "").strip().replace("\n", " ").strip()
            if len(text) > 300:
                text = text[:297] + "..."
            if text:
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)

    async def _persist_exchange(self, user_message: str, ai_response: str, context_used: str) -> None:
        """Write conversation + session metadata so resume works across restarts."""
        if self.db is None or self.session_id is None:
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
        except Exception as e:
            # Log persistence errors for debugging (but don't break the flow)
            try:
                stream = self.query_one(NeuralStream)
                stream.add_message(f"[dim red]Session save error: {e}[/dim red]", "system")
            except Exception:
                pass

    def action_toggle_sidebar(self) -> None:
        """Toggle secondary panels (Wide: sidebar, Tall/Compact: bottom dock)."""
        if self._current_layout == "wide":
            self._sidebar_hidden = not self._sidebar_hidden
            if self._sidebar_hidden:
                self.add_class("sidebar-hidden")
            else:
                self.remove_class("sidebar-hidden")
        else:
            self._dock_hidden = not self._dock_hidden
            if self._dock_hidden:
                self.add_class("dock-hidden")
            else:
                self.remove_class("dock-hidden")

    def action_insert_newline(self) -> None:
        """Insert a newline into the chat input (Ctrl+J)."""
        try:
            chat_input = self.query_one("#chat-input", ChatInput)
            chat_input.insert("\n")
        except Exception:
            pass

    # --- RESPONSE PROCESSING ---

    def _strip_reasoning_traces(self, response: str) -> tuple[str, str]:
        """
        Strip reasoning traces from model responses.
        
        Reasoning models often wrap thinking in tags like:
        - <think>...</think>
        - <reasoning>...</reasoning>
        - <internal>...</internal>
        
        Some models (Nemotron) omit the opening tag, outputting:
        - "reasoning text</think>actual response"
        
        Returns (display_text, reasoning_text) for future collapsible support.
        """
        import re
        
        reasoning_parts = []
        display_text = response
        
        # Standard paired tag patterns (case-insensitive)
        paired_patterns = [
            r'<think>(.*?)</think>',
            r'<thinking>(.*?)</thinking>',
            r'<reasoning>(.*?)</reasoning>',
            r'<internal>(.*?)</internal>',
            r'<reflection>(.*?)</reflection>',
        ]
        
        for pattern in paired_patterns:
            matches = re.findall(pattern, display_text, re.DOTALL | re.IGNORECASE)
            reasoning_parts.extend(matches)
            display_text = re.sub(pattern, '', display_text, flags=re.DOTALL | re.IGNORECASE)
        
        # Handle missing opening tag: everything before </think> is reasoning
        # Pattern: "reasoning text</think>actual response" or "</tag>" at start
        orphan_patterns = [
            r'^(.*?)</think>',
            r'^(.*?)</thinking>',
            r'^(.*?)</reasoning>',
        ]
        
        for pattern in orphan_patterns:
            match = re.match(pattern, display_text, re.DOTALL | re.IGNORECASE)
            if match:
                reasoning_parts.append(match.group(1))
                display_text = re.sub(pattern, '', display_text, count=1, flags=re.DOTALL | re.IGNORECASE)
        
        # Clean up extra whitespace
        display_text = re.sub(r'\n{3,}', '\n\n', display_text).strip()
        reasoning_text = '\n\n'.join(reasoning_parts).strip()
        
        return display_text, reasoning_text

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
            if self._initiative_forced_low:
                self._initiative_forced_low = False
                self._refresh_initiative_ui()

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
            if self.idle_mode and not self._initiative_forced_low:
                self._initiative_forced_low = True
                self._refresh_initiative_ui()

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
    MEMORY_FILE = workspace_root / "Memory" / "memory.json"

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
        """Back-compat: stage+commit now requires explicit confirmation."""
        await self._queue_git_confirm("commit")

    async def _git_commit_execute(self, message: str) -> None:
        """Commit changes (execution path; call only after explicit confirm)."""
        import subprocess
        stream = self.query_one(NeuralStream)

        stream.add_message(f"[dim]📝 Committing: {message}[/dim]", "system")

        try:
            await asyncio.to_thread(
                subprocess.run,
                ["git", "add", "-A"],
                cwd=str(workspace_root),
                capture_output=True,
            )

            result = await asyncio.to_thread(
                subprocess.run,
                ["git", "commit", "-m", message],
                cwd=str(workspace_root),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                summary = lines[0] if lines else "Committed"
                stream.add_message(f"[green]✓ {summary}[/green]", "system")
            else:
                error = result.stderr.strip() or result.stdout.strip() or "Commit failed"
                stream.add_message(f"[red]✗ {error}[/red]", "error")
        except Exception as e:
            stream.add_message(f"[red]Git error: {e}[/red]", "error")

    async def _queue_git_confirm(self, op: str) -> None:
        """Show a git preview and require explicit confirmation before execution."""
        import subprocess

        stream = self.query_one(NeuralStream)

        def run_git(args: list[str]) -> str:
            try:
                r = subprocess.run(
                    ["git", *args],
                    cwd=str(workspace_root),
                    capture_output=True,
                    text=True,
                )
                out = (r.stdout or r.stderr or "").strip()
                return out[:1200]
            except Exception as e:
                return f"(preview failed: {e})"

        if op == "commit":
            status_porcelain = run_git(["status", "--porcelain"])
            if not status_porcelain.strip():
                stream.add_message("[dim]No changes to commit.[/dim]", "system")
                return

            message = await self.push_screen_wait(CommitModal())
            if not message:
                stream.add_message("[dim]Commit cancelled.[/dim]", "system")
                return

            diff_stat = run_git(["diff", "--stat"])

            stream.add_message("[yellow]Confirm git commit[/yellow]", "system")
            stream.add_message(f"[dim]Message: {message}[/dim]", "system")
            stream.add_message("[dim]This will run: git add -A; git commit -m \"…\"[/dim]", "system")
            stream.add_message("[dim]git status --porcelain (preview):[/dim]", "system")
            stream.add_message(f"[dim]{status_porcelain}[/dim]", "system")
            if diff_stat:
                stream.add_message("[dim]git diff --stat (preview):[/dim]", "system")
                stream.add_message(f"[dim]{diff_stat}[/dim]", "system")
            stream.add_message("[yellow]Type /confirm-yes to commit, or /confirm-no to cancel.[/yellow]", "system")

            self._pending_confirm = {
                "kind": "git",
                "payload": {"op": "commit", "message": message},
                "created_at": time.time(),
                "expires_at": time.time() + 60,
            }
            return

        if op not in {"pull", "push"}:
            stream.add_message("[red]Unknown git operation.[/red]", "error")
            return

        status_sb = run_git(["status", "-sb"])
        stream.add_message(f"[yellow]Confirm git {op}[/yellow]", "system")
        stream.add_message(f"[dim]This will run: git {op}[/dim]", "system")
        if status_sb:
            stream.add_message("[dim]git status -sb (preview):[/dim]", "system")
            stream.add_message(f"[dim]{status_sb}[/dim]", "system")

        if op == "push":
            ahead = run_git(["log", "--oneline", "@{u}.."])
            if ahead and not ahead.startswith("(preview failed"):
                stream.add_message("[dim]Commits to push (preview):[/dim]", "system")
                stream.add_message(f"[dim]{ahead}[/dim]", "system")

        stream.add_message("[yellow]Type /confirm-yes to proceed, or /confirm-no to cancel.[/yellow]", "system")
        self._pending_confirm = {
            "kind": "git",
            "payload": {"op": op},
            "created_at": time.time(),
            "expires_at": time.time() + 60,
        }

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
