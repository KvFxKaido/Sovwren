"""Council client for cloud model consultation via CLI tools, Ollama, or OpenRouter.

Primary method: Shell out to CLI tools (gemini, codex, claude, etc.)
Fallback: Ollama Cloud API or OpenRouter API

The CLI approach is simpler and more flexible:
- No API key management (each CLI handles its own auth)
- User controls what's installed
- Easy to add new "seats" by defining CLI commands
"""
import asyncio
import aiohttp
import shlex
import shutil
from typing import Optional, Dict, Tuple
from urllib.parse import urlparse

from config import (
    COUNCIL_PROVIDER,
    COUNCIL_OLLAMA_BASE,
    COUNCIL_OLLAMA_MODELS,
    COUNCIL_OPENROUTER_KEY,
    COUNCIL_OPENROUTER_BASE,
    COUNCIL_OPENROUTER_MODELS,
    COUNCIL_DEFAULT_MODEL,
    TIMEOUTS,
    load_profile,
    build_council_brief,
    prepare_council_brief,
)


# CLI-based council seats: shortname -> (command_template, description)
# {brief} will be replaced with the escaped brief text
COUNCIL_CLI_SEATS: Dict[str, Tuple[str, str]] = {
    "gemini": ('gemini -p "{brief}"', "Google Gemini CLI"),
    "codex": ('codex exec "{brief}"', "OpenAI Codex CLI (Constraint Steward)"),
    # "claude": ('claude -p "{brief}"', "Anthropic Claude CLI"),  # if installed
}


def _detect_available_cli_seats() -> Dict[str, Tuple[str, str]]:
    """Detect which CLI tools are actually installed."""
    available = {}
    cli_executables = {
        "gemini": "gemini",
        "codex": "codex",
        # "claude": "claude",
    }
    for seat, exe in cli_executables.items():
        if shutil.which(exe):
            available[seat] = COUNCIL_CLI_SEATS[seat]
    return available


class CouncilClient:
    """Client for cloud model consultation via CLI tools, Ollama, or OpenRouter.

    The Council is a heavy-compute reasoning engine that Sovwren can consult
    for architectural decisions, complex debugging, and multi-step reasoning.

    This follows the Liaison model: Sovwren prepares a Brief, Council returns Counsel.

    Supports three backends (in order of preference):
    - "cli": Shell out to CLI tools (gemini, codex, claude) - simplest, no API keys
    - "ollama": Uses local Ollama server which routes to Ollama Cloud
    - "openrouter": Uses OpenRouter API (requires API key)
    """

    def __init__(self, provider: str = COUNCIL_PROVIDER):
        self.provider = provider
        self.session = None
        self._council_profile = None
        self._base_url_error = None

        # Detect available CLI seats
        self.cli_seats = _detect_available_cli_seats()
        self.current_cli_seat = None

        # Set up based on provider
        if provider == "cli":
            # CLI mode: use detected CLI tools
            self.api_base = None
            self.models = {k: v[0] for k, v in self.cli_seats.items()}  # shortname -> command
            self.api_key = None
            # Default to first available CLI seat
            if self.cli_seats:
                self.current_cli_seat = list(self.cli_seats.keys())[0]
        elif provider == "ollama":
            self.api_base = COUNCIL_OLLAMA_BASE.rstrip('/')
            self.models = COUNCIL_OLLAMA_MODELS
            self.api_key = None  # Ollama doesn't need API key
        else:  # openrouter
            self.api_base = COUNCIL_OPENROUTER_BASE.rstrip('/')
            self.models = COUNCIL_OPENROUTER_MODELS
            self.api_key = COUNCIL_OPENROUTER_KEY
            self._base_url_error = self._validate_openrouter_base(self.api_base)

        # Set current model (for API-based providers)
        self.current_model_shortname = COUNCIL_DEFAULT_MODEL
        self.current_model = self.models.get(
            COUNCIL_DEFAULT_MODEL,
            list(self.models.values())[0] if self.models else None
        )

    def _validate_openrouter_base(self, base: str) -> Optional[str]:
        """Avoid accidentally sending API keys to arbitrary endpoints."""
        try:
            parsed = urlparse(base)
        except Exception:
            return "Invalid COUNCIL_API_BASE"

        if parsed.scheme.lower() != "https":
            return "COUNCIL_API_BASE must be https:// for OpenRouter"

        host = (parsed.hostname or "").lower()
        if host != "openrouter.ai":
            return "COUNCIL_API_BASE host must be openrouter.ai (refusing to send API key elsewhere)"

        return None

    def _get_council_profile(self) -> dict:
        """Load the Council profile (cached)."""
        if self._council_profile is None:
            self._council_profile = load_profile("council") or {}
        return self._council_profile

    def _get_system_prompt(self) -> str:
        """Build system prompt from Council profile."""
        profile = self._get_council_profile()
        sp = profile.get("system_prompt", {})

        parts = []

        # Role
        if sp.get("role"):
            parts.append(sp["role"])

        # Priority header
        if sp.get("priority_header"):
            parts.append("\n".join(sp["priority_header"]))

        # Context awareness
        if sp.get("context_awareness"):
            parts.append("CONTEXT AWARENESS:\n" + "\n".join(f"- {c}" for c in sp["context_awareness"]))

        # Response style
        if sp.get("response_style"):
            parts.append("RESPONSE STYLE:\n" + "\n".join(f"- {r}" for r in sp["response_style"]))

        # What Council does
        if sp.get("what_council_does"):
            parts.append("WHAT YOU DO:\n" + "\n".join(f"- {w}" for w in sp["what_council_does"]))

        # What Council avoids
        if sp.get("what_council_avoids"):
            parts.append("WHAT YOU AVOID:\n" + "\n".join(f"- {w}" for w in sp["what_council_avoids"]))

        # Output format
        if sp.get("output_format"):
            parts.append("OUTPUT FORMAT:\n" + "\n".join(f"- {o}" for o in sp["output_format"]))

        # Behavioral checksum
        if sp.get("behavioral_checksum"):
            parts.append("\n".join(sp["behavioral_checksum"]))

        return "\n\n".join(parts) if parts else "You are a reasoning engine. Be direct and technical."

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=TIMEOUTS.get("council_gate", 120))
            headers = {"Content-Type": "application/json"}

            # OpenRouter needs auth header
            if self.provider == "openrouter" and self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.session

    async def check_connection(self) -> bool:
        """Check if the backend is accessible."""
        try:
            session = await self._get_session()
            if self.provider == "ollama":
                # Check Ollama is running
                async with session.get(f"{self.api_base}/api/tags") as response:
                    return response.status == 200
            else:
                # Check OpenRouter (needs API key)
                if not self.api_key:
                    return False
                async with session.get(f"{self.api_base}/models") as response:
                    return response.status == 200
        except Exception:
            return False

    def is_available(self) -> bool:
        """Check if Council is configured and potentially available."""
        if self.provider == "cli":
            return bool(self.cli_seats)  # At least one CLI tool installed
        elif self.provider == "ollama":
            return True  # Ollama just needs to be running
        else:
            return bool(self.api_key) and self._base_url_error is None  # OpenRouter needs API key + safe base URL

    async def list_models(self) -> list:
        """List available models/seats."""
        if self.provider == "cli":
            return [
                {
                    "shortname": k,
                    "model_id": v[1],  # description
                    "current": k == self.current_cli_seat,
                    "type": "cli"
                }
                for k, v in self.cli_seats.items()
            ]
        return [
            {"shortname": k, "model_id": v, "current": k == self.current_model_shortname, "type": "api"}
            for k, v in self.models.items()
        ]

    def switch_model(self, shortname: str) -> bool:
        """Switch to a different Council model/seat by shortname."""
        if self.provider == "cli":
            if shortname in self.cli_seats:
                self.current_cli_seat = shortname
                return True
            return False

        if shortname in self.models:
            self.current_model_shortname = shortname
            self.current_model = self.models[shortname]
            return True
        # Try matching the full model ID
        for k, v in self.models.items():
            if v == shortname:
                self.current_model_shortname = k
                self.current_model = v
                return True
        return False

    def get_current_seat_info(self) -> dict:
        """Get info about the current seat for consent display."""
        if self.provider == "cli":
            seat = self.current_cli_seat
            if seat and seat in self.cli_seats:
                cmd, desc = self.cli_seats[seat]
                return {
                    "provider": "cli",
                    "seat": seat,
                    "description": desc,
                    "destination": f"CLI: {seat}",
                }
        return {
            "provider": self.provider,
            "seat": self.current_model_shortname,
            "description": self.current_model,
            "destination": f"{self.provider}: {self.current_model_shortname}",
        }

    async def _consult_ollama(self, brief: str, model: str, system_prompt: str) -> Optional[str]:
        """Send request to Ollama API."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": brief}
        ]

        request_data = {
            "model": model,
            "messages": messages,
            "stream": False
        }

        # Add generation params from profile
        profile = self._get_council_profile()
        gen_params = profile.get("generation_params", {})
        if gen_params.get("temperature") is not None:
            request_data["options"] = {"temperature": gen_params["temperature"]}

        try:
            session = await self._get_session()
            async with session.post(
                f"{self.api_base}/api/chat",
                json=request_data,
                allow_redirects=False,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Ollama returns {"message": {"content": "..."}}
                    return data.get("message", {}).get("content", "").strip()
                else:
                    error_text = await response.text()
                    return f"[Council error: HTTP {response.status}] {error_text[:200]}"
        except asyncio.TimeoutError:
            return f"[Council timeout after {TIMEOUTS.get('council_gate', 120)}s]"
        except Exception as e:
            return f"[Council error: {str(e)[:200]}]"

    async def _consult_openrouter(self, brief: str, model: str, system_prompt: str) -> Optional[str]:
        """Send request to OpenRouter API (OpenAI-compatible)."""
        if self._base_url_error:
            return f"[Council unavailable: {self._base_url_error}]"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": brief}
        ]

        request_data = {
            "model": model,
            "messages": messages,
            "stream": False
        }

        # Add generation params from profile
        profile = self._get_council_profile()
        gen_params = profile.get("generation_params", {})
        if gen_params.get("temperature") is not None:
            request_data["temperature"] = gen_params["temperature"]
        if gen_params.get("max_tokens") is not None:
            request_data["max_tokens"] = gen_params["max_tokens"]

        try:
            session = await self._get_session()
            async with session.post(
                f"{self.api_base}/chat/completions",
                json=request_data,
                allow_redirects=False,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        return data['choices'][0].get('message', {}).get('content', '').strip()
                    return None
                else:
                    error_text = await response.text()
                    return f"[Council error: HTTP {response.status}] {error_text[:200]}"
        except asyncio.TimeoutError:
            return f"[Council timeout after {TIMEOUTS.get('council_gate', 120)}s]"
        except Exception as e:
            return f"[Council error: {str(e)[:200]}]"

    async def _consult_cli(self, brief: str, seat: str) -> Optional[str]:
        """Send request via CLI tool (gemini, codex, etc.).

        This is the preferred method: simpler, no API key management,
        each CLI handles its own auth.
        """
        if seat not in self.cli_seats:
            return f"[Council error: CLI seat '{seat}' not available]"

        cmd_template, _desc = self.cli_seats[seat]
        timeout = TIMEOUTS.get("council_gate", 120)

        import tempfile
        import os
        import sys

        try:
            # Write brief to temp file to avoid shell escaping nightmares
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(brief)
                temp_path = f.name

            # Build command - platform-specific
            is_windows = sys.platform == 'win32'

            if seat == "gemini":
                if is_windows:
                    # PowerShell: use Get-Content
                    cmd = f'powershell -Command "gemini -p (Get-Content -Raw \'{temp_path}\')"'
                else:
                    cmd = f'gemini -p "$(cat {shlex.quote(temp_path)})"'
            elif seat == "codex":
                if is_windows:
                    cmd = f'powershell -Command "codex exec (Get-Content -Raw \'{temp_path}\')"'
                else:
                    cmd = f'codex exec "$(cat {shlex.quote(temp_path)})"'
            else:
                # Fallback: try the template with escaped brief
                escaped_brief = brief.replace('"', '\\"').replace('$', '\\$')
                cmd = cmd_template.replace("{brief}", escaped_brief)

            # Run the command
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=None,  # Use current directory
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return f"[Council timeout after {timeout}s]"

            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass

            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace')[:200]
                return f"[Council error: CLI returned {process.returncode}] {error_msg}"

            # Parse output - strip CLI noise (startup messages, etc.)
            output = stdout.decode('utf-8', errors='replace')

            # Try to extract just the model response
            # Different CLIs have different output formats
            response = self._clean_cli_output(output, seat)
            return response.strip() if response else "[Council error: Empty response]"

        except Exception as e:
            return f"[Council error: {str(e)[:200]}]"

    def _clean_cli_output(self, output: str, seat: str) -> str:
        """Clean CLI output to extract just the model response.

        Different CLIs have different noise (startup messages, timing info, etc.)
        """
        lines = output.split('\n')

        if seat == "gemini":
            # Gemini CLI may have startup noise, look for actual content
            # Skip lines that look like startup/timing info
            content_lines = []
            in_content = False
            for line in lines:
                # Skip common noise patterns
                if any(noise in line.lower() for noise in [
                    'loaded cached', '[startup]', 'recording metric',
                    'duration:', 'error executing tool'
                ]):
                    continue
                # Once we hit real content, keep it
                if line.strip() and not line.startswith('['):
                    in_content = True
                if in_content:
                    content_lines.append(line)
            return '\n'.join(content_lines)

        elif seat == "codex":
            # Codex has verbose startup, look for actual response after noise
            content_lines = []
            found_response = False
            for line in lines:
                # Skip header noise
                if any(noise in line.lower() for noise in [
                    'openai codex', '--------', 'workdir:', 'model:',
                    'provider:', 'approval:', 'sandbox:', 'reasoning',
                    'session id:', 'deprecated:', 'mcp startup',
                    'tokens used', 'plan update', 'exec', 'thinking'
                ]):
                    continue
                # Skip stderr markers
                if line.startswith('[stderr]'):
                    continue
                # Keep content after the noise
                if line.strip():
                    found_response = True
                if found_response:
                    content_lines.append(line)
            return '\n'.join(content_lines)

        # Default: return as-is
        return output

    async def consult(
        self,
        brief: str,
        model: Optional[str] = None,
        seat: Optional[str] = None,
        stream: bool = False
    ) -> Optional[str]:
        """Send a Brief to Council and receive Counsel.

        Args:
            brief: The formatted Brief (from build_council_brief)
            model: Optional model override for API providers (uses current_model if not specified)
            seat: Optional CLI seat override (uses current_cli_seat if not specified)
            stream: Whether to stream the response (default False for Council)

        Returns:
            The Council's response (Counsel), or None on failure
        """
        if not self.is_available():
            if self.provider == "cli":
                return "[Council unavailable: No CLI tools detected (install gemini or codex)]"
            elif self.provider == "ollama":
                return "[Council unavailable: Ollama not running]"
            else:
                if self._base_url_error:
                    return f"[Council unavailable: {self._base_url_error}]"
                return "[Council unavailable: No API key configured]"

        # CLI provider: shell out to CLI tool
        if self.provider == "cli":
            seat = seat or self.current_cli_seat
            if not seat:
                return "[Council unavailable: No CLI seat selected]"
            return await self._consult_cli(brief, seat)

        # API providers: use HTTP
        model = model or self.current_model
        if not model:
            return "[Council unavailable: No model configured]"

        system_prompt = self._get_system_prompt()

        if self.provider == "ollama":
            return await self._consult_ollama(brief, model, system_prompt)
        else:
            return await self._consult_openrouter(brief, model, system_prompt)

    async def consult_with_context(
        self,
        user_query: str,
        mode: str = "Workshop",
        lens: str = "Blue",
        context_band: str = "Unknown",
        recent_turns: list = None,
        request_type: str = "general",
        active_file: tuple = None,
        node_assessment: str = None
    ) -> Optional[str]:
        """Convenience method: build Brief and consult in one call.

        This is the primary interface for Sovwren to consult Council.
        """
        # Redact sensitive content by default (best-effort safety belt).
        brief, _meta = prepare_council_brief(
            mode=mode,
            lens=lens,
            context_band=context_band,
            recent_turns=recent_turns or [],
            user_query=user_query,
            request_type=request_type,
            active_file=active_file,
            node_assessment=node_assessment,
        )

        return await self.consult(brief)

    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()


# Global Council client instance
council_client = CouncilClient()
