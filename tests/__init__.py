"""
Test configuration and fixtures
"""

import pytest
from pathlib import Path


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary data directory for tests"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "logs").mkdir()
    (data_dir / "memory").mkdir()
    (data_dir / "tasks").mkdir()
    return data_dir
