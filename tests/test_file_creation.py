"""File creation regressions using only temporary files and no model services."""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import unittest

from src.tools.file_ops import FileOperator


class FileCreationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.operator = FileOperator(str(self.workspace))

    def make_symlink(self, link, target, *, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"Symlinks are unavailable: {error}")

    def test_creates_nested_unicode_file(self):
        result = self.operator.create_file("reports/보고서.txt", "원본 내용")
        self.assertTrue(result["success"], result)
        self.assertEqual((self.workspace / "reports/보고서.txt").read_text(encoding="utf-8"), "원본 내용")

    def test_preserves_existing_file(self):
        target = self.workspace / "report.txt"
        target.write_bytes(b"original content")
        result = self.operator.create_file("report.txt", "replacement")
        self.assertFalse(result["success"], result)
        self.assertEqual(target.read_bytes(), b"original content")

    def test_concurrent_creators_do_not_overwrite_the_winner(self):
        barrier = threading.Barrier(2)

        def create(content):
            barrier.wait(timeout=5)
            return content, self.operator.create_file("shared.txt", content)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(create, ("first content", "second content")))
        winners = [content for content, result in results if result["success"]]
        self.assertEqual(len(winners), 1, results)
        self.assertEqual((self.workspace / "shared.txt").read_text(encoding="utf-8"), winners[0])

    def test_rejects_parent_traversal_before_creating_directories(self):
        result = self.operator.create_file("../outside/report.txt", "data")
        self.assertFalse(result["success"], result)
        self.assertFalse((self.root / "outside").exists())

    def test_rejects_absolute_path_outside_workspace(self):
        outside = self.root / "outside.txt"
        result = self.operator.create_file(str(outside), "data")
        self.assertFalse(result["success"], result)
        self.assertFalse(outside.exists())

    def test_rejects_sibling_with_same_name_prefix(self):
        sibling = self.root / "workspace-other" / "report.txt"
        result = self.operator.create_file(str(sibling), "data")
        self.assertFalse(result["success"], result)
        self.assertFalse(sibling.parent.exists())

    def test_allows_absolute_path_inside_workspace(self):
        target = self.workspace / "report.txt"
        result = self.operator.create_file(str(target), "data")
        self.assertTrue(result["success"], result)
        self.assertEqual(target.read_text(encoding="utf-8"), "data")

    def test_resolves_relative_workspace(self):
        operator = FileOperator(os.path.relpath(self.workspace, Path.cwd()))
        result = operator.create_file("nested/report.txt", "data")
        self.assertTrue(result["success"], result)
        self.assertEqual((self.workspace / "nested/report.txt").read_text(encoding="utf-8"), "data")

    def test_rejects_parent_symlink_outside_workspace(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.make_symlink(self.workspace / "link", outside, directory=True)
        result = self.operator.create_file("link/nested/report.txt", "data")
        self.assertFalse(result["success"], result)
        self.assertFalse((outside / "nested").exists())

    def test_preserves_final_symlink_and_target(self):
        target = self.root / "original.txt"
        target.write_bytes(b"original content")
        link = self.workspace / "link.txt"
        self.make_symlink(link, target)
        result = self.operator.create_file("link.txt", "replacement")
        self.assertFalse(result["success"], result)
        self.assertTrue(link.is_symlink())
        self.assertEqual(target.read_bytes(), b"original content")

    def test_dangling_symlink_does_not_create_its_target(self):
        target = self.workspace / "missing.txt"
        link = self.workspace / "link.txt"
        self.make_symlink(link, target)
        result = self.operator.create_file("link.txt", "data")
        self.assertFalse(result["success"], result)
        self.assertTrue(link.is_symlink())
        self.assertFalse(target.exists())

    def test_parent_creation_failure_returns_tool_error(self):
        parent = self.workspace / "parent"
        parent.write_bytes(b"keep me")
        result = self.operator.create_file("parent/report.txt", "data")
        self.assertFalse(result["success"], result)
        self.assertEqual(parent.read_bytes(), b"keep me")

    def test_invalid_input_does_not_create_a_file(self):
        for filename, content in (("", "data"), ("   ", "data"), ("invalid.txt", None)):
            with self.subTest(filename=filename, content=content):
                result = self.operator.create_file(filename, content)
                self.assertFalse(result["success"], result)
        self.assertEqual(list(self.workspace.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
