"""The interface every module implements.

A module receives a read-only `Context` and returns a `ModuleOutput` holding
ONLY the partial fields it declared in `provides`. It never sees other modules,
never applies thresholds, never decides an action. `BaseModule` handles timing
and exception capture so every module fails the same visible way - `ok=False`
plus a note - never a crash and never a silent empty result.
"""
from __future__ import annotations

import os
import time
import traceback
from dataclasses import dataclass, field, fields
from types import MappingProxyType
from typing import Any, ClassVar, Mapping, Protocol, runtime_checkable

from contracts.codes import ModuleName
from contracts.schema import ContentScore, FormResult, GuardResult, TargetResult, ThreadSignal

RAW = "raw"
NORMALIZED = "normalized"


def _empty_mapping() -> Mapping[str, Any]:
    return MappingProxyType({})


@dataclass(frozen=True)
class Context:
    """Read-only view handed to a module.

    `text` is the original input and is never replaced. `charsafe_text` comes
    from m0, `normalized_text` from m2 (a PARALLEL channel, not a replacement).
    `signals` holds other modules' published signals keyed by module name -
    the only legal way for one module to use another's work.
    """

    text: str
    charsafe_text: str | None = None
    normalized_text: str | None = None
    signals: Mapping[str, Any] = field(default_factory=_empty_mapping)
    config: Mapping[str, Any] = field(default_factory=_empty_mapping)
    trace_id: str = ""

    def best_text(self, channel: str = RAW) -> str:
        """Best available text for a channel.

        Defaults to the raw channel (charsafe text, falling back to the
        original). The normalized channel is opt-in because blind
        normalization lowered F1 on Turkish: a module must ask for it
        explicitly and tag its scores `@normalized`.
        """
        if channel not in (RAW, NORMALIZED):
            raise ValueError(f"unknown channel: {channel!r}")
        if channel == NORMALIZED and self.normalized_text is not None:
            return self.normalized_text
        return self.charsafe_text if self.charsafe_text is not None else self.text


# Fields a module may declare in `provides`. `signals` and `notes` are always allowed.
PROVIDABLE_FIELDS: frozenset[str] = frozenset(
    {"charsafe_text", "normalized_text", "form", "content", "target", "guards", "thread"}
)


@dataclass
class ModuleOutput:
    """Partial contract. An unset field means "this module has nothing to say"."""

    module: str = ""
    version: str = ""
    ok: bool = True
    latency_ms: float = 0.0
    charsafe_text: str | None = None
    normalized_text: str | None = None
    form: FormResult | None = None
    content: list[ContentScore] = field(default_factory=list)
    target: TargetResult | None = None
    guards: list[GuardResult] = field(default_factory=list)
    thread: ThreadSignal | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def populated_fields(self) -> set[str]:
        """Contract fields carrying a value (used to enforce `provides`)."""
        out: set[str] = set()
        for f in fields(self):
            if f.name in PROVIDABLE_FIELDS:
                value = getattr(self, f.name)
                if value is not None and value != []:
                    out.add(f.name)
        return out


@runtime_checkable
class Module(Protocol):
    name: ModuleName
    version: str
    provides: frozenset[str]

    def load(self) -> None: ...

    def process(self, ctx: Context) -> ModuleOutput: ...


class BaseModule:
    """Uniform timing and exception capture.

    Subclasses implement `_run` only (and optionally `_load` for artifacts).
    """

    name: ClassVar[ModuleName]
    version: ClassVar[str] = "0.0.0"
    provides: ClassVar[frozenset[str]] = frozenset()

    def __init__(self) -> None:
        self._loaded = False
        self._load_error: str | None = None

    def _load(self) -> None:
        """Load artifacts. Override if needed. Must never touch the network."""

    def _run(self, ctx: Context) -> ModuleOutput:
        raise NotImplementedError

    def load(self) -> None:
        if self._loaded:
            return
        try:
            self._load()
        except Exception as exc:  # reported on every call, never swallowed
            self._load_error = f"load failed: {type(exc).__name__}: {exc}"
        self._loaded = True

    def process(self, ctx: Context) -> ModuleOutput:
        start = time.perf_counter()
        self.load()
        if self._load_error is not None:
            out = ModuleOutput(ok=False, notes=[self._load_error])
        else:
            try:
                out = self._run(ctx)
                if not isinstance(out, ModuleOutput):
                    raise TypeError(f"_run returned {type(out).__name__}, expected ModuleOutput")
            except Exception as exc:
                frame = traceback.extract_tb(exc.__traceback__)[-1]
                where = f"{os.path.basename(frame.filename)}:{frame.lineno}"
                out = ModuleOutput(ok=False, notes=[f"{type(exc).__name__}: {exc} ({where})"])
        out.module = self.name.value
        out.version = self.version
        out.latency_ms = (time.perf_counter() - start) * 1000.0
        return out
