"""Static checks for the non-negotiable rules in CLAUDE.md.

  * no module imports another module, nor pipeline/decision/api/eval (rule 2)
  * no threshold outside decision/thresholds.yaml (rule 4): no float literal
    in a comparison, and no numeric literal bound to a threshold-like name
  * core imports only the standard library + pyyaml (rule 6); a module may
    additionally import what its own requirements.txt declares
  * every module folder has the required layout and a complete spec.md (rule 7)
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
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
SPEC_SECTIONS = ("## Purpose", "## What it catches", "## What it deliberately does NOT catch",
                 "## Input / output contract", "## Approach and tools", "## Forbidden shortcuts",
                 "## Metric", "## Acceptance criteria")


def python_files(*dirs: str, include_tests: bool = True) -> list[Path]:
    files: list[Path] = []
    for d in dirs:
        for path in sorted((ROOT / d).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if not include_tests and path.name.startswith("test_"):
                continue
            files.append(path)
    return files


def imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                names.append("." * node.level + (node.module or ""))
            elif node.module:
                names.append(node.module)
    return names


def module_dirs() -> list[Path]:
    return sorted(p for p in (ROOT / "modules").iterdir() if p.is_dir() and re.match(r"m\d+_", p.name))


class ArchitectureTest(unittest.TestCase):
    def test_modules_do_not_import_each_other(self) -> None:
        forbidden_roots = {"pipeline", "decision", "api", "eval"}
        for mdir in module_dirs():
            for path in python_files(f"modules/{mdir.name}"):
                for name in imported_names(path):
                    with self.subTest(file=str(path.relative_to(ROOT)), imports=name):
                        self.assertFalse(name.startswith("."), "relative imports hide cross-module access")
                        parts = name.split(".")
                        if parts[0] == "modules":
                            self.assertTrue(len(parts) > 1 and parts[1] == mdir.name,
                                            f"{mdir.name} imports {name}")
                        # eval.py / test_unit.py are measurement tooling and may use the
                        # harness; runtime code must not reach pipeline or decision.
                        if path.name not in ("eval.py", "test_unit.py"):
                            self.assertNotIn(parts[0], forbidden_roots)

    def test_no_thresholds_outside_yaml(self) -> None:
        files = python_files(*CORE_DIRS, "modules", include_tests=False)
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            rel = str(path.relative_to(ROOT))
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    operands = [node.left, *node.comparators]
                    floats = [o for o in operands if isinstance(o, ast.Constant) and isinstance(o.value, float)]
                    self.assertFalse(floats, f"{rel}:{node.lineno} compares against a float literal")
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    value = node.value
                    if isinstance(value, ast.Constant) and isinstance(value.value, (int, float)) \
                            and not isinstance(value.value, bool):
                        for target in targets:
                            name = getattr(target, "id", getattr(target, "attr", ""))
                            self.assertFalse(THRESHOLD_NAME.search(name),
                                             f"{rel}:{node.lineno} binds a numeric literal to {name}")
                if isinstance(node, ast.keyword) and node.arg and THRESHOLD_NAME.search(node.arg):
                    self.assertFalse(isinstance(node.value, ast.Constant) and node.value.value is not None,
                                     f"{rel}: literal passed as {node.arg}=")
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = node.args.args[-len(node.args.defaults):] if node.args.defaults else []
                    for arg, default in zip(args, node.args.defaults):
                        if THRESHOLD_NAME.search(arg.arg):
                            self.assertFalse(isinstance(default, ast.Constant) and default.value is not None,
                                             f"{rel}:{node.lineno} default value for {arg.arg}")

    def test_core_is_stdlib_plus_pyyaml(self) -> None:
        allowed = set(sys.stdlib_module_names) | PROJECT_PACKAGES | CORE_THIRD_PARTY | {"__future__"}
        core = python_files(*CORE_DIRS, "tests") + [ROOT / "modules" / "registry.py", ROOT / "modules" / "__init__.py"]
        for path in core:
            for name in imported_names(path):
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
                for name in imported_names(path):
                    with self.subTest(file=str(path.relative_to(ROOT)), imports=name):
                        self.assertIn(name.split(".")[0], base | declared)

    def test_root_requirements_are_pyyaml_only(self) -> None:
        lines = [l.split("#", 1)[0].strip() for l in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([l for l in lines if l][:1], ["pyyaml>=6.0"])
        self.assertEqual(len([l for l in lines if l]), 1)

    def test_module_layout_and_specs(self) -> None:
        registered = {entry.name.value for entry in registry.REGISTRY}
        self.assertEqual({d.name for d in module_dirs()}, registered)
        for mdir in module_dirs():
            for filename in MODULE_FILES:
                self.assertTrue((mdir / filename).exists(), f"{mdir.name}/{filename} missing")
            self.assertTrue((mdir / "fixtures").is_dir(), f"{mdir.name}/fixtures missing")
            spec = (mdir / "spec.md").read_text(encoding="utf-8")
            for section in SPEC_SECTIONS:
                self.assertIn(section, spec, f"{mdir.name}/spec.md lacks '{section}'")

    def test_registry_classes_match_names(self) -> None:
        for entry in registry.REGISTRY:
            cls = registry.load_class(entry)
            self.assertIs(cls.name, entry.name)
            self.assertTrue(entry.target.startswith(f"modules.{entry.name.value}.module:"))


if __name__ == "__main__":
    unittest.main()
