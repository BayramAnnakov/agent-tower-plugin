#!/usr/bin/env python3
"""Tests for OpenCode backend."""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

import pytest
from opencode_backend import OpencodeBackend
from response import AgentRole


class TestOpencodeBackend:
    """Tests for OpencodeBackend class."""

    def test_backend_exists(self):
        """Test that OpencodeBackend can be imported."""
        assert OpencodeBackend is not None
