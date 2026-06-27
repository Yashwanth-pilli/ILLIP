"""
File utilities for ILLIP AI
"""

import json
from pathlib import Path
from typing import Any, Dict


def read_json_file(file_path: Path) -> Dict[str, Any]:
    """Read and parse a JSON file"""
    if not file_path.exists():
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json_file(file_path: Path, data: Dict[str, Any]) -> None:
    """Write data to a JSON file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_text_file(file_path: Path) -> str:
    """Read a text file"""
    if not file_path.exists():
        return ""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def write_text_file(file_path: Path, content: str) -> None:
    """Write content to a text file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def append_text_file(file_path: Path, content: str) -> None:
    """Append content to a text file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(content)
        f.write('\n')


def delete_file(file_path: Path) -> bool:
    """Delete a file if it exists"""
    if file_path.exists():
        file_path.unlink()
        return True
    return False


def file_exists(file_path: Path) -> bool:
    """Check if file exists"""
    return file_path.exists()
