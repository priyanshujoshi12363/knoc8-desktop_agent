import os
import shutil

from logger import get_logger
from tools.base import Action

log = get_logger("filesystem")


def _expand(path: str) -> str:
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))


def create_file(path: str, content: str = "") -> str:
    path = _expand(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content or "")
    return f"Created file {path}"


def create_folder(path: str) -> str:
    path = _expand(path)
    os.makedirs(path, exist_ok=True)
    return f"Created folder {path}"


def rename(path: str, new_name: str) -> str:
    path = _expand(path)
    target = os.path.join(os.path.dirname(path), new_name)
    os.rename(path, target)
    return f"Renamed to {target}"


def move(path: str, destination: str) -> str:
    result = shutil.move(_expand(path), _expand(destination))
    return f"Moved to {result}"


def copy(path: str, destination: str) -> str:
    path, destination = _expand(path), _expand(destination)
    if os.path.isdir(path):
        shutil.copytree(path, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(path, destination)
    return f"Copied to {destination}"


def delete(path: str) -> str:
    path = _expand(path)
    log.warning("DELETING: %s", path)
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)
    else:
        return f"Path not found: {path}"
    return f"Deleted {path}"


def list_dir(path: str = ".") -> str:
    path = _expand(path)
    entries = sorted(os.listdir(path))[:100]
    return f"Contents of {path}:\n" + "\n".join(entries)


def read_file(path: str) -> str:
    path = _expand(path)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read(8000)
    return f"Content of {path}:\n{content}"


ACTIONS = {
    "create_file": Action(create_file, "Create (or overwrite) a text file.",
                          {"path": "file path", "content": "optional file content"}),
    "create_folder": Action(create_folder, "Create a folder (parents included).",
                            {"path": "folder path"}),
    "rename": Action(rename, "Rename a file or folder.",
                     {"path": "existing path", "new_name": "new name only"}),
    "move": Action(move, "Move a file or folder.",
                   {"path": "source path", "destination": "destination path"}),
    "copy": Action(copy, "Copy a file or folder.",
                   {"path": "source path", "destination": "destination path"}),
    "delete": Action(delete, "Delete a file or folder permanently.",
                     {"path": "path to delete"}, dangerous=True),
    "list": Action(list_dir, "List the contents of a folder.",
                   {"path": "folder path"}),
    "read": Action(read_file, "Read a text file's content.",
                   {"path": "file path"}),
}
