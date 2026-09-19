"""
Phase 0 Setup and Verification Tests.

Verifies:
1. Project directory structure and essential files exist.
2. Python environment meets minimum version specifications.
3. Core baseline dependencies are installable and importable.
"""
import sys
from pathlib import Path


def test_python_version():
    """Verify that Python version is at least 3.10."""
    assert sys.version_info >= (3, 10), (
        f"Python 3.10+ required, current is {sys.version_info.major}.{sys.version_info.minor}"
    )


def test_required_root_files_exist():
    """Verify essential initialization files exist in the repository root."""
    root_dir = Path(__file__).resolve().parent.parent
    expected_files = [
        "README.md",
        "PROJECT_SPEC.md",
        "ARCHITECTURE.md",
        "requirements.txt",
        ".gitignore",
    ]
    for filename in expected_files:
        filepath = root_dir / filename
        assert filepath.is_file(), f"Expected file '{filename}' was not found in project root."


def test_required_directories_exist():
    """Verify project skeleton directories exist."""
    root_dir = Path(__file__).resolve().parent.parent
    expected_dirs = [
        "src",
        "src/collector",
        "src/storage",
        "src/analysis",
        "src/detection",
        "src/prediction",
        "src/optimization",
        "src/dashboard",
        "tests",
        "experiments",
        "data",
        "docs",
    ]
    for rel_path in expected_dirs:
        dirpath = root_dir / rel_path
        assert dirpath.is_dir(), f"Expected directory '{rel_path}' was not found."


def test_core_dependencies_importable():
    """Verify essential runtime libraries (psutil, sqlite3, pytest) are importable."""
    # psutil is needed for Phase 1 monitoring
    import psutil
    assert hasattr(psutil, "virtual_memory"), "psutil must expose virtual_memory"
    assert hasattr(psutil, "process_iter"), "psutil must expose process_iter"

    # sqlite3 is part of the standard library and needed for Phase 2 storage
    import sqlite3
    assert hasattr(sqlite3, "connect"), "sqlite3 must be functional"


def test_requirements_content():
    """Verify requirements.txt contains the baseline dependencies."""
    root_dir = Path(__file__).resolve().parent.parent
    req_file = root_dir / "requirements.txt"
    content = req_file.read_text(encoding="utf-8")
    assert "psutil" in content, "requirements.txt must list psutil"
    assert "pytest" in content, "requirements.txt must list pytest"
