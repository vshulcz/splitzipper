import base64
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

_PART_RE = re.compile(r"\.part(\d{3})\.b64$", re.IGNORECASE)


def _numeric_key(path: Path):
    m = _PART_RE.search(path.name)
    return int(m.group(1)) if m else 0


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def join_and_unzip(
    src_folder: str | Path,
    dst_folder: str | Path,
    *,
    ext: str = "b64",
    progress_cb: Callable[[str, int, int], None] | None = None,
) -> Path:
    src_folder = Path(src_folder).expanduser().resolve()
    dst_folder = Path(dst_folder).expanduser().resolve()
    _ensure_dir(dst_folder)

    parts = sorted(src_folder.glob(f"*.{ext}"), key=_numeric_key)
    if not parts:
        raise FileNotFoundError(f"No .{ext} parts found in {src_folder}")

    num_parts = len(parts)
    base_name = parts[0].stem.split(".part")[0]
    tmp_zip_path = Path(tempfile.gettempdir()) / f"{base_name}.zip"

    with tmp_zip_path.open("wb") as out_f:
        for i, part in enumerate(parts, start=1):
            if progress_cb:
                progress_cb("decoding", i - 1, num_parts)
            data_b64 = part.read_bytes()
            out_f.write(base64.b64decode(data_b64))
            if progress_cb:
                progress_cb("decoding", i, num_parts)

    with zipfile.ZipFile(tmp_zip_path, "r") as zf:
        members = zf.infolist()
        total_members = len(members)

    if total_members > 1:
        extract_dir = dst_folder / base_name
        _ensure_dir(extract_dir)
    else:
        extract_dir = dst_folder

    with zipfile.ZipFile(tmp_zip_path, "r") as zf:
        for idx, member in enumerate(members, start=1):
            if progress_cb:
                progress_cb("extracting", idx - 1, total_members)
            zf.extract(member, path=extract_dir)
            if progress_cb:
                progress_cb("extracting", idx, total_members)

    tmp_zip_path.unlink(missing_ok=True)
    return dst_folder
