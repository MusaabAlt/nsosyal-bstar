"""Execution order of the modules. The ONLY place order is defined.

Modules never import each other (CLAUDE.md rule 2); the pipeline builds them
from these dotted paths. Order rationale:

  m0_charsafe  first: every other module reads its charsafe_text.
  m2_deobf     before m1: the lexicon runs on BOTH channels, so the parallel
               normalized channel must exist before it.
  m1_lexicon   cheap, high-precision signal; feeds the fast path.
  m6_target    cheap regex/rule signal and a guard producer (SELF_DIRECTED,
               NON_HUMAN_TARGET); runs before the fast-path check so those
               guards are never skipped.
  m3_encoder   expensive; publishes embeddings in signals for m4/m5.
  m4_implicit, m5_sarcasm  consume m3 signals, never import m3.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass

from contracts.codes import ModuleName
from contracts.module_api import BaseModule


@dataclass(frozen=True)
class RegistryEntry:
    name: ModuleName
    target: str  # "package.module:ClassName"
    enabled: bool = True


REGISTRY: tuple[RegistryEntry, ...] = (
    RegistryEntry(ModuleName.M0_CHARSAFE, "modules.m0_charsafe.module:CharSafeModule"),
    RegistryEntry(ModuleName.M2_DEOBF, "modules.m2_deobf.module:DeobfModule"),
    RegistryEntry(ModuleName.M1_LEXICON, "modules.m1_lexicon.module:LexiconModule"),
    RegistryEntry(ModuleName.M6_TARGET, "modules.m6_target.module:TargetModule"),
    RegistryEntry(ModuleName.M3_ENCODER, "modules.m3_encoder.module:EncoderModule"),
    RegistryEntry(ModuleName.M4_IMPLICIT, "modules.m4_implicit.module:ImplicitModule"),
    RegistryEntry(ModuleName.M5_SARCASM, "modules.m5_sarcasm.module:SarcasmModule"),
)


def load_class(entry: RegistryEntry) -> type[BaseModule]:
    module_path, _, class_name = entry.target.partition(":")
    return getattr(importlib.import_module(module_path), class_name)


def build(name: ModuleName | str) -> BaseModule:
    """Instantiate a single module by name (used by per-module eval)."""
    wanted = ModuleName(name)
    for entry in REGISTRY:
        if entry.name is wanted:
            return load_class(entry)()
    raise KeyError(f"module not in registry: {wanted.value}")


def build_all() -> list[BaseModule]:
    return [load_class(entry)() for entry in REGISTRY if entry.enabled]
