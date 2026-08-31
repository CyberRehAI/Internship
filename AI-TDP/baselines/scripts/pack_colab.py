"""Pack baselines code + Phase 3 windows as forward-slash ZIP files for Colab."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINES = Path(__file__).resolve().parents[1]
DEFAULT_OUT = BASELINES / "dist"


def _add_file(zf: zipfile.ZipFile, arcname: str, path: Path) -> None:
    info = zipfile.ZipInfo(filename=arcname.replace("\\", "/"))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, path.read_bytes())


def _add_dir_marker(zf: zipfile.ZipFile, arcname: str) -> None:
    name = arcname.replace("\\", "/")
    if not name.endswith("/"):
        name += "/"
    info = zipfile.ZipInfo(name)
    info.external_attr = 0o40755 << 16
    zf.writestr(info, b"")


def _baseline_code_files() -> list[tuple[str, Path]]:
    """Collect (arcname, path) for the baselines package (no windows NPZs)."""
    files: list[tuple[str, Path]] = []
    for p in [
        BASELINES / "__init__.py",
        BASELINES / "requirements.txt",
        BASELINES / "README.md",
    ]:
        if p.is_file():
            files.append((f"baselines/{p.name}", p))
    docs = BASELINES / "docs"
    if docs.is_dir():
        for path in sorted(docs.glob("*.md")):
            files.append((f"baselines/docs/{path.name}", path))
    for root in (
        BASELINES / "models",
        BASELINES / "data",
        BASELINES / "train",
        BASELINES / "eval",
        BASELINES / "detect",
    ):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_dir() or path.name == ".gitkeep":
                continue
            if path.suffix == ".pyc" or "__pycache__" in path.parts:
                continue
            if path.parent.name == "windows" and path.suffix == ".npz":
                continue
            rel = path.relative_to(BASELINES).as_posix()
            files.append((f"baselines/{rel}", path))
    return files


def pack_code(out_path: Path) -> None:
    """Zip baselines package (models, data, train, eval) with forward-slash paths."""
    files = _baseline_code_files()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        _add_dir_marker(zf, "baselines/")
        for arc, path in files:
            _add_file(zf, arc, path)
    with zipfile.ZipFile(out_path, "r") as zf:
        names = zf.namelist()
        if any("\\" in n for n in names):
            raise RuntimeError("ZIP contains backslash entries")
        print(f"Wrote {out_path} ({len(names)} entries)")


def pack_windows(out_path: Path, windows_dir: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in ("train.npz", "val.npz", "test.npz"):
            path = windows_dir / name
            if not path.is_file():
                raise FileNotFoundError(path)
            _add_file(zf, name, path)
    with zipfile.ZipFile(out_path, "r") as zf:
        if any("\\" in n for n in zf.namelist()):
            raise RuntimeError("ZIP contains backslash entries")
    print(f"Wrote {out_path}")


def _pack_model_colab(
    out_path: Path,
    *,
    notebook_name: str,
    guide_name: str,
    model_module: str,
    train_module: str,
    label: str,
) -> None:
    notebook = BASELINES / "notebooks" / notebook_name
    guide = BASELINES / "docs" / guide_name
    if not notebook.is_file():
        raise FileNotFoundError(notebook)

    files = _baseline_code_files()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        _add_dir_marker(zf, "baselines/")
        _add_file(zf, notebook_name, notebook)
        if guide.is_file():
            _add_file(zf, guide_name, guide)
        for arc, path in files:
            _add_file(zf, arc, path)
    with zipfile.ZipFile(out_path, "r") as zf:
        names = zf.namelist()
        if any("\\" in n for n in names):
            raise RuntimeError("ZIP contains backslash entries")
        assert notebook_name in names
        assert f"baselines/models/{model_module}" in names
        assert f"baselines/train/{train_module}" in names
    print(f"Wrote {out_path} ({len(names)} entries) — {label} Colab bundle (no windows)")


def pack_usad_colab(out_path: Path) -> None:
    _pack_model_colab(
        out_path,
        notebook_name="colab_usad.ipynb",
        guide_name="COLAB_USAD_GUIDE.md",
        model_module="usad.py",
        train_module="train_usad.py",
        label="USAD",
    )


def pack_tranad_colab(out_path: Path) -> None:
    _pack_model_colab(
        out_path,
        notebook_name="colab_tranad.ipynb",
        guide_name="COLAB_TRANAD_GUIDE.md",
        model_module="tranad.py",
        train_module="train_tranad.py",
        label="TranAD",
    )


def pack_stacked_cascade_colab(out_path: Path) -> None:
    notebook = BASELINES / "notebooks" / "colab_stacked_cascade.ipynb"
    guide = BASELINES / "docs" / "COLAB_STACKED_CASCADE_GUIDE.md"
    if not notebook.is_file():
        raise FileNotFoundError(notebook)

    files = _baseline_code_files()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        _add_dir_marker(zf, "baselines/")
        _add_file(zf, "colab_stacked_cascade.ipynb", notebook)
        if guide.is_file():
            _add_file(zf, "COLAB_STACKED_CASCADE_GUIDE.md", guide)
        for arc, path in files:
            _add_file(zf, arc, path)
    with zipfile.ZipFile(out_path, "r") as zf:
        names = zf.namelist()
        if any("\\" in n for n in names):
            raise RuntimeError("ZIP contains backslash entries")
        assert "colab_stacked_cascade.ipynb" in names
        assert "baselines/models/stacked_cascade.py" in names
        assert "baselines/train/train_stacked_cascade.py" in names
        assert "baselines/detect/mahalanobis.py" in names
    print(
        f"Wrote {out_path} ({len(names)} entries) - stacked cascade Colab bundle (no windows)"
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Pack Colab zips for baselines")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument(
        "--windows-dir",
        type=Path,
        default=ROOT / "behavior" / "outputs" / "windows",
    )
    p.add_argument(
        "--usad-only",
        action="store_true",
        help="Only write usad_colab.zip",
    )
    p.add_argument(
        "--tranad-only",
        action="store_true",
        help="Only write tranad_colab.zip",
    )
    p.add_argument(
        "--cascade-only",
        action="store_true",
        help="Only write stacked_cascade_colab.zip",
    )
    args = p.parse_args()
    if args.usad_only:
        pack_usad_colab(args.out_dir / "usad_colab.zip")
        return 0
    if args.tranad_only:
        pack_tranad_colab(args.out_dir / "tranad_colab.zip")
        return 0
    if args.cascade_only:
        pack_stacked_cascade_colab(args.out_dir / "stacked_cascade_colab.zip")
        return 0
    pack_code(args.out_dir / "baselines_code.zip")
    pack_windows(args.out_dir / "baselines_windows.zip", args.windows_dir)
    pack_usad_colab(args.out_dir / "usad_colab.zip")
    pack_tranad_colab(args.out_dir / "tranad_colab.zip")
    pack_stacked_cascade_colab(args.out_dir / "stacked_cascade_colab.zip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
