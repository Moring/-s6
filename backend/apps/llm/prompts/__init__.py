"""
Prompt templates for LLM calls.
"""
from pathlib import Path


def get_analysis_prompt(content: str) -> str:
    """Get worklog analysis prompt."""
    template = Path(__file__).parent / 'worklog.md'
    return template.read_text().format(content=content)


def get_extraction_prompt(content: str) -> str:
    """Get skills extraction prompt."""
    template = Path(__file__).parent / 'skills.md'
    return template.read_text().format(content=content)


def get_report_prompt(kind: str, data: dict) -> str:
    """Get report generation prompt."""
    template = Path(__file__).parent / 'reports.md'
    import json
    data_str = json.dumps(data, indent=2)
    return template.read_text().format(kind=kind, data=data_str)
