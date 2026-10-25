"""Prepare static Pages files locally; never run converter code or deploy."""
import argparse
import pathlib
import shutil

from build_index import build

WORKFLOW_ASSETS = (
    "WORKFLOW.md", "docs/assets/converter-workflow.svg",
    "docs/assets/converter-workflow.png", "docs/assets/converter-workflow.pdf",
    "docs/assets/source/converter-workflow.drawio",
)


def prepare(root, output):
    root, output = pathlib.Path(root).resolve(), pathlib.Path(output).absolute()
    if output.exists() or output.is_symlink() or output.resolve().is_relative_to(root):
        raise ValueError("Pages output must be a new directory outside the registry")
    build(root)
    for name in ("index.html", "README.md", "LICENSE", "NOTICE", "LICENSING.md", "CATALOG.md", "EXTERNAL-QUICKSTART.md", "UPSTREAM-RESEARCH.json"):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or unsafe static file: " + name)
    for name in WORKFLOW_ASSETS:
        path = root / name
        if (not path.is_file() or path.is_symlink() or
                any(p.is_symlink() for p in path.parents if p != root and p.is_relative_to(root)) or
                not path.resolve().is_relative_to(root)):
            raise ValueError("Missing or unsafe workflow asset: " + name)
    output.mkdir(parents=True)
    for name in ("index.html", "index.json", "feedback.json", "README.md", "LICENSE", "NOTICE", "LICENSING.md", "CATALOG.md", "EXTERNAL-QUICKSTART.md", "UPSTREAM-RESEARCH.json"):
        shutil.copyfile(root / name, output / name)
    shutil.copytree(root / "converters", output / "converters")
    for name in WORKFLOW_ASSETS:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    (output / ".nojekyll").write_text("")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("output")
    args = parser.parse_args()
    print(prepare(args.root, args.output))
