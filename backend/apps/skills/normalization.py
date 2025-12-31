"""
Skill name normalization utilities.
"""


def normalize_skill_name(name: str) -> str:
    """
    Normalize a skill name for matching and deduplication.
    
    Examples:
        - "Python" -> "python"
        - "Node.js" -> "nodejs"
        - "React.JS" -> "reactjs"
    """
    normalized = name.lower().strip()
    # Remove common separators
    normalized = normalized.replace('.', '').replace('-', '').replace('_', '')
    # Remove "programming", "language" suffixes
    for suffix in [' programming', ' language', ' framework', ' library']:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
    return normalized
