from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
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


def workflow_tool_calls(text: str) -> list[str]:
    return TOOL_CALL_RE.findall(text)


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

    def test_embedded_site_status_blocks_write_valid_status_json(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        blocks = workflow_python_blocks(text)

        self.assertEqual(3, len(blocks))
        expected_modes = ["notice", "updating", "normal"]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            (temp_root / "data").mkdir()
            previous_cwd = Path.cwd()
            try:
                os.chdir(temp_root)
                for index, block in enumerate(blocks):
                    exec(
                        compile(block, f"update-catalog.yml python block {index + 1}", "exec"),
                        {"__builtins__": __builtins__},
                        {},
                    )
                    status_path = Path("data/site_status_public.json")
                    self.assertTrue(status_path.exists())
                    status = json.loads(status_path.read_text(encoding="utf-8"))
                    self.assertEqual(expected_modes[index], status.get("mode"))
                    self.assertIsInstance(status.get("message"), str)
                    self.assertIsInstance(status.get("eta"), str)
            finally:
                os.chdir(previous_cwd)

    def test_refresh_regenerates_current_queues_before_backlog_and_consistency_audit(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        calls = workflow_tool_calls(text)

        quality = calls.index("tools/catalog_quality_report.py")
        field_queue = calls.index("tools/build_catalog_field_enrichment_queue.py")
        naming_queue = calls.index("tools/build_catalog_naming_quality_queue.py")
        ichiban_queue = calls.index("tools/build_ichiban_public_quality_queue.py")
        image_queue = calls.index("tools/build_image_enrichment_queue.py")
        source_discovery = calls.index("tools/build_source_discovery_queue.py")
        missing_image_sync = calls.index("tools/sync_missing_image_work_queue_public.py")
        backlog = calls.index("tools/build_catalog_update_backlog.py")
        consistency = calls.index("tools/audit_catalog_report_consistency.py")
        seed = calls.index("tools/generate_seed_catalog_dart.py")

        self.assertLess(quality, field_queue)
        self.assertLess(field_queue, naming_queue)
        self.assertLess(naming_queue, ichiban_queue)
        self.assertLess(ichiban_queue, image_queue)
        self.assertLess(image_queue, source_discovery)
        self.assertLess(source_discovery, missing_image_sync)
        self.assertLess(missing_image_sync, backlog)
        self.assertLess(backlog, consistency)
        self.assertLess(consistency, seed)
        self.assertIn("python tools/sync_missing_image_work_queue_public.py --write", text)
        self.assertIn("python tools/audit_catalog_report_consistency.py --core-only --fail-on-mismatch", text)


if __name__ == "__main__":
    unittest.main()
