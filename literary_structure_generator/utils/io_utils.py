"""
I/O utilities

JSON serialization and file handling.

Features:
    - Pydantic model serialization
    - JSON loading/saving with validation
    - File path utilities
    - Artifact directory management
"""

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def save_json(obj: BaseModel, filepath: str, indent: int = 2) -> None:
    """
    Save Pydantic model to JSON file.

    Args:
        obj: Pydantic model object
        filepath: Path to save JSON
        indent: JSON indentation
    """
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(obj.model_dump_json(indent=indent, by_alias=True), encoding="utf-8")


def load_json(filepath: str, model_class: type[T]) -> T:
    """
    Load and validate JSON file as Pydantic model.

    Args:
        filepath: Path to JSON file
        model_class: Pydantic model class

    Returns:
        Validated model object
    """
    input_path = Path(filepath)
    if not input_path.exists():
        raise FileNotFoundError(f"JSON file not found: {filepath}")

    return model_class.model_validate_json(input_path.read_text(encoding="utf-8"))


def ensure_dir(dirpath: str) -> Path:
    """
    Ensure directory exists, create if needed.

    Args:
        dirpath: Directory path

    Returns:
        Path object
    """
    path = Path(dirpath)
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_artifact_structure(base_dir: str, run_id: str) -> dict[str, Path]:
    """
    Create artifact directory structure for a run.

    Args:
        base_dir: Base artifacts directory
        run_id: Unique run identifier

    Returns:
        Dictionary with paths to subdirectories
    """
    root = ensure_dir(str(Path(base_dir) / run_id))

    paths = {
        "root": root,
        "digests": root / "digests",
        "specs": root / "specs",
        "configs": root / "configs",
        "reports": root / "reports",
        "candidates": root / "candidates",
        "final": root / "final",
        "logs": root / "logs",
    }

    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    return paths


def load_text_file(filepath: str, encoding: str = "utf-8") -> str:
    """
    Load text file with encoding handling.

    Args:
        filepath: Path to text file
        encoding: Text encoding

    Returns:
        File contents as string
    """
    input_path = Path(filepath)
    if not input_path.exists():
        raise FileNotFoundError(f"Text file not found: {filepath}")

    return input_path.read_text(encoding=encoding)


def save_text_file(text: str, filepath: str, encoding: str = "utf-8") -> None:
    """
    Save text to file.

    Args:
        text: Text content
        filepath: Path to save file
        encoding: Text encoding
    """
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding=encoding)
