"""
pytest configuration for address-forge tests.

Sets environment variables needed for all tests so the converter
doesn't raise ValueError before the mocked Anthropic client is used.
"""

import os
import pytest


def pytest_configure(config):
    """Set a dummy API key so converter.py key-check passes in tests."""
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
