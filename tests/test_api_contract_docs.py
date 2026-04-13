import ast
import inspect
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import heru
import heru.base as base
import heru.main as main_module
import heru.types as types_module
from heru.adapters.claude import ClaudeCLIAdapter
from heru.adapters.codex import CodexCLIAdapter
from heru.adapters.copilot import CopilotCLIAdapter
from heru.adapters.gemini import GeminiCLIAdapter
from heru.adapters.goz import GozCLIAdapter
from heru.adapters.opencode import OpenCodeAdapter


README = ROOT / "README.md"


def test_readme_api_contract_section_lists_public_and_internal_names() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "## API Contract" in readme
    assert "ExternalCLIAdapter" in readme
    assert "CLIInvocation" in readme
    assert "CLIExecutionResult" in readme
    assert "get_engine" in readme
    assert "ENGINE_CHOICES" in readme
    assert "CodexCLIAdapter" in readme
    assert "ClaudeCLIAdapter" in readme
    assert "CopilotCLIAdapter" in readme
    assert "GeminiCLIAdapter" in readme
    assert "OpenCodeAdapter" in readme
    assert "GozCLIAdapter" in readme
    assert "EngineUsageWindow" in readme
    assert "heru._engine_detection" in readme
    assert "heru.adapters._codex_impl" in readme
    assert "### Stability Matrix" in readme
    assert "v0.1.0" in readme
    assert "semver major version" in readme
    assert "migration note for litehive" in readme


def test_public_modules_classes_and_functions_have_contract_docstrings() -> None:
    public_module_files = [
        ROOT / "heru/__init__.py",
        ROOT / "heru/base.py",
        ROOT / "heru/main.py",
        ROOT / "heru/types.py",
        ROOT / "heru/adapters/codex.py",
        ROOT / "heru/adapters/claude.py",
        ROOT / "heru/adapters/copilot.py",
        ROOT / "heru/adapters/gemini.py",
        ROOT / "heru/adapters/opencode.py",
        ROOT / "heru/adapters/goz.py",
    ]
    for module_file in public_module_files:
        assert '"""Public' in module_file.read_text(encoding="utf-8")

    public_definitions = {
        ROOT / "heru/__init__.py": ["get_engine"],
        ROOT / "heru/base.py": ["CLIInvocation", "CLIExecutionResult", "ExternalCLIAdapter"],
        ROOT / "heru/main.py": ["main"],
        ROOT / "heru/types.py": [
            "EngineUsageWindow",
            "EngineUsageObservation",
            "UnifiedEvent",
            "LiveEvent",
            "LiveTimeline",
            "ResourceLimitEvent",
            "RuntimeEngineContinuation",
            "SubagentRef",
        ],
        ROOT / "heru/adapters/codex.py": ["CodexCLIAdapter"],
        ROOT / "heru/adapters/claude.py": ["ClaudeCLIAdapter"],
        ROOT / "heru/adapters/copilot.py": ["CopilotCLIAdapter"],
        ROOT / "heru/adapters/gemini.py": ["GeminiCLIAdapter"],
        ROOT / "heru/adapters/opencode.py": ["OpenCodeAdapter"],
        ROOT / "heru/adapters/goz.py": ["GozCLIAdapter"],
    }

    for source_file, names in public_definitions.items():
        module = ast.parse(source_file.read_text(encoding="utf-8"))
        docs = {
            node.name: ast.get_docstring(node)
            for node in module.body
            if isinstance(node, ast.ClassDef | ast.FunctionDef)
        }
        for name in names:
            doc = docs.get(name)
            assert doc is not None
            assert "public" in doc.lower()
