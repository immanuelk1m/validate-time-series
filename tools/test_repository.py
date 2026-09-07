#!/usr/bin/env python3
"""Local repository checks; publication safety tests make no network writes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from subprocess import CompletedProcess
import tempfile
import unittest
from unittest.mock import patch

import publish_github as publisher

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "validate-time-series"


class RepositoryTests(unittest.TestCase):
    def test_single_skill_source(self):
        self.assertEqual(list((ROOT / "skills").rglob("SKILL.md")), [SKILL / "SKILL.md"])
        self.assertFalse((ROOT / "SKILL.md").exists())

    def test_plugin_points_to_skill(self):
        manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["name"], "validate-time-series")
        self.assertEqual(manifest["version"], "1.1.0")
        self.assertNotIn("license", manifest)

    def test_marketplace_local_source(self):
        marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
        self.assertEqual(marketplace["plugins"][0]["source"], {"source": "local", "path": "./"})
        self.assertEqual(marketplace["name"], "validate-time-series")

    def test_local_document_links(self):
        documents = [ROOT / "README.md", ROOT / "README.ko.md", ROOT / "CONTRIBUTING.md"]
        documents += list((ROOT / "docs").glob("*.md"))
        for document in documents:
            for link in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" not in link and not link.startswith("#"):
                    self.assertTrue((document.parent / link.split("#")[0]).is_file(), (document.name, link))

    def test_ci_is_read_only_and_pinned(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("contents: read", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("publish_github.py --execute", workflow)
        for action in re.findall(r"uses: (\S+)", workflow):
            self.assertRegex(action, r"@([0-9a-f]{40})$")

    def test_original_import_metadata_complete(self):
        provenance = json.loads((ROOT / "docs/import-provenance.json").read_text())
        for name, expected in provenance["imported_files_sha256"].items():
            self.assertTrue((ROOT / name).is_file(), name)
            self.assertRegex(expected, r"^[0-9a-f]{64}$")

    def test_packaged_allowlist_has_required_files(self):
        manifest = json.loads((ROOT / publisher.MANIFEST).read_text())
        files = set(manifest["files_sha256"])
        self.assertTrue({"README.md", "tools/publish_github.py",
                         "skills/validate-time-series/SKILL.md"}.issubset(files))
        self.assertNotIn(publisher.MANIFEST, files)

    def test_no_private_source_artifacts(self):
        manifest = json.loads((ROOT / publisher.MANIFEST).read_text())
        for name in manifest["files_sha256"]:
            self.assertNotIn(Path(name).suffix.lower(), {".pdf", ".zip", ".pem", ".key"})
            self.assertNotIn(Path(name).name, {".env", "hosts.yml"})


class PublisherSafetyTests(unittest.TestCase):
    def fixture(self, root: Path, filename: str = "README.md") -> None:
        (root / "README.md").write_text("test\n")
        (root / publisher.MANIFEST).write_text(json.dumps({
            "repository": publisher.REPOSITORY,
            "files_sha256": {filename: hashlib.sha256(b"test\n").hexdigest()}}))

    def test_dry_run_never_calls_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            with patch.object(publisher, "command", side_effect=AssertionError("No subprocess in dry run")):
                result = publisher.publish(root)
        self.assertFalse(result["remote_created"])
        self.assertEqual(result["visibility"], "private")

    def test_modified_file_stops_before_any_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "README.md").write_text("changed\n")
            with patch.object(publisher, "command", side_effect=AssertionError("No tool call allowed")):
                with self.assertRaisesRegex(ValueError, "changed"):
                    publisher.publish(root, execute=True)

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, "../README.md")
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                publisher.packaged_files(root)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "README.md").rename(root / "target.md")
            (root / "README.md").symlink_to(root / "target.md")
            with self.assertRaisesRegex(ValueError, "Symlinks"):
                publisher.packaged_files(root)

    def test_existing_checkout_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / ".git").mkdir()
            with patch.object(publisher.shutil, "which", return_value="/mock/tool"):
                with self.assertRaisesRegex(RuntimeError, "existing Git checkout"):
                    publisher.publish(root, execute=True)

    def test_wrong_account_refused_before_git_init(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            responses = [CompletedProcess([], 0, "", ""), CompletedProcess([], 0, "another-user\n", "")]
            with patch.object(publisher.shutil, "which", return_value="/mock/tool"), \
                 patch.object(publisher, "command", side_effect=responses) as mocked:
                with self.assertRaisesRegex(RuntimeError, "Expected account"):
                    publisher.publish(root, execute=True)
                self.assertEqual(mocked.call_count, 2)
                self.assertFalse((root / ".git").exists())

    def test_publish_flow_mocked_private_and_allowlisted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            calls = []
            def fake_command(cwd, *args, check=True):
                calls.append(args)
                output = ""
                if args[:3] == ("gh", "api", "--hostname"):
                    if "user" in args:
                        output = "immanuelk1m\n"
                    else:
                        return CompletedProcess(args, 1, "", "HTTP 404")
                elif args[:3] == ("git", "config", "--get"):
                    output = "configured-by-user\n"
                elif args[:3] == ("git", "diff", "--cached"):
                    output = "README.md\0repository-files.json\0"
                elif args[:3] == ("gh", "repo", "view"):
                    output = json.dumps({"url": "https://github.com/" + publisher.REPOSITORY,
                                         "isPrivate": True, "nameWithOwner": publisher.REPOSITORY})
                return CompletedProcess(args, 0, output, "")
            with patch.object(publisher.shutil, "which", return_value="/mock/tool"), \
                 patch.object(publisher, "command", side_effect=fake_command):
                result = publisher.publish(root, execute=True)
            create = next(args for args in calls if args[:3] == ("gh", "repo", "create"))
            self.assertIn("--private", create)
            self.assertIn("--push", create)
            self.assertNotIn("--public", create)
            self.assertTrue(result["remote_created"])
            self.assertIn(("git", "add", "--", "README.md", "repository-files.json"), calls)
            self.assertFalse((root / ".git").exists())  # All commands were mocked.


if __name__ == "__main__":
    unittest.main(verbosity=2)
