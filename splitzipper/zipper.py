import base64
import tempfile
import zipfile
from pathlib import Path
from typing import Callable, List


DEFAULT_CHUNK_SIZE = 16 * 1024 * 1024  # 16 MiB


def _iter_chunks(file_path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE):
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def zip_folder(src_folder: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in src_folder.rglob("*"):
            arcname = p.relative_to(src_folder)
            if p.is_dir():
                continue
            zf.write(p, arcname.as_posix())


def split_zip(
    src_folder: str | Path,
    dst_folder: str | Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    ext: str = "b64",
    progress_cb: Callable[[str, int, int], None] | None = None,
) -> List[Path]:
    src_folder = Path(src_folder).expanduser().resolve()
    dst_folder = Path(dst_folder).expanduser().resolve()
    _ensure_dir(dst_folder)

    tmp_zip = Path(tempfile.gettempdir()) / f"{src_folder.stem}.zip"
    if progress_cb:
        progress_cb("compressing", 0, 1)
    zip_folder(src_folder, tmp_zip)
    if progress_cb:
        progress_cb("compressing", 1, 1)

    size = tmp_zip.stat().st_size
    num_parts = (size + chunk_size - 1) // chunk_size

    if num_parts > 1:
        target_dir = dst_folder / src_folder.stem
        _ensure_dir(target_dir)
    else:
        target_dir = dst_folder

    parts: list[Path] = []
    for i, chunk in enumerate(_iter_chunks(tmp_zip, chunk_size), start=1):
        part_name = f"{src_folder.stem}.part{i:03d}.{ext}"
        part_path = target_dir / part_name
        parts.append(part_path)
        if progress_cb:
            progress_cb("splitting", i - 1, num_parts)
        encoded = base64.b64encode(chunk)
        part_path.write_bytes(encoded)
        if progress_cb:
            progress_cb("splitting", i, num_parts)

    tmp_zip.unlink(missing_ok=True)
    return parts
