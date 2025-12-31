"""
Test configuration for pytest-django.
"""
import pytest
from django.conf import settings


@pytest.fixture
def fake_llm():
    """Ensure fake LLM provider is used in tests."""
    settings.LLM_PROVIDER = 'local'
