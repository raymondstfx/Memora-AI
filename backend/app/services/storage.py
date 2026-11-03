import re
import unicodedata
from pathlib import Path, PurePosixPath

from app.services.llm.provider import ChatError


def safe_filename(filename: str) -> str:
    name = PurePosixPath(filename.replace("\\", "/")).name
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r"[^\w. ()-]", "_", name).strip(". ")
    return (name[:170] or "upload") + ("" if name.lower().endswith(".pdf") else ".pdf")


class PrivateStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root) or path == self.root:
            raise ChatError("INVALID_STORAGE_KEY", "Invalid storage reference.", 400)
        return path

    def write(self, key: str, data: bytes) -> None:
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with path.open("xb") as output:
            output.write(data)

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)
