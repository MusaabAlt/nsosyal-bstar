"""Static checks for the non-negotiable rules in CLAUDE.md.

  * rule 2 - no module imports another module, nor pipeline/decision/api/eval;
    module eval.py entry points get a narrow, declared allow-list
  * rule 4 - no threshold outside decision/thresholds.yaml: no numeric literal
    (or name bound to one) in a comparison, no literal bound to a threshold-like
    name, no float literal in a unittest ordering assertion; module eval.py and
    test_unit.py are scanned too
  * rule 4 - decision-owned fields (threshold / fired / active / suppressed) are
    assigned only in decision/fusion.py, with no exception (B2)
  * rule 6 - core imports only the standard library + pyyaml; a module may
    additionally import what its own requirements.txt declares
  * rule 7 - every module folder has the required layout and a complete spec.md

The checks are pure functions over source text so their enforcement is itself
tested (see ArchitectureRuleSelfTest).
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
import warnings
from pathlib import Path

from modules import registry

ROOT = Path(__file__).resolve().parent.parent
CORE_DIRS = ("contracts", "decision", "pipeline", "api", "eval")
PROJECT_PACKAGES = {"contracts", "modules", "decision", "pipeline", "api", "eval", "tests"}
CORE_THIRD_PARTY = {"yaml"}
# pip distribution name -> import name, for module requirements files
DIST_TO_IMPORT = {"pyyaml": "yaml", "scikit-learn": "sklearn", "onnxruntime": "onnxruntime"}
THRESHOLD_NAME = re.compile(r"(threshold|margin|cutoff|min_confidence)", re.IGNORECASE)
MODULE_FILES = ("__init__.py", "module.py", "spec.md", "test_unit.py", "eval.py")
# The sections every real spec shares (modules/README.md). Specs number their
# sections differently, so headings are matched without the "N. " prefix.
# REQUIRED: a spec missing one fails. RECOMMENDED: a spec missing one only warns -
# m4's "What it must do" is a better title for its approach section than "Approach",
# and prose is never edited to satisfy an automated check (owner decision).
SPEC_SECTIONS = ("Objective", "What it catches / does not catch", "Contract", "Forbidden — with reasons",
                 "Metrics this module must produce", "Required fixtures", "Acceptance criteria",
                 "Definition of done")
SPEC_RECOMMENDED_SECTIONS = ("Approach", "Research pointers")


class SpecSectionWarning(UserWarning):
    """A recommended spec section is absent. Reported, never a failure."""

# Project imports allowed in module code (module.py, __init__.py, test_unit.py, ...):
# the frozen contracts and the module's own package. "{own}" is the module folder.
MODULE_ALLOWED_PROJECT_IMPORTS = ("contracts", "contracts.*", "modules.{own}", "modules.{own}.*")

# Project imports allowed in modules/<name>/eval.py - shared measurement infrastructure
# and the module's OWN code by name; rule 2 does not cover shared infrastructure.
EVAL_ENTRYPOINT_ALLOWED_PROJECT_IMPORTS = ("eval.harness", "contracts", "contracts.*", "modules.{own}.module")

# Numeric constants compared in core code that are operational limits, not moderation
# decisions, with the reason each one is not a threshold.
OPERATIONAL_LIMITS = {"MAX_BODY_BYTES": "HTTP request body size limit in api/main.py",
                      "MAX_LEN": "m3_encoder truncation length in tokens (m3 spec §5), not a score cut-off",
                      "MAX_TIER2_TOKENS": "m2_deobf tokens sent to the morphology analyser per post: a latency "
                                          "guard (m2 spec §5), not a score cut-off",
                      "seed": "the frozen split's seed (42) checked by eval/m1_lexicon_labels.py against the split "
                              "file: an identity check on an input, not a score cut-off"}

# tests/ is not scanned for literals: decision-layer tests must pin their own
# thresholds to test the decision layer independently of placeholder values.
THRESHOLD_SCAN_DIRS = (*CORE_DIRS, "modules")

UNITTEST_ORDERING_ASSERTS = {"assertLess", "assertLessEqual", "assertGreater", "assertGreaterEqual"}

# Contract fields only the decision layer fills (contracts/schema.py "decision layer only").
DECISION_OWNED_ATTRS = {"threshold", "fired", "active", "suppressed"}
# The one file allowed to assign them. No other exception exists.
DECISION_FIELD_OWNER = "decision/fusion.py"


def python_files(*dirs: str) -> list[Path]:
    return [p for d in dirs for p in sorted((ROOT / d).rglob("*.py")) if "__pycache__" not in p.parts]


def imported_names(source: str) -> list[str]:
    """Static imports plus importlib.import_module / __import__ with a literal name."""
    names: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append("." * node.level + (node.module or "") if node.level else (node.module or ""))
        elif isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if called in ("import_module", "__import__"):
                names.append(node.args[0].value)
    return names


def _matches(name: str, pattern: str) -> bool:
    return name == pattern[:-2] or name.startswith(pattern[:-1]) if pattern.endswith(".*") else name == pattern


def module_import_violations(source: str, own: str, filename: str) -> list[str]:
    """Rule 2 for one file inside modules/<own>/."""
    allowed = EVAL_ENTRYPOINT_ALLOWED_PROJECT_IMPORTS if filename == "eval.py" else MODULE_ALLOWED_PROJECT_IMPORTS
    allowed = tuple(p.format(own=own) for p in allowed)
    problems = []
    for name in imported_names(source):
        if name.startswith("."):
            problems.append(f"relative import {name!r} hides cross-module access")
        elif name.split(".")[0] in PROJECT_PACKAGES and not any(_matches(name, p) for p in allowed):
            problems.append(f"{filename} in {own} imports {name!r}; allowed: {', '.join(allowed)}")
    return problems


def _numeric(node: ast.AST) -> bool:
    """True for a numeric literal expression: 0.7, -3, 64 * 1024."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
    if isinstance(node, ast.UnaryOp):
        return _numeric(node.operand)
    if isinstance(node, ast.BinOp):
        return _numeric(node.left) and _numeric(node.right)
    return False


def _literals_outside_subscripts(node: ast.AST):
    """Numeric constants in an expression, skipping subscript indexes (a[1])."""
    if isinstance(node, ast.Subscript):
        yield from _literals_outside_subscripts(node.value)
        return
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        yield node
        return
    for child in ast.iter_child_nodes(node):
        yield from _literals_outside_subscripts(child)


def _identifier(node: ast.AST) -> str | None:
    return node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None


def threshold_violations(source: str, rel: str) -> list[str]:
    """Rule 4 for one file."""
    tree = ast.parse(source)
    problems: list[str] = []
    numeric_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None and _numeric(node.value):
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                name = _identifier(target)
                if name:
                    numeric_names.add(name)
                    if THRESHOLD_NAME.search(name):
                        problems.append(f"{rel}:{node.lineno} binds a numeric literal to {name}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            has_len = any(isinstance(o, ast.Call) and getattr(o.func, "id", "") == "len" for o in operands)
            for operand in operands:
                for lit in _literals_outside_subscripts(operand):
                    if isinstance(lit.value, float) or (lit.value not in (0, 1) and not has_len):
                        problems.append(f"{rel}:{node.lineno} compares against the literal {lit.value!r}")
                for sub in ast.walk(operand):
                    name = _identifier(sub)
                    if name in numeric_names and name not in OPERATIONAL_LIMITS:
                        problems.append(f"{rel}:{node.lineno} compares against {name}, a name bound to a literal")
        elif isinstance(node, ast.Call):
            called = _identifier(node.func)
            if called in UNITTEST_ORDERING_ASSERTS:
                for arg in node.args:
                    if any(isinstance(lit.value, float) for lit in _literals_outside_subscripts(arg)):
                        problems.append(f"{rel}:{node.lineno} {called} against a float literal")
            for kw in node.keywords:
                if kw.arg and THRESHOLD_NAME.search(kw.arg) and _numeric(kw.value):
                    problems.append(f"{rel}:{node.lineno} literal passed as {kw.arg}=")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args.args[-len(node.args.defaults):] if node.args.defaults else []
            for arg, default in zip(args, node.args.defaults):
                if THRESHOLD_NAME.search(arg.arg) and _numeric(default):
                    problems.append(f"{rel}:{node.lineno} numeric default for {arg.arg}")
    return problems


def decision_field_assignments(source: str, rel: str) -> list[str]:
    """Attribute assignments to decision-owned fields, including tuple targets,
    augmented assignment and in-place list mutation of `.suppressed`/`.active`."""
    problems: list[str] = []

    def check_target(target: ast.AST, lineno: int) -> None:
        if isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                check_target(element, lineno)
        elif isinstance(target, ast.Attribute) and target.attr in DECISION_OWNED_ATTRS:
            problems.append(f"{rel}:{lineno} assigns decision-owned .{target.attr}")

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                check_target(target, node.lineno)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            check_target(node.target, node.lineno)
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr in {"append", "extend", "insert", "clear", "remove", "pop"}
              and isinstance(node.func.value, ast.Attribute) and node.func.value.attr in DECISION_OWNED_ATTRS):
            problems.append(f"{rel}:{node.lineno} mutates decision-owned .{node.func.value.attr}")
    return problems


def spec_section_gaps(spec: str) -> tuple[list[str], list[str]]:
    """(missing required sections, missing recommended sections) for one spec."""
    headings = {re.sub(r"^\d+\.\s*", "", line[3:].strip()) for line in spec.splitlines() if line.startswith("## ")}
    return ([s for s in SPEC_SECTIONS if s not in headings],
            [s for s in SPEC_RECOMMENDED_SECTIONS if s not in headings])


def module_dirs() -> list[Path]:
    return sorted(p for p in (ROOT / "modules").iterdir() if p.is_dir() and re.match(r"m\d+_", p.name))


class ArchitectureTest(unittest.TestCase):
    def test_modules_do_not_import_each_other(self) -> None:
        for mdir in module_dirs():
            for path in python_files(f"modules/{mdir.name}"):
                problems = module_import_violations(path.read_text(encoding="utf-8"), mdir.name, path.name)
                self.assertEqual(problems, [], str(path.relative_to(ROOT)))

    def test_no_thresholds_outside_yaml(self) -> None:
        problems = []
        for path in python_files(*THRESHOLD_SCAN_DIRS):
            problems += threshold_violations(path.read_text(encoding="utf-8"), str(path.relative_to(ROOT)))
        self.assertEqual(problems, [])

    def test_only_fusion_assigns_decision_owned_fields(self) -> None:
        problems = []
        for path in python_files(*THRESHOLD_SCAN_DIRS):
            rel = path.relative_to(ROOT).as_posix()
            if rel != DECISION_FIELD_OWNER:
                problems += decision_field_assignments(path.read_text(encoding="utf-8"), rel)
        self.assertEqual(problems, [])

    def test_core_is_stdlib_plus_pyyaml(self) -> None:
        allowed = set(sys.stdlib_module_names) | PROJECT_PACKAGES | CORE_THIRD_PARTY | {"__future__"}
        core = python_files(*CORE_DIRS, "tests") + [ROOT / "modules" / "registry.py", ROOT / "modules" / "__init__.py"]
        for path in core:
            for name in imported_names(path.read_text(encoding="utf-8")):
                with self.subTest(file=str(path.relative_to(ROOT)), imports=name):
                    self.assertIn(name.split(".")[0], allowed)

    def test_modules_import_only_declared_dependencies(self) -> None:
        base = set(sys.stdlib_module_names) | PROJECT_PACKAGES | {"__future__"}
        for mdir in module_dirs():
            declared: set[str] = set()
            req = mdir / "requirements.txt"
            if req.exists():
                for line in req.read_text(encoding="utf-8").splitlines():
                    line = line.split("#", 1)[0].strip()
                    if line:
                        dist = re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0].lower()
                        declared.add(DIST_TO_IMPORT.get(dist, dist.replace("-", "_")))
            for path in python_files(f"modules/{mdir.name}"):
                for name in imported_names(path.read_text(encoding="utf-8")):
                    with self.subTest(file=str(path.relative_to(ROOT)), imports=name):
                        self.assertIn(name.split(".")[0], base | declared)

    def test_root_requirements_are_pyyaml_only(self) -> None:
        lines = [l.split("#", 1)[0].strip() for l in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([l for l in lines if l][:1], ["pyyaml>=6.0"])
        self.assertEqual(len([l for l in lines if l]), 1)

    def test_module_layout_and_specs(self) -> None:
        registered = {entry.name.value for entry in registry.PIPELINE_ORDER}
        self.assertEqual({d.name for d in module_dirs()}, registered)
        for mdir in module_dirs():
            for filename in MODULE_FILES:
                self.assertTrue((mdir / filename).exists(), f"{mdir.name}/{filename} missing")
            self.assertTrue((mdir / "fixtures").is_dir(), f"{mdir.name}/fixtures missing")
            required, recommended = spec_section_gaps((mdir / "spec.md").read_text(encoding="utf-8"))
            self.assertEqual(required, [], f"{mdir.name}/spec.md lacks required section(s)")
            if recommended:
                warnings.warn(f"{mdir.name}/spec.md lacks recommended section(s): {', '.join(recommended)}",
                              SpecSectionWarning, stacklevel=1)

    def test_every_module_declares_whether_it_emits_spans(self) -> None:
        # ADR-001: the no-span fallback exists only for an explicit emits_spans = False.
        for entry in registry.PIPELINE_ORDER:
            cls = registry.load_class(entry)
            with self.subTest(module=entry.name.value):
                self.assertIn("emits_spans", vars(cls))
                self.assertIsInstance(cls.emits_spans, bool)
        by_name = {entry.name.value: registry.load_class(entry) for entry in registry.PIPELINE_ORDER}
        self.assertTrue(by_name["m1_lexicon"].emits_spans)
        self.assertTrue(by_name["m6_target"].emits_spans)

    def test_entry_point_convention(self) -> None:
        # CLAUDE.md "Entry points": PIPELINE_ORDER names classes; no module-level instance.
        self.assertFalse(hasattr(registry, "REGISTRY"))
        for mdir in module_dirs():
            tree = ast.parse((mdir / "module.py").read_text(encoding="utf-8"))
            instances = [t.id for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))
                         for t in (node.targets if isinstance(node, ast.Assign) else [node.target])
                         if isinstance(t, ast.Name) and t.id == "MODULE"]
            self.assertEqual(instances, [], f"{mdir.name}/module.py defines a module-level MODULE")

    def test_m6_runs_before_m1(self) -> None:
        # m1 reads m6's published target to raise NON_HUMAN_TARGET (ADR-005).
        order = [entry.name.value for entry in registry.PIPELINE_ORDER]
        self.assertLess(order.index("m6_target"), order.index("m1_lexicon"))

    def test_registry_classes_match_names(self) -> None:
        for entry in registry.PIPELINE_ORDER:
            cls = registry.load_class(entry)
            self.assertIs(cls.name, entry.name)
            self.assertTrue(entry.target.startswith(f"modules.{entry.name.value}.module:"))


class ArchitectureRuleSelfTest(unittest.TestCase):
    """Proves the allowances are enforced, not merely declared."""

    def test_decision_field_scan_catches_every_assignment_form(self) -> None:
        for bad in ("score.fired = True\n", "s.threshold, s.fired = None, None\n", "g.suppressed.append(c)\n",
                    "form.active = []\n", "t.threshold += 1\n", "out.thread.fired: bool = False\n"):
            with self.subTest(source=bad):
                self.assertNotEqual(decision_field_assignments(bad, "x.py"), [])
        for ok in ("if score.fired is not None:\n    pass\n", "x = ContentScore(c, 0.1, 's', fired=None)\n",
                   "active = [g for g in guards]\n"):
            with self.subTest(source=ok):
                self.assertEqual(decision_field_assignments(ok, "x.py"), [])

    def test_spec_sections_required_fail_recommended_warn(self) -> None:
        full = "\n".join(f"## {i}. {s}" for i, s in enumerate(SPEC_SECTIONS + SPEC_RECOMMENDED_SECTIONS, 1))
        self.assertEqual(spec_section_gaps(full), ([], []))
        no_approach = full.replace("Approach", "What it must do")
        self.assertEqual(spec_section_gaps(no_approach), ([], ["Approach"]))
        no_fixtures = full.replace("## 6. Required fixtures", "## 6. Fixtures")
        self.assertEqual(spec_section_gaps(no_fixtures)[0], ["Required fixtures"])

    def test_eval_entrypoint_allow_list(self) -> None:
        allowed = ("from eval.harness import main_for\n"
                   "from modules.m0_charsafe.module import CharSafeModule\n"
                   "from contracts.codes import FormCode\nimport json\n")
        self.assertEqual(module_import_violations(allowed, "m0_charsafe", "eval.py"), [])

    def test_eval_entrypoint_importing_another_module_fails(self) -> None:
        for bad in ("from modules.m1_lexicon.module import LexiconModule\n",
                    "import modules.m1_lexicon.module\n",
                    "import importlib\nimportlib.import_module('modules.m1_lexicon.module')\n",
                    "from pipeline.run import Pipeline\n",
                    "from decision import fusion\n",
                    "from api.main import main\n",
                    "from eval.run_all import main\n",
                    "from modules import registry\n",
                    "from . import module\n"):
            with self.subTest(source=bad):
                self.assertNotEqual(module_import_violations(bad, "m0_charsafe", "eval.py"), [])

    def test_test_unit_has_no_import_exemption(self) -> None:
        for bad in ("from eval.harness import ModuleEvaluator\n", "from decision import fusion\n",
                    "from modules.m1_lexicon.module import LexiconModule\n"):
            with self.subTest(source=bad):
                self.assertNotEqual(module_import_violations(bad, "m0_charsafe", "test_unit.py"), [])
        ok = "from contracts.module_api import Context\nfrom modules.m0_charsafe.module import CharSafeModule\n"
        self.assertEqual(module_import_violations(ok, "m0_charsafe", "test_unit.py"), [])

    def test_threshold_scan_catches_more_than_decimal_literals(self) -> None:
        for bad in ("LIMIT = 0.7\ndef f(s):\n    return s > LIMIT\n",
                    "def f(s, t):\n    return s >= t + 0.1\n",
                    "def f(repeat_count):\n    return repeat_count >= 3\n",
                    "class C:\n    CUT = 5\n    def f(self, x):\n        return x > self.CUT\n",
                    "self.assertLess(confidence, 0.5)\n",
                    "margin = 2\n",
                    "ContentScore(code, score, source, threshold=0.5)\n",
                    "def f(x, threshold=0.5):\n    return x\n"):
            with self.subTest(source=bad):
                self.assertNotEqual(threshold_violations(bad, "x.py"), [])
        for ok in ("def f(a, b, x):\n    return a[0] < b[1] and len(x) == 3 and x != 0\n",
                   "def f(s, entry):\n    return s >= float(entry['threshold'])\n",
                   "MAX_BODY_BYTES = 64 * 1024\ndef f(n):\n    return n > MAX_BODY_BYTES\n"):
            with self.subTest(source=ok):
                self.assertEqual(threshold_violations(ok, "x.py"), [])


if __name__ == "__main__":
    unittest.main()
