"""PIPELINE_ORDER: the one place that defines which modules run, and in what order.

Entry-point convention (CLAUDE.md, modules/README.md): each entry names a
module CLASS by dotted path ("modules.<name>.module:<ClassName>"). Modules do
not expose a module-level instance. The pipeline instantiates classes itself
(`pipeline.run.build_modules_safely`) so that a constructor that raises is
isolated as one degraded module instead of an import error that takes down the
service. Modules never import each other (rule 2); only this list knows order.

Order rationale:
  m0_charsafe  first: every other module reads its charsafe_text.
  m2_deobf     before m1: the lexicon runs on BOTH channels (m1 spec.md §3), so
               the parallel normalized channel must exist first.
  m1_lexicon   guard producer (SUBSTRING_COLLISION, HOMONYM) and fast-path input.
  m6_target    guard producer (NON_HUMAN_TARGET) and target owner; cheap, runs
               before the encoder.
  m3_encoder   expensive; publishes its scores in signals (m4 spec.md §4).
  m4_implicit  reads M3's published scores from ctx.signals.
  m5_sarcasm   D1 (see the open m3/m5 ownership question).
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


PIPELINE_ORDER: tuple[RegistryEntry, ...] = (
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
    for entry in PIPELINE_ORDER:
        if entry.name is wanted:
            return load_class(entry)()
    raise KeyError(f"module not in registry: {wanted.value}")

