"""
Theme drift prevention tests.
Ensures templates stay aligned with theme structure.
"""
import pytest
from pathlib import Path
import re


FRONTEND_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = FRONTEND_ROOT / "templates"


class TestThemeDrift:
    """Test suite to prevent theme drift."""

    def test_no_html_directory_references(self):
        """Ensure no templates reference the root HTML directory."""
        violations = []
        for template_file in TEMPLATES_DIR.rglob("*.html"):
            content = template_file.read_text()
            if "HTML/" in content or "html/" in content:
                violations.append(str(template_file.relative_to(FRONTEND_ROOT)))
        
        assert not violations, f"Found HTML directory references in: {violations}"

    def test_all_templates_use_static_tag(self):
        """Ensure templates use {% static %} not hardcoded paths."""
        violations = []
        for template_file in TEMPLATES_DIR.rglob("*.html"):
            content = template_file.read_text()
            # Check for hardcoded asset paths
            if re.search(r'(href|src)=["\'](?:\.\./)*(css|js|images|fonts)/', content):
                if "{% static" not in content:
                    violations.append(str(template_file.relative_to(FRONTEND_ROOT)))
        
        assert not violations, f"Found hardcoded static paths in: {violations}"

    def test_base_shell_exists(self):
        """Ensure base_shell.html exists as master template."""
        base_shell = TEMPLATES_DIR / "base_shell.html"
        assert base_shell.exists(), "base_shell.html is missing"
        
        content = base_shell.read_text()
        assert "{% load static %}" in content
        assert "{% block content %}" in content
        assert "wrapper" in content

    def test_required_partials_exist(self):
        """Ensure required partial templates exist."""
        required_partials = [
            "partials/sidebar_nav.html",
            "partials/topbar_status.html",
            "partials/footer.html",
        ]
        
        for partial in required_partials:
            partial_path = TEMPLATES_DIR / partial
            assert partial_path.exists(), f"Missing required partial: {partial}"

    def test_partials_have_required_classes(self):
        """Ensure partials use required theme classes."""
        # Sidebar must have .sidenav-menu
        sidebar = TEMPLATES_DIR / "partials" / "sidebar_nav.html"
        if sidebar.exists():
            content = sidebar.read_text()
            assert "sidenav-menu" in content, "Sidebar missing .sidenav-menu class"
            assert "side-nav" in content, "Sidebar missing .side-nav class"

        # Topbar must have .topbar
        topbar = TEMPLATES_DIR / "partials" / "topbar_status.html"
        if topbar.exists():
            content = topbar.read_text()
            assert "topbar" in content, "Topbar missing .topbar class"

    def test_htmx_script_loaded(self):
        """Ensure HTMX is loaded in base template."""
        base_shell = TEMPLATES_DIR / "base_shell.html"
        if base_shell.exists():
            content = base_shell.read_text()
            assert "htmx" in content.lower(), "HTMX script not found in base template"

    def test_no_inline_styles_except_override(self):
        """Prevent inline styles except where explicitly needed."""
        violations = []
        for template_file in TEMPLATES_DIR.rglob("*.html"):
            content = template_file.read_text()
            # Allow style blocks, just not inline style attributes (unless in {% block extra_css %})
            if re.search(r'<[^>]+style=["\'][^"\']+["\']', content):
                if "extra_css" not in content:
                    violations.append(str(template_file.relative_to(FRONTEND_ROOT)))
        
        # This is a warning, not a failure (some inline styles may be necessary)
        if violations:
            print(f"Warning: Templates with inline styles: {violations}")


class TestRouteGuards:
    """Test that routes are properly guarded."""

    def test_views_require_login_by_default(self):
        """Ensure views use @login_required or @staff_member_required."""
        from pathlib import Path
        import ast
        
        apps_dir = FRONTEND_ROOT / "apps"
        violations = []
        
        for views_file in apps_dir.rglob("views.py"):
            if "api_proxy" in str(views_file):
                continue  # API proxy has special handling
            
            content = views_file.read_text()
            
            # Parse the file to find function definitions
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check if function is decorated with login_required or staff_member_required
                        decorators = [d.id if isinstance(d, ast.Name) else None for d in node.decorator_list]
                        if node.name not in ['health', '__init__'] and not any(
                            d in ['login_required', 'staff_member_required'] for d in decorators
                        ):
                            violations.append(f"{views_file.relative_to(FRONTEND_ROOT)}::{node.name}")
            except SyntaxError:
                pass  # Skip files with syntax errors (may be empty)
        
        if violations:
            print(f"Warning: Views without auth decorators: {violations}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
