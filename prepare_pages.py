"""Prepare static Pages files locally; never run converter code or deploy."""
import argparse
import pathlib
import shutil

from build_index import build


def prepare(root, output):
    root, output = pathlib.Path(root).resolve(), pathlib.Path(output).absolute()
    if output.exists() or output.is_symlink() or output.resolve().is_relative_to(root):
        raise ValueError("Pages output must be a new directory outside the registry")
    build(root)
    for name in ("index.html", "README.md", "LICENSE", "NOTICE", "LICENSING.md"):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or unsafe static file: " + name)
    output.mkdir(parents=True)
    for name in ("index.html", "index.json", "feedback.json", "README.md", "LICENSE", "NOTICE", "LICENSING.md"):
        shutil.copyfile(root / name, output / name)
    shutil.copytree(root / "converters", output / "converters")
    (output / ".nojekyll").write_text("")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("output")
    args = parser.parse_args()
    print(prepare(args.root, args.output))
