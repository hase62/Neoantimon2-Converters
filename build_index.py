"""Validate contributed files as DATA. Never import or execute converters."""
import hashlib
import argparse
import datetime
import json
import pathlib
import re
import tempfile
import math
import stat
import itertools

IMMUTABLE_FIELDS = {"id", "runtime", "script", "sha256", "metadata", "supported_predictor_versions", "source_revision"}
LEGACY_FEEDBACK_FIELDS = {"issue_url", "ok", "ng"}
ISSUE_URL = r"https://github\.com/[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+/issues/[1-9][0-9]*"
VERSION_ID = r"[a-z0-9][a-z0-9-]*@[0-9]+\.[0-9]+\.[0-9]+"
MAX_FILE_BYTES = 2 * 1024 * 1024


def version_files(directory):
    """Reject symlinks/special files before reading or publishing submitted data."""
    files = []
    for path in itertools.chain([directory], directory.rglob("*")):
        mode = path.lstat().st_mode
        if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise ValueError("Unsafe version file: " + str(path))
        if path.is_file():
            if path.stat().st_size > MAX_FILE_BYTES:
                raise ValueError("Synthetic registry files must be at most 2 MiB")
            if path.suffix.lower() not in (".r", ".py", ".json", ".tsv", ".csv", ".md", ".txt") and path.name not in ("LICENSE", "README"):
                raise ValueError("Active web/binary/unsupported content is not a converter submission")
            files.append(path.relative_to(directory))
    if len(files) > 100 or sum((directory / p).stat().st_size for p in files) > 20 * 1024 * 1024:
        raise ValueError("Version exceeds 100 files or 20 MiB")
    return set(files)


def validate_expected(path):
    """Data-only structural check; the R importer remains the biological authority."""
    contract = json.loads(pathlib.Path(__file__).with_name("external-prediction-1.0.0.json").read_text())
    lines = path.read_text(encoding="utf-8").splitlines()

    def decode(cell):
        if cell.startswith('"'):
            if not re.fullmatch(r'"(?:[^"]|"")*"', cell):
                raise ValueError("Malformed expected.tsv quoted field")
            return cell[1:-1].replace('""', '"')
        if '"' in cell:
            raise ValueError("Malformed expected.tsv quoted field")
        return cell

    rows = [[decode(cell) for cell in line.split("\t")] for line in lines]
    if not rows or len(rows[0]) != len(contract["columns"]) or set(rows[0]) != set(contract["columns"]):
        raise ValueError("expected.tsv must have exactly the standard schema columns")
    keys, channels = set(), {}
    optional = {"mhc_key", "predictor_version", "model_version", "score", "unit", "reason"}
    for cells in rows[1:]:
        if len(cells) != len(rows[0]) or any(any(ord(c) < 32 for c in value) for value in cells):
            raise ValueError("Invalid expected.tsv record")
        row = dict(zip(rows[0], cells))
        if any(not row[k] or row[k].strip() != row[k] for k in set(row) - optional):
            raise ValueError("Missing or padded expected.tsv value")
        if row["schema_version"] != contract["schema_version"] or not re.fullmatch("[" + contract["alphabet"] + "]+", row["peptide_sequence"]):
            raise ValueError("Invalid expected.tsv schema version or peptide")
        for key in ("scope", "status", "metric_kind", "metric_semantics", "score_direction"):
            if row[key] not in contract[key]:
                raise ValueError("Invalid expected.tsv " + key)
        if (row["scope"] == "peptide" and row["mhc_key"]) or (row["scope"] == "peptide_hla" and not row["mhc_key"]):
            raise ValueError("Invalid expected.tsv presenter scope")
        # Full presenter resolution and native-task compatibility are checked by R,
        # not inferred here from a different biological algorithm.
        evaluated = row["status"] == "evaluated"
        score = None
        if evaluated:
            try:
                score = float(row["score"])
            except ValueError as e:
                raise ValueError("Invalid expected.tsv score") from e
            if not math.isfinite(score):
                raise ValueError("Invalid expected.tsv score")
        elif row["score"] or not row["reason"]:
            raise ValueError("Non-evaluated expected.tsv rows need empty scores and reasons")
        if row["metric_kind"] == "percentile_rank":
            if row["score_direction"] != "lower_is_better" or row["unit"] != "percent" or row["metric_semantics"] == "raw" or (evaluated and not 0 <= score <= 100):
                raise ValueError("Invalid expected.tsv percentile")
        elif row["metric_semantics"] != "raw":
            raise ValueError("Invalid expected.tsv raw semantics")
        key = tuple(row[k] for k in contract["logical_key"])
        if key in keys:
            raise ValueError("Duplicate expected.tsv prediction")
        keys.add(key)
        channel = tuple(row[k] for k in ("provider", "predictor_version", "model_version", "run_id", "task", "metric"))
        meaning = tuple(row[k] for k in ("scope", "metric_kind", "metric_semantics", "score_direction", "unit"))
        if channel in channels and channels[channel] != meaning:
            raise ValueError("Inconsistent expected.tsv metric channel")
        channels[channel] = meaning


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("Duplicate JSON key: " + key)
        obj[key] = value
    return obj


def feedback_values(entry):
    if not isinstance(entry, dict) or not LEGACY_FEEDBACK_FIELDS <= set(entry) or set(entry) - (LEGACY_FEEDBACK_FIELDS | {"refreshed_at"}):
        raise ValueError("Invalid feedback fields")
    url = entry["issue_url"]
    if url is not None and (not isinstance(url, str) or not re.fullmatch(ISSUE_URL, url) or url.split("/")[4] in (".", "..")):
        raise ValueError("Invalid GitHub issue URL")
    if any(type(entry[k]) is not int or entry[k] < 0 for k in ("ok", "ng")):
        raise ValueError("Invalid feedback counts")
    refreshed = entry.get("refreshed_at")
    if refreshed is not None:
        if not isinstance(refreshed, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", refreshed):
            raise ValueError("Invalid UTC feedback timestamp")
        try:
            datetime.datetime.strptime(refreshed, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as e:
            raise ValueError("Invalid UTC feedback timestamp") from e
    if url is None and (entry["ok"] or entry["ng"] or refreshed is not None):
        raise ValueError("Unlinked feedback must have zero counts and no timestamp")
    return {k: entry[k] for k in ("issue_url", "ok", "ng")}


def read_feedback(root, ids):
    path = root / "feedback.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or unsafe feedback.json")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("feedback.json must be at most 2 MiB")
    data = json.loads(path.read_text(), object_pairs_hook=unique_object)
    if not isinstance(data, dict) or set(data) != {"schema_version", "feedback"} or data["schema_version"] != "1.0.0" or not isinstance(data["feedback"], dict):
        raise ValueError("Invalid feedback mapping")
    entries = data["feedback"]
    if set(entries) - ids:
        raise ValueError("Unknown feedback converter ID")
    return {id: feedback_values(entry) for id, entry in entries.items()}


def check_immutable(base, submitted):
    """Same read-only check used by trusted CI; feedback is outside versions."""
    base, submitted = pathlib.Path(base), pathlib.Path(submitted)
    for old in sorted((base / "converters").glob("*")):
        if not old.is_dir():
            continue
        new = submitted / "converters" / old.name
        if not new.is_dir() or new.is_symlink():
            raise ValueError("Accepted version file lists are immutable: " + old.name)
        old_files = version_files(old)
        new_files = version_files(new)
        if new.is_symlink() or old_files != new_files:
            raise ValueError("Accepted version file lists are immutable: " + old.name)
        for file in old_files:
            candidate = new / file
            if candidate.is_symlink() or not candidate.is_file() or candidate.read_bytes() != (old / file).read_bytes():
                raise ValueError("Accepted versions are immutable: " + old.name)


def build(root):
    root = pathlib.Path(root).resolve()
    entries = []
    versions = root / "converters"
    if versions.is_symlink() or not versions.is_dir():
        raise ValueError("Missing or unsafe converters directory")
    for directory in sorted(versions.iterdir()):
        if directory.is_symlink() or not directory.is_dir() or not re.fullmatch(VERSION_ID, directory.name):
            raise ValueError("Invalid version directory: " + str(directory))
        version_files(directory)
        path = directory / "metadata.json"
        if not path.is_file():
            raise ValueError("Missing metadata.json: " + str(directory))
        if path.is_symlink() or path.parent.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Unsafe metadata path")
        e = json.loads(path.read_text(), object_pairs_hook=unique_object)
        if not isinstance(e, dict) or set(e) not in (IMMUTABLE_FIELDS, IMMUTABLE_FIELDS | LEGACY_FEEDBACK_FIELDS) or not isinstance(e["id"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*@[0-9]+\.[0-9]+\.[0-9]+", e["id"]):
            raise ValueError("Invalid entry: " + str(path))
        if path.parent.name != e["id"] or e["runtime"] not in ("R", "Python"):
            raise ValueError("ID directory or runtime mismatch")
        if not isinstance(e["script"], str):
            raise ValueError("Unsafe script path")
        script = pathlib.PurePosixPath(e["script"])
        if script.is_absolute() or any(p in ("", ".", "..") for p in e["script"].split("/")) or not re.fullmatch(r"[A-Za-z0-9_./@-]+", e["script"]):
            raise ValueError("Unsafe script path")
        supplied = root / script
        actual = supplied.resolve()
        if not actual.is_relative_to(path.parent.resolve()) or supplied.is_symlink() or not actual.is_file():
            raise ValueError("Script must be inside its version directory")
        suffix = ".r" if e["runtime"] == "R" else ".py"
        if actual.suffix.lower() != suffix:
            raise ValueError("Script extension/runtime mismatch")
        sha = hashlib.sha256(actual.read_bytes()).hexdigest()
        if e["sha256"] != sha:
            raise ValueError("Checksum mismatch: " + e["id"])
        m = e["metadata"]
        if not isinstance(m, dict) or set(m) != {"output_schema", "description", "usage", "arguments", "license"} or m["output_schema"] != "external-prediction-1.0.0" or m["arguments"] != ["--input", "--output", "--bundle"]:
            raise ValueError("Incompatible converter contract")
        if any(not isinstance(m[k], str) or not m[k].strip() for k in ("description", "usage", "license")):
            raise ValueError("Missing metadata")
        if not isinstance(e["supported_predictor_versions"], list) or not all(isinstance(v, str) and v for v in e["supported_predictor_versions"]):
            raise ValueError("Invalid predictor versions")
        if not isinstance(e["source_revision"], str) or not e["source_revision"].strip():
            raise ValueError("Missing source revision")
        if LEGACY_FEEDBACK_FIELDS <= set(e):
            # Validate legacy hygiene, but never use immutable copies as feedback.
            feedback_values({k: e[k] for k in LEGACY_FEEDBACK_FIELDS})
        for fixture in ("input-X.tsv", "expected.tsv"):
            if not (path.parent / fixture).is_file() or (path.parent / fixture).is_symlink():
                raise ValueError("Missing synthetic fixture: " + fixture)
        validate_expected(path.parent / "expected.tsv")
        entries.append({k: v for k, v in e.items() if k in IMMUTABLE_FIELDS})
    if len({e["id"] for e in entries}) != len(entries):
        raise ValueError("Duplicate immutable ID")
    feedback = read_feedback(root, {e["id"] for e in entries})
    for entry in entries:
        entry.update(feedback.get(entry["id"], {"issue_url": None, "ok": 0, "ng": 0}))
    output = root / "index.json"
    if output.is_symlink():
        raise ValueError("Unsafe index output")
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root, prefix=".index-", delete=False) as stream:
        temp = pathlib.Path(stream.name)
        stream.write(json.dumps({"schema_version": "1.0.0", "converters": entries}, indent=2) + "\n")
    try:
        temp.replace(output)
    finally:
        temp.unlink(missing_ok=True)
    return entries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--check-immutable", nargs=2, metavar=("BASE", "SUBMITTED"))
    args = parser.parse_args()
    if args.check_immutable:
        check_immutable(*args.check_immutable)
    else:
        build(args.root)
