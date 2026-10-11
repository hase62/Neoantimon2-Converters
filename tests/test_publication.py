"""Publication-specific checks; no contributed converter is executed."""
import hashlib
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prepare_pages import prepare
from build_index import build, check_immutable

ACCEPTED = {
    "converter.R": "ff2f3c4351df4bc6cfd91719a64edc2adf300f26425cbc19e0c66d20b5a5d8fb",
    "metadata.json": "61004336bc50775936b311a32f52bba33da42b748fa419c88541ec6bd26c6aed",
    "input-X.tsv": "5015bd0f7a22768ea7fed39a2a842b7105eba719c0a29435f5aff1f2f5b1ede2",
    "expected.tsv": "2dbd3a716eb26841c0d62a3c3171c0c1c8bcb8f12b904dda32c9c299a1edc1ba",
}

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.parent = pathlib.Path(self.tmp.name)
        self.root = self.parent / "registry"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "__pycache__"))

    def test_license_notices_are_served_byte_identically(self):
        out = prepare(self.root, self.parent / "site")
        for name in ("LICENSE", "NOTICE", "LICENSING.md"):
            self.assertEqual((out / name).read_bytes(), (self.root / name).read_bytes())

    def test_missing_license_refused_before_output_created(self):
        (self.root / "LICENSE").unlink()
        out = self.parent / "site"
        with self.assertRaisesRegex(ValueError, "LICENSE"):
            prepare(self.root, out)
        self.assertFalse(out.exists())

    def test_symlink_notice_refused(self):
        (self.root / "NOTICE").unlink()
        (self.root / "NOTICE").symlink_to(ROOT / "NOTICE")
        with self.assertRaisesRegex(ValueError, "NOTICE"):
            prepare(self.root, self.parent / "site")

    def test_accepted_bytes_preserved_in_public_artifact(self):
        out = prepare(self.root, self.parent / "site")
        for name, digest in ACCEPTED.items():
            self.assertEqual(hashlib.sha256((out / "converters/synthetic-example@1.0.0" / name).read_bytes()).hexdigest(), digest)

    def test_accepted_file_tamper_rejected(self):
        p = self.root / "converters/synthetic-example@1.0.0/input-X.tsv"
        p.write_bytes(p.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "immutable"):
            check_immutable(ROOT, self.root)

    def test_page_discloses_maintainer_only_feedback_and_license_links(self):
        text = (self.root / "index.html").read_text()
        self.assertIn("both reactions are from @hase62", text)
        self.assertIn("no independent community validation", text)
        for name in ("LICENSE", "NOTICE", "LICENSING.md"):
            self.assertIn('href="' + name + '"', text)

    def test_pages_contains_no_workflows_or_tests(self):
        out = prepare(self.root, self.parent / "site")
        self.assertFalse((out / ".github").exists())
        self.assertFalse((out / "tests").exists())

if __name__ == "__main__":
    unittest.main()
