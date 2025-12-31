"""
Report rendering utilities.
"""
import json


def render_report_text(kind: str, content: dict) -> str:
    """Render report content as plain text/markdown."""
    if kind == 'resume':
        return _render_resume_text(content)
    elif kind == 'status':
        return _render_status_text(content)
    elif kind == 'standup':
        return _render_standup_text(content)
    else:
        return json.dumps(content, indent=2)


def render_report_html(kind: str, content: dict) -> str:
    """Render report content as HTML (stub for MVP)."""
    # For MVP, just wrap text in <pre>
    text = render_report_text(kind, content)
    return f"<pre>{text}</pre>"


def _render_resume_text(content: dict) -> str:
    """Render resume as markdown."""
    lines = []
    if 'name' in content:
        lines.append(f"# {content['name']}")
        lines.append("")
    
    for section in content.get('sections', []):
        title = section.get('title', '')
        items = section.get('items', [])
        if title:
            lines.append(f"## {title}")
            lines.append("")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    
    return "\n".join(lines)


def _render_status_text(content: dict) -> str:
    """Render status report as markdown."""
    lines = ["# Status Report", ""]
    
    for section in content.get('sections', []):
        title = section.get('title', '')
        items = section.get('items', [])
        if title:
            lines.append(f"## {title}")
            lines.append("")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    
    return "\n".join(lines)


def _render_standup_text(content: dict) -> str:
    """Render standup as markdown."""
    lines = ["# Standup", ""]
    
    for section in content.get('sections', []):
        title = section.get('title', '')
        items = section.get('items', [])
        if title:
            lines.append(f"## {title}")
            lines.append("")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    
    return "\n".join(lines)
