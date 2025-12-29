from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OBS_PATH = ROOT / "metadata" / "observations.json"


def _parse_rfc3339(dt: str) -> bool:
    """Best-effort RFC3339 check (accepts trailing 'Z')."""
    if not isinstance(dt, str) or not dt.strip():
        return False
    text = dt.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        datetime.fromisoformat(text)
        return True
    except Exception:
        return False


@dataclass
class Issue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _expect_type(value, types: tuple[type, ...], path: str, issues: list[Issue]) -> bool:
    if not isinstance(value, types):
        issues.append(Issue(path, f"expected {', '.join(t.__name__ for t in types)}, got {type(value).__name__}"))
        return False
    return True


def _expect_enum(value, allowed: set[str], path: str, issues: list[Issue]) -> None:
    if value not in allowed:
        issues.append(Issue(path, f"invalid value {value!r}; expected one of {sorted(allowed)}"))


def validate_observations(doc: dict) -> list[Issue]:
    issues: list[Issue] = []

    if not _expect_type(doc, (dict,), "$", issues):
        return issues

    observations = doc.get("observations")
    if observations is None:
        issues.append(Issue("$", "missing required key 'observations'"))
        return issues

    if not _expect_type(observations, (list,), "$.observations", issues):
        return issues

    allowed_interpretation_bias = {"Low", "Medium", "High"}
    allowed_metaphor_momentum = {"Restrained", "Responsive", "Runaway"}
    allowed_consent_sensitivity = {"Conservative", "Neutral", "Lax"}
    allowed_silence_tolerance = {"Good", "Shaky", "Poor"}
    allowed_instruction_boundary_integrity = {"Strong", "Moderate", "Weak"}
    allowed_symbolic_load_capacity = {"Low", "Medium", "High"}

    allowed_backend = {"LM Studio", "Ollama", "Other"}
    allowed_fit = {"recommended", "usable_with_constraints", "not_recommended", "unknown"}

    for i, entry in enumerate(observations):
        base = f"$.observations[{i}]"
        if not _expect_type(entry, (dict,), base, issues):
            continue

        for key in ("model_id", "version", "observed_at", "core_traits"):
            if key not in entry:
                issues.append(Issue(base, f"missing required key {key!r}"))

        model_id = entry.get("model_id")
        if model_id is not None:
            _expect_type(model_id, (str,), f"{base}.model_id", issues)

        version = entry.get("version")
        if version is not None:
            _expect_type(version, (str,), f"{base}.version", issues)

        observed_at = entry.get("observed_at")
        if observed_at is not None:
            if not _expect_type(observed_at, (str,), f"{base}.observed_at", issues):
                pass
            elif not _parse_rfc3339(observed_at):
                issues.append(Issue(f"{base}.observed_at", "expected RFC3339 date-time string"))

        core_traits = entry.get("core_traits")
        if core_traits is not None and _expect_type(core_traits, (dict,), f"{base}.core_traits", issues):
            for key in (
                "interpretation_bias",
                "metaphor_momentum",
                "consent_sensitivity",
                "silence_tolerance",
                "instruction_boundary_integrity",
                "symbolic_load_capacity",
            ):
                if key not in core_traits:
                    issues.append(Issue(f"{base}.core_traits", f"missing required key {key!r}"))

            _expect_enum(core_traits.get("interpretation_bias"), allowed_interpretation_bias, f"{base}.core_traits.interpretation_bias", issues)
            _expect_enum(core_traits.get("metaphor_momentum"), allowed_metaphor_momentum, f"{base}.core_traits.metaphor_momentum", issues)
            _expect_enum(core_traits.get("consent_sensitivity"), allowed_consent_sensitivity, f"{base}.core_traits.consent_sensitivity", issues)
            _expect_enum(core_traits.get("silence_tolerance"), allowed_silence_tolerance, f"{base}.core_traits.silence_tolerance", issues)
            _expect_enum(core_traits.get("instruction_boundary_integrity"), allowed_instruction_boundary_integrity, f"{base}.core_traits.instruction_boundary_integrity", issues)
            _expect_enum(core_traits.get("symbolic_load_capacity"), allowed_symbolic_load_capacity, f"{base}.core_traits.symbolic_load_capacity", issues)

        runtime_context = entry.get("runtime_context")
        if runtime_context is not None and _expect_type(runtime_context, (dict,), f"{base}.runtime_context", issues):
            backend = runtime_context.get("backend")
            if backend is not None:
                _expect_type(backend, (str,), f"{base}.runtime_context.backend", issues)
                _expect_enum(backend, allowed_backend, f"{base}.runtime_context.backend", issues)
            sampler_profile = runtime_context.get("sampler_profile")
            if sampler_profile is not None:
                _expect_type(sampler_profile, (str,), f"{base}.runtime_context.sampler_profile", issues)
            notes = runtime_context.get("notes")
            if notes is not None:
                _expect_type(notes, (str,), f"{base}.runtime_context.notes", issues)

        observations_text = entry.get("observations")
        if observations_text is not None:
            _expect_type(observations_text, (str,), f"{base}.observations", issues)

        sovwren_fit = entry.get("sovwren_fit")
        if sovwren_fit is not None and _expect_type(sovwren_fit, (dict,), f"{base}.sovwren_fit", issues):
            if "status" not in sovwren_fit:
                issues.append(Issue(f"{base}.sovwren_fit", "missing required key 'status'"))
            else:
                _expect_type(sovwren_fit.get("status"), (str,), f"{base}.sovwren_fit.status", issues)
                _expect_enum(sovwren_fit.get("status"), allowed_fit, f"{base}.sovwren_fit.status", issues)

            if "rationale" in sovwren_fit and sovwren_fit.get("rationale") is not None:
                _expect_type(sovwren_fit.get("rationale"), (str,), f"{base}.sovwren_fit.rationale", issues)

    return issues


def main() -> int:
    if not OBS_PATH.exists():
        print(f"Missing file: {OBS_PATH}", file=sys.stderr)
        return 2

    try:
        doc = json.loads(OBS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to read JSON: {OBS_PATH}: {e}", file=sys.stderr)
        return 2

    issues = validate_observations(doc)
    if issues:
        print(f"Invalid: {OBS_PATH}", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print(f"OK: {OBS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

