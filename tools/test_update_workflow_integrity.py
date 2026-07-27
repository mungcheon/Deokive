from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "update-catalog.yml"
TOOL_CALL_RE = re.compile(r"python(?: -X utf8)? (tools/[^\s]+\.py)")


def git_tracked_paths() -> set[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def workflow_python_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    for raw_block in text.split("python - <<'PY'")[1:]:
        block = raw_block.split("\n          PY", 1)[0]
        lines = [
            line[10:] if line.startswith("          ") else line
            for line in block.splitlines()
        ]
        blocks.append("\n".join(lines))
    return blocks


class UpdateWorkflowIntegrityTests(unittest.TestCase):
    def test_workflow_calls_only_tracked_tool_scripts(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        referenced_tools = sorted(set(TOOL_CALL_RE.findall(text)))

        self.assertGreater(len(referenced_tools), 0)
        missing = [path for path in referenced_tools if path not in git_tracked_paths()]

        self.assertEqual([], missing)

    def test_embedded_python_blocks_compile(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        blocks = workflow_python_blocks(text)

        self.assertGreater(len(blocks), 0)
        for index, block in enumerate(blocks, start=1):
            compile(block, f"update-catalog.yml python block {index}", "exec")


if __name__ == "__main__":
    unittest.main()
