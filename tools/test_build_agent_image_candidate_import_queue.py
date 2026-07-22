from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_agent_image_candidate_import_queue import build_queue
from build_agent_image_candidate_import_queue import discover_candidate_files
from build_agent_image_candidate_import_queue import write_html, write_markdown


def _row(**overrides):
    row = {
        "source_store": "애니메이트",
        "name_ko": "원피스 아크릴 키링 (루피)",
        "name_ja": "",
        "affiliation": "원피스",
        "category": "키링",
        "image_url": "",
        "source_url": "",
    }
    row.update(overrides)
    return row


def _candidate(**overrides):
    item = {
        "row_index": 0,
        "name_ko": "원피스 아크릴 키링 (루피)",
        "source_store": "애니메이트",
        "affiliation": "원피스",
        "category": "키링",
        "source_url": "https://www.animate-onlineshop.jp/pd/1668273/",
        "image_url": "https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4589795628072_1.jpg",
        "candidate_title": "원피스 아크릴 키링 루피",
        "confidence": "high",
    }
    item.update(overrides)
    return item


class AgentImageCandidateImportQueueTests(unittest.TestCase):
    def _candidate_file(self, items):
        tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
        path = Path(tmp.name)
        tmp.write(json.dumps({"items": items}, ensure_ascii=False))
        tmp.close()
        self.addCleanup(lambda: path.exists() and path.unlink())
        return path

    def test_builds_ready_queue_for_safe_current_candidate(self):
        report = build_queue([_row()], [self._candidate_file([_candidate()])])

        self.assertEqual(report["summary"]["ready_items"], 1)
        self.assertEqual(report["items"][0]["row_index"], 0)

    def test_rejects_candidate_when_image_already_exists(self):
        report = build_queue(
            [_row(image_url="https://example.test/existing.jpg")],
            [self._candidate_file([_candidate()])],
        )

        self.assertEqual(report["summary"]["ready_items"], 0)
        self.assertEqual(report["rejected_sample"][0]["reason"], "image_already_present")

    def test_import_rejection_keeps_original_candidate_context(self):
        report = build_queue(
            [_row(source_url="https://www.animate-onlineshop.jp/pd/old/")],
            [self._candidate_file([_candidate()])],
        )

        self.assertEqual(report["summary"]["ready_items"], 0)
        rejected = report["rejected_sample"][0]
        self.assertEqual(rejected["reason"], "existing_source_url_conflict")
        self.assertEqual(rejected["image_url"], _candidate()["image_url"])
        self.assertEqual(rejected["candidate_title"], _candidate()["candidate_title"])

    def test_can_build_ready_queue_when_existing_source_overwrite_is_allowed(self):
        report = build_queue(
            [_row(source_url="https://www.animate-onlineshop.jp/")],
            [self._candidate_file([_candidate()])],
            allow_existing_overwrite=True,
        )

        self.assertEqual(report["summary"]["ready_items"], 1)
        self.assertTrue(report["summary"]["allow_existing_overwrite"])

    def test_rejects_duplicate_ready_source_image_pair_for_different_names(self):
        report = build_queue(
            [
                _row(name_ko="상품 A", name_ja="", source_url="https://www.animate-onlineshop.jp/"),
                _row(name_ko="상품 B", name_ja="", source_url="https://www.animate-onlineshop.jp/"),
            ],
            [
                self._candidate_file(
                    [
                        _candidate(row_index=0, name_ko="상품 A", name_ja="", candidate_title="상품 A"),
                        _candidate(row_index=1, name_ko="상품 B", name_ja="", candidate_title="상품 B"),
                    ]
                )
            ],
            allow_existing_overwrite=True,
        )

        self.assertEqual(report["summary"]["ready_items"], 0)
        self.assertIn(
            ("duplicate_ready_source_image_pair", 2),
            report["summary"]["rejected_reasons"],
        )

    def test_rejects_duplicate_ready_row_index_after_import_preflight(self):
        report = build_queue(
            [_row()],
            [
                self._candidate_file(
                    [
                        _candidate(source_store="????"),
                        _candidate(source_store="????"),
                    ]
                )
            ],
        )

        self.assertEqual(report["summary"]["ready_items"], 1)
        self.assertIn(
            ("duplicate_ready_row_index", 1),
            report["summary"]["rejected_reasons"],
        )

    def test_accepts_candidates_key_shape(self):
        tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
        path = Path(tmp.name)
        tmp.write(json.dumps({"candidates": [_candidate()]}, ensure_ascii=False))
        tmp.close()
        self.addCleanup(lambda: path.exists() and path.unlink())

        report = build_queue([_row()], [path])

        self.assertEqual(report["summary"]["ready_items"], 1)

    def test_rejects_nested_current_identity_mismatch(self):
        report = build_queue(
            [_row()],
            [
                self._candidate_file(
                    [
                        {
                            "row_index": 0,
                            "current": {
                                "name_ko": "다른 상품",
                                "source_store": "애니메이트",
                                "affiliation": "원피스",
                                "category": "키링",
                            },
                            "source_url": "https://www.animate-onlineshop.jp/pd/1668273/",
                            "image_url": "https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4589795628072_1.jpg",
                            "candidate_title": "원피스 아크릴 키링 루피",
                            "confidence": "high",
                        }
                    ]
                )
            ],
        )

        self.assertEqual(report["summary"]["ready_items"], 0)
        self.assertEqual(report["rejected_sample"][0]["reason"], "current_name_mismatch")

    def test_rejects_unconfirmed_remapped_candidate(self):
        report = build_queue(
            [_row()],
            [
                self._candidate_file(
                    [
                        _candidate(
                            remap_reason="exact_current_name_match_from_broad_rejected",
                            old_row_index=99,
                            manual_confirmed=False,
                        )
                    ]
                )
            ],
        )

        self.assertEqual(report["summary"]["ready_items"], 0)
        self.assertEqual(
            report["rejected_sample"][0]["reason"],
            "remapped_candidate_requires_manual_confirmation",
        )

    def test_accepts_manually_confirmed_remapped_candidate(self):
        report = build_queue(
            [_row()],
            [
                self._candidate_file(
                    [
                        _candidate(
                            remap_reason="exact_current_name_match_from_broad_rejected",
                            old_row_index=99,
                            manual_confirmed=True,
                        )
                    ]
                )
            ],
        )

        self.assertEqual(report["summary"]["ready_items"], 1)

    def test_ignores_mojibake_candidate_source_store_metadata(self):
        report = build_queue(
            [_row(source_store="애니메이트")],
            [self._candidate_file([_candidate(source_store="????")])],
        )

        self.assertEqual(report["summary"]["ready_items"], 1)
        self.assertIsNone(report["items"][0]["source_store"])

    def test_records_unreadable_candidate_file_without_failing_queue(self):
        tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
        path = Path(tmp.name)
        tmp.write("{not json")
        tmp.close()
        self.addCleanup(lambda: path.exists() and path.unlink())

        report = build_queue([_row()], [path, self._candidate_file([_candidate()])])

        self.assertEqual(report["summary"]["ready_items"], 1)
        self.assertIn(("candidate_file_unreadable", 1), report["summary"]["rejected_reasons"])

    def test_strict_title_match_allows_korean_name_when_japanese_name_exists(self):
        report = build_queue(
            [
                _row(
                    name_ko="프리렌 러버 스트랩",
                    name_ja="フリーレン ラバーストラップ",
                    source_store="장송의 프리렌 공식",
                    affiliation="장송의 프리렌",
                    category="키링",
                )
            ],
            [
                self._candidate_file(
                    [
                        _candidate(
                            name_ko="프리렌 러버 스트랩",
                            name_ja="フリーレン ラバーストラップ",
                            source_store="장송의 프리렌 공식",
                            affiliation="장송의 프리렌",
                            category="키링",
                            source_kind="official_licensed",
                            source_url="https://frieren-anime.jp/goods/toy/2234/",
                            image_url="https://frieren-anime.jp/wp-content/uploads/2026/01/example.jpg",
                            candidate_title="프리렌 러버 스트랩",
                            confidence=0.95,
                        )
                    ]
                )
            ],
        )

        self.assertEqual(report["summary"]["ready_items"], 1)

    def test_writes_review_markdown_and_html(self):
        report = build_queue([_row()], [self._candidate_file([_candidate()])])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            md_path = root / "queue.md"
            html_path = root / "queue.html"

            write_markdown(report, md_path)
            write_html(report, html_path)

            self.assertIn("Agent Image Candidate Import Queue", md_path.read_text(encoding="utf-8"))
            html_text = html_path.read_text(encoding="utf-8")
            self.assertIn("<table>", html_text)
            self.assertIn("ready items", html_text.lower())

    def test_discovers_candidate_files_from_globs_without_duplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "server" / "agent_image_candidates.json"
            second = root / "server" / "manual_image_candidates.json"
            first.parent.mkdir(parents=True)
            first.write_text("[]", encoding="utf-8")
            second.write_text("[]", encoding="utf-8")

            files = discover_candidate_files(
                ["server/*image*candidates*.json", "server/agent_image_candidates.json"],
                root=root,
            )

            self.assertEqual(files, [first, second])

    def test_discovery_skips_generated_review_and_import_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            server = root / "server"
            server.mkdir(parents=True)
            source = server / "agent_image_candidates.json"
            generated = [
                server / "agent_image_candidates_import_queue_current.json",
                server / "agent_image_candidates_import_dryrun.json",
                server / "agent_image_candidates_import_write.json",
                server / "agent_image_candidates_review.json",
                server / "agent_image_candidates_recheck.json",
            ]
            source.write_text("[]", encoding="utf-8")
            for path in generated:
                path.write_text("[]", encoding="utf-8")

            files = discover_candidate_files(["server/*image*candidates*.json"], root=root)

            self.assertEqual(files, [source])


if __name__ == "__main__":
    unittest.main()
