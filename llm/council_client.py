"""Council client for cloud model consultation via Ollama Cloud or OpenRouter"""
import asyncio
import aiohttp
from typing import Optional

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
    build_council_brief
)


class CouncilClient:
    """Client for cloud model consultation via Ollama Cloud or OpenRouter.

    The Council is a heavy-compute reasoning engine that NeMo can consult
    for architectural decisions, complex debugging, and multi-step reasoning.

    This follows the Liaison model: NeMo prepares a Brief, Council returns Counsel.

    Supports two backends:
    - "ollama": Uses local Ollama server which routes to Ollama Cloud transparently
    - "openrouter": Uses OpenRouter API (requires API key)
    """

    def __init__(self, provider: str = COUNCIL_PROVIDER):
        self.provider = provider
        self.session = None
        self._council_profile = None

        # Set up based on provider
        if provider == "ollama":
            self.api_base = COUNCIL_OLLAMA_BASE.rstrip('/')
            self.models = COUNCIL_OLLAMA_MODELS
            self.api_key = None  # Ollama doesn't need API key
        else:  # openrouter
            self.api_base = COUNCIL_OPENROUTER_BASE.rstrip('/')
            self.models = COUNCIL_OPENROUTER_MODELS
            self.api_key = COUNCIL_OPENROUTER_KEY

        # Set current model
        self.current_model_shortname = COUNCIL_DEFAULT_MODEL
        self.current_model = self.models.get(
            COUNCIL_DEFAULT_MODEL,
            list(self.models.values())[0] if self.models else None
        )

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
        if self.provider == "ollama":
            return True  # Ollama just needs to be running
        else:
            return bool(self.api_key)  # OpenRouter needs API key

    async def list_models(self) -> list:
        """List available models from the allowlist."""
        return [
            {"shortname": k, "model_id": v, "current": k == self.current_model_shortname}
            for k, v in self.models.items()
        ]

    def switch_model(self, shortname: str) -> bool:
        """Switch to a different Council model by shortname."""
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
                json=request_data
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
                json=request_data
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

    async def consult(
        self,
        brief: str,
        model: Optional[str] = None,
        stream: bool = False
    ) -> Optional[str]:
        """Send a Brief to Council and receive Counsel.

        Args:
            brief: The formatted Brief (from build_council_brief)
            model: Optional model override (uses current_model if not specified)
            stream: Whether to stream the response (default False for Council)

        Returns:
            The Council's response (Counsel), or None on failure
        """
        if not self.is_available():
            if self.provider == "ollama":
                return "[Council unavailable: Ollama not running]"
            else:
                return "[Council unavailable: No API key configured]"

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

        This is the primary interface for NeMo to consult Council.
        """
        brief = build_council_brief(
            mode=mode,
            lens=lens,
            context_band=context_band,
            recent_turns=recent_turns or [],
            user_query=user_query,
            request_type=request_type,
            active_file=active_file,
            node_assessment=node_assessment
        )

        return await self.consult(brief)

    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()


# Global Council client instance
council_client = CouncilClient()
