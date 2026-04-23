"""Public package entrypoints for heru's stable adapter contract.

Callers may rely on the names re-exported here as the supported public
surface for engine lookup, adapter classes, execution records, and the
unified event models documented in the README API Contract section.
"""

from dataclasses import dataclass
import json
import logging
from typing import Callable

from pydantic import ValidationError

from heru.adapters import (
    ClaudeCLIAdapter,
    CodexCLIAdapter,
    CopilotCLIAdapter,
    EngineError,
    GeminiCLIAdapter,
    GozCLIAdapter,
    OpenCodeAdapter,
    RetryableExecutionFailure,
    _ENGINE_LIMIT_PATTERNS,
    _EXECUTION_INTERRUPTION_PATTERNS,
    _RETRYABLE_EXECUTION_PATTERNS,
    classify_execution_interruption,
    classify_execution_limit,
    classify_retryable_execution_failure,
)
from heru.base import (
    AdapterCapabilities,
    CLIExecutionResult,
    CLIInvocation,
    ExternalCLIAdapter,
    LATEST_CONTINUATION_SENTINEL,
    StreamEventAdapter,
    extract_jsonl_errors,
    extract_jsonl_messages,
    extract_live_timeline,
    extract_stream_errors,
    extract_stream_transcript,
    iter_jsonl_payloads,
)
from heru.types import (
    EngineUsageObservation,
    EngineUsageWindow,
    LiveEvent,
    LiveTimeline,
    RuntimeEngineContinuation,
    UnifiedEvent,
)

logger = logging.getLogger(__name__)

ENGINE_ADAPTER_TYPES: tuple[type[ExternalCLIAdapter], ...] = (
    CodexCLIAdapter,
    OpenCodeAdapter,
    GozCLIAdapter,
    GeminiCLIAdapter,
    CopilotCLIAdapter,
    ClaudeCLIAdapter,
)

ENGINE_REGISTRY: dict[str, ExternalCLIAdapter] = {
    adapter.name: adapter for adapter in (adapter_type() for adapter_type in ENGINE_ADAPTER_TYPES)
}

ENGINE_CHOICES = sorted(ENGINE_REGISTRY.keys())


@dataclass(frozen=True, slots=True)
class UnifiedExecutionView:
    events: tuple[UnifiedEvent, ...]

    def continuation(self) -> RuntimeEngineContinuation | None:
        continuation_id: str | None = None
        for event in self.events:
            if event.kind != "continuation":
                continue
            continuation_id = event.continuation_id or event.content or continuation_id
        if not continuation_id:
            return None
        return RuntimeEngineContinuation(session_id=continuation_id)

    def timeline(
        self,
        *,
        engine_name: str,
        task_id: str | None = None,
        subagent_id: str | None = None,
    ) -> LiveTimeline:
        timeline = LiveTimeline(engine=engine_name, task_id=task_id, subagent_id=subagent_id)
        timeline.events = [LiveEvent.model_validate(event.model_dump(mode="python")) for event in self.events]
        timeline.recompute_counts()
        return timeline

    def transcript(self, *, stderr: str) -> str:
        parts: list[str] = []
        for event in self.events:
            rendered = _render_event_for_transcript(event)
            if rendered:
                parts.append(rendered)
        if not parts:
            return f"[stderr]\n{stderr.strip()}" if stderr.strip() else ""
        if stderr.strip():
            parts.append(f"[stderr]\n{stderr.strip()}")
        return "\n\n".join(parts)


@dataclass(frozen=True, slots=True)
class _UnifiedJsonlLine:
    line_number: int
    raw_line: str
    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class _UnifiedParseWarning:
    message: str
    context: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class _UnifiedJsonlScan:
    candidate_lines: tuple[_UnifiedJsonlLine, ...]
    warnings: tuple[_UnifiedParseWarning, ...]


def get_engine(name: str) -> ExternalCLIAdapter:
    """Public engine lookup that resolves a stable engine name to its adapter."""
    try:
        return ENGINE_REGISTRY[name]
    except KeyError as exc:
        raise EngineError(f"Unknown engine '{name}'") from exc


def get_stream_event_adapter(engine_name: str) -> StreamEventAdapter | None:
    adapter = ENGINE_REGISTRY.get(engine_name)
    if adapter is None:
        return None
    return adapter.stream_event_adapter()


def parse_unified_execution(stdout: str) -> UnifiedExecutionView | None:
    scan = _collect_unified_jsonl_candidates(stdout)
    for warning in scan.warnings:
        logger.warning(warning.message, *warning.context)

    if not scan.candidate_lines:
        return None

    events: list[UnifiedEvent] = []
    for item_index, candidate in enumerate(scan.candidate_lines, 1):
        try:
            event = UnifiedEvent.model_validate(candidate.payload)
        except ValidationError as exc:
            logger.warning(
                "parse_unified_execution: skipping invalid unified event at line %d (item %d): %s (content: %.200s)",
                candidate.line_number,
                item_index,
                _summarize_validation_error(exc),
                candidate.raw_line,
            )
            continue
        events.append(event)
    if not events:
        logger.warning("parse_unified_execution: detected unified JSONL output but found no valid events")
        return None
    return UnifiedExecutionView(tuple(events))


def render_execution_transcript(
    engine_name: str,
    execution: CLIExecutionResult | None,
    *,
    fallback_renderer: Callable[[CLIExecutionResult], str] | None = None,
) -> str:
    if execution is None:
        return ""
    unified = parse_unified_execution(execution.stdout)
    if unified is not None:
        return unified.transcript(stderr=execution.stderr)
    renderer = fallback_renderer or get_engine(engine_name).render_transcript
    return renderer(execution)


def resume_safe_model_override(
    engine_name: str,
    model_name: str | None,
    *,
    resume_session_id: str | None,
) -> str | None:
    if resume_session_id and engine_name == "opencode":
        return None
    return model_name


def resolve_engine_resume_session_id(
    engine_name: str,
    continuation: RuntimeEngineContinuation | str | None,
    *,
    prefer_latest: bool = False,
) -> str | None:
    if isinstance(continuation, str):
        return continuation or None
    if continuation is not None and continuation.resume_id:
        return continuation.resume_id
    if prefer_latest and get_engine(engine_name).supports_continue_latest():
        return LATEST_CONTINUATION_SENTINEL
    return None


def extract_engine_timeline(
    engine_name: str,
    stdout: str,
    *,
    task_id: str | None = None,
    subagent_id: str | None = None,
) -> LiveTimeline | None:
    unified = parse_unified_execution(stdout)
    if unified is not None:
        return unified.timeline(engine_name=engine_name, task_id=task_id, subagent_id=subagent_id)
    if not stdout.strip():
        return None
    adapter = get_stream_event_adapter(engine_name)
    timeline = extract_live_timeline(stdout, engine=engine_name, adapter=adapter)
    if not timeline.events:
        return None
    if task_id is not None:
        timeline.task_id = task_id
    if subagent_id is not None:
        timeline.subagent_id = subagent_id
    return timeline


def extract_engine_continuation_for_execution(
    engine_name: str, execution: CLIExecutionResult | None
) -> RuntimeEngineContinuation | None:
    if execution is None:
        return None
    unified = parse_unified_execution(execution.stdout)
    if unified is not None:
        continuation = unified.continuation()
        if continuation is not None:
            return continuation
    if not execution.stdout.strip():
        return None
    adapter = ENGINE_REGISTRY.get(engine_name)
    if adapter is None:
        return None
    return adapter.extract_continuation(execution)


extract_engine_continuation = extract_engine_continuation_for_execution


def _summarize_validation_error(exc: ValidationError) -> str:
    details: list[str] = []
    for error in exc.errors(include_url=False):
        location = ".".join(str(part) for part in error.get("loc", ())) or "<root>"
        message = error.get("msg", "validation error")
        details.append(f"{location}: {message}")
    return "; ".join(details) if details else str(exc)


def _render_event_for_transcript(event: UnifiedEvent) -> str:
    if event.kind in {"message", "status"} and event.content:
        return event.content
    if event.kind == "error" and event.error:
        return event.error
    if event.kind not in {"tool_call", "tool_result"}:
        return ""

    lines = ["```tool"]
    if event.tool_name:
        lines.append(f"name: {event.tool_name}")
    if event.tool_input:
        lines.append("input:")
        lines.append(event.tool_input.rstrip())
    if event.tool_output:
        lines.append("output:")
        lines.append(event.tool_output.rstrip())
    if event.error:
        lines.append("error:")
        lines.append(event.error.rstrip())
    lines.append("```")
    return "\n".join(lines)


def _collect_unified_jsonl_candidates(stdout: str) -> _UnifiedJsonlScan:
    candidates: list[_UnifiedJsonlLine] = []
    rejected_lines: list[_UnifiedParseWarning] = []
    native_lines: list[_UnifiedParseWarning] = []
    saw_jsonl_like_content = False

    for line_number, raw_line in enumerate(stdout.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        looks_like_jsonl = line.startswith("{") or line.startswith("[")
        try:
            payload = json.loads(line)
        except (json.JSONDecodeError, ValueError) as exc:
            if looks_like_jsonl:
                saw_jsonl_like_content = True
            rejected_lines.append(
                _UnifiedParseWarning(
                    "parse_unified_execution: skipping unparseable JSONL line %d: %s (content: %.200s)",
                    (line_number, exc, line),
                )
            )
            continue
        saw_jsonl_like_content = True
        if not isinstance(payload, dict):
            rejected_lines.append(
                _UnifiedParseWarning(
                    "parse_unified_execution: skipping non-object JSONL line %d (type=%s, content: %.200s)",
                    (line_number, type(payload).__name__, line),
                )
            )
            continue
        if "kind" in payload:
            candidates.append(_UnifiedJsonlLine(line_number=line_number, raw_line=line, payload=payload))
            continue
        if _is_native_engine_payload(payload):
            native_lines.append(
                _UnifiedParseWarning(
                    "parse_unified_execution: skipping native engine payload at line %d while parsing unified output (content: %.200s)",
                    (line_number, line),
                )
            )
            continue
        rejected_lines.append(
            _UnifiedParseWarning(
                "parse_unified_execution: skipping JSON object without unified event kind at line %d (content: %.200s)",
                (line_number, line),
            )
        )

    warnings: list[_UnifiedParseWarning] = []
    if candidates:
        warnings.extend(rejected_lines)
        warnings.extend(native_lines)
    elif saw_jsonl_like_content and not native_lines:
        warnings.extend(rejected_lines)

    return _UnifiedJsonlScan(candidate_lines=tuple(candidates), warnings=tuple(warnings))


def _is_native_engine_payload(payload: dict[str, object]) -> bool:
    return "type" in payload or isinstance(payload.get("event"), dict)


__all__ = [
    "AdapterCapabilities",
    "CLIExecutionResult",
    "CLIInvocation",
    "ClaudeCLIAdapter",
    "CodexCLIAdapter",
    "CopilotCLIAdapter",
    "ENGINE_ADAPTER_TYPES",
    "ENGINE_CHOICES",
    "ENGINE_REGISTRY",
    "EngineError",
    "EngineUsageObservation",
    "EngineUsageWindow",
    "ExternalCLIAdapter",
    "GeminiCLIAdapter",
    "GozCLIAdapter",
    "LiveEvent",
    "LiveTimeline",
    "OpenCodeAdapter",
    "RetryableExecutionFailure",
    "RuntimeEngineContinuation",
    "StreamEventAdapter",
    "UnifiedEvent",
    "_ENGINE_LIMIT_PATTERNS",
    "_EXECUTION_INTERRUPTION_PATTERNS",
    "_RETRYABLE_EXECUTION_PATTERNS",
    "classify_execution_interruption",
    "classify_execution_limit",
    "classify_retryable_execution_failure",
    "extract_engine_continuation",
    "extract_engine_timeline",
    "extract_jsonl_errors",
    "extract_jsonl_messages",
    "extract_live_timeline",
    "extract_stream_errors",
    "extract_stream_transcript",
    "get_engine",
    "get_stream_event_adapter",
    "iter_jsonl_payloads",
    "render_execution_transcript",
    "resolve_engine_resume_session_id",
    "resume_safe_model_override",
]
