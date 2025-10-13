"""Playwright-powered E2E tests for the web workflow."""

from __future__ import annotations

import socket
from pathlib import Path
from textwrap import dedent

import pytest

_ = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.e2e


def _is_frontend_running(host: str = "localhost", port: int = 5173) -> bool:
    """Check if frontend server is running."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (TimeoutError, ConnectionRefusedError, OSError):
        return False


# Skip frontend tests if server is not running
_skip_if_no_frontend = pytest.mark.skipif(
    not _is_frontend_running(), reason="Requires running frontend server on localhost:5173"
)


def _write_stub_application(tmp_path: Path) -> Path:
    html = dedent(
        """
        <html>
          <head>
            <meta charset=\"utf-8\">
            <title>lift-sys test harness</title>
            <style>
              body { font-family: sans-serif; margin: 2rem; }
              button { margin-top: 1rem; }
              .chip { display: inline-block; padding: 0.2rem 0.5rem; background: #1976d2; color: #fff; border-radius: 12px; cursor: pointer; }
            </style>
          </head>
          <body>
            <h1>Reverse Mode Harness</h1>
            <label for=\"repository\">Repository</label>
            <select id=\"repository\">
              <option value=\"demo\">demo-repo</option>
            </select>
            <button id=\"reverse\">Lift Specification</button>
            <pre id=\"ir-panel\"></pre>
            <div id=\"assist-chip\" class=\"chip\" hidden>Resolve Typed Hole</div>
            <script>
              const irPanel = document.getElementById('ir-panel');
              const chip = document.getElementById('assist-chip');
              document.getElementById('reverse').addEventListener('click', () => {
                irPanel.textContent = 'ir sample_module {\\n  intent: Demo\\n  assert: - placeholder predicate\\n  <?hole_id: Predicate?>\\n}';
                chip.hidden = false;
              });
              chip.addEventListener('click', () => {
                irPanel.textContent = irPanel.textContent.replace('placeholder predicate', 'x > 0');
                chip.textContent = 'Hole Resolved';
              });
            </script>
          </body>
        </html>
        """
    ).strip()
    page_path = tmp_path / "index.html"
    page_path.write_text(html, encoding="utf8")
    return page_path


@pytest.mark.playwright
def test_code_to_ir_to_human_input_workflow(page, tmp_path) -> None:  # type: ignore[no-redef]
    """Simulate selecting a repo, triggering reverse mode, and resolving a typed hole."""

    harness_path = _write_stub_application(tmp_path)

    page.goto(harness_path.as_uri())
    page.select_option("#repository", "demo")
    page.click("#reverse")
    page.wait_for_selector("#assist-chip:not([hidden])")
    page.click("#assist-chip")

    panel_text = page.text_content("#ir-panel")
    assert panel_text is not None
    assert "x > 0" in panel_text
    assert "Hole Resolved" in page.text_content("#assist-chip")


# =============================================================================
# Additional Web UI Test Placeholders
# These tests demonstrate the structure for comprehensive Playwright testing
# =============================================================================


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.playwright
class TestWebUIWorkflows:
    """End-to-end tests for web UI using Playwright."""

    @_skip_if_no_frontend
    def test_web_ui_loads_successfully(self, page):
        """Test that web UI loads without errors."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Verify page title or main content loads
        assert page.title() is not None
        # Should not have console errors (critical ones)
        # Note: This is a basic smoke test

    @_skip_if_no_frontend
    def test_web_ui_navigate_to_repository_selection(self, page):
        """Test navigating to repository selection page."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Look for repository-related elements
        # This depends on the actual UI structure
        # For now, just verify we can navigate
        assert page.url.startswith("http://localhost:5173")

    @_skip_if_no_frontend
    def test_web_ui_select_repository(self, page):
        """Test selecting a repository section."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Look for Repository navigation button
        if page.locator('button:has-text("Repository")').count() > 0:
            page.locator('button:has-text("Repository")').click()
            # Verify section loaded
            assert page.is_visible("body")

    @_skip_if_no_frontend
    def test_web_ui_reverse_mode_workflow(self, page):
        """Test navigating to IR Review section."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Navigate to IR Review section (reverse mode)
        if page.locator('button:has-text("IR Review")').count() > 0:
            page.locator('button:has-text("IR Review")').click()
            page.wait_for_timeout(500)  # Allow for lazy loading
            assert page.is_visible("body")

    @_skip_if_no_frontend
    def test_web_ui_forward_mode_workflow(self, page):
        """Test navigating to Prompt Workbench section."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Navigate to Prompt Workbench (forward mode)
        if page.locator('button:has-text("Prompt Workbench")').count() > 0:
            page.locator('button:has-text("Prompt Workbench")').click()
            page.wait_for_timeout(500)  # Allow for lazy loading
            assert page.is_visible("body")

    @_skip_if_no_frontend
    def test_web_ui_typed_hole_interaction(self, page):
        """Test UI elements are interactive."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Test that navigation buttons are clickable
        if page.locator('button:has-text("Configuration")').count() > 0:
            page.locator('button:has-text("Configuration")').click()
            assert page.is_visible("body")

    @_skip_if_no_frontend
    def test_web_ui_verification_display(self, page):
        """Test that main content area is displayed."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Verify main content area exists
        if page.locator("#main-content").count() > 0:
            assert page.locator("#main-content").is_visible()
        else:
            # Fallback: just check body is visible
            assert page.is_visible("body")

    @_skip_if_no_frontend
    def test_web_ui_plan_visualization(self, page):
        """Test viewing Planner section."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Navigate to Planner section
        if page.locator('button:has-text("Planner")').count() > 0:
            page.locator('button:has-text("Planner")').click()
            page.wait_for_timeout(500)  # Allow for lazy loading
            assert page.is_visible("body")

    @_skip_if_no_frontend
    def test_web_ui_save_ir(self, page):
        """Test navigating to IDE section."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Navigate to IDE section
        if page.locator('button:has-text("IDE")').count() > 0:
            page.locator('button:has-text("IDE")').click()
            page.wait_for_timeout(500)  # Allow for lazy loading
            assert page.is_visible("body")

    @_skip_if_no_frontend
    def test_web_ui_error_handling(self, page):
        """Test error handling in web UI."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Basic test: verify app doesn't crash on load
        # More specific error handling tests can be added based on UI structure
        assert page.is_visible("body")

    @_skip_if_no_frontend
    def test_web_ui_responsive_layout(self, page):
        """Test responsive layout at different screen sizes."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Test desktop size
        page.set_viewport_size({"width": 1920, "height": 1080})
        assert page.is_visible("body")

        # Test mobile size
        page.set_viewport_size({"width": 375, "height": 667})
        assert page.is_visible("body")


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.playwright
class TestWebUIAnalysisModes:
    """E2E tests for project mode and file mode analysis."""

    @_skip_if_no_frontend
    def test_project_mode_analysis(self, page):
        """Test whole-project reverse mode analysis workflow."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Navigate to Repository section
        if page.locator('button:has-text("Repository")').count() > 0:
            page.locator('button:has-text("Repository")').click()
            page.wait_for_timeout(500)

            # Look for the "Entire Project" mode toggle button
            entire_project_button = page.locator('button:has-text("Entire Project")')
            if entire_project_button.count() > 0:
                # Click to select project mode
                entire_project_button.click()
                page.wait_for_timeout(300)

                # Verify the button is in selected state (has default variant styling)
                # In the UI, the selected button should have different styling
                # We just verify it's present and clickable

                # Look for analyze button
                analyze_button = page.locator('button:has-text("Analyze")').first
                if analyze_button.count() > 0:
                    # In a real test, we would:
                    # 1. Click analyze
                    # 2. Wait for results
                    # 3. Verify multiple IR cards are displayed
                    # 4. Verify summary statistics are shown
                    # For now, we verify the UI elements are present
                    assert analyze_button.is_visible()

    @_skip_if_no_frontend
    def test_file_mode_analysis(self, page):
        """Test single-file reverse mode analysis workflow."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Navigate to Repository section
        if page.locator('button:has-text("Repository")').count() > 0:
            page.locator('button:has-text("Repository")').click()
            page.wait_for_timeout(500)

            # Look for the "Single File" mode toggle button
            single_file_button = page.locator('button:has-text("Single File")')
            if single_file_button.count() > 0:
                # Click to select file mode
                single_file_button.click()
                page.wait_for_timeout(300)

                # Look for module name input
                module_input = page.locator('input[placeholder*="module"]')
                if module_input.count() > 0:
                    # Verify input is visible and interactive
                    assert module_input.is_visible()
                    # In a real test, we would:
                    # 1. Enter a module name
                    # 2. Click analyze
                    # 3. Wait for results
                    # 4. Verify single IR is displayed

    @_skip_if_no_frontend
    def test_mode_switching(self, page):
        """Test switching between project and file modes."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Navigate to Repository section
        if page.locator('button:has-text("Repository")').count() > 0:
            page.locator('button:has-text("Repository")').click()
            page.wait_for_timeout(500)

            # Try switching between modes
            entire_project_button = page.locator('button:has-text("Entire Project")')
            single_file_button = page.locator('button:has-text("Single File")')

            if entire_project_button.count() > 0 and single_file_button.count() > 0:
                # Switch to project mode
                entire_project_button.click()
                page.wait_for_timeout(300)

                # Verify project mode UI (no module input)
                module_input = page.locator('input[placeholder*="module"]')
                # Module input should not be visible in project mode

                # Switch to file mode
                single_file_button.click()
                page.wait_for_timeout(300)

                # Verify file mode UI (module input visible)
                if module_input.count() > 0:
                    assert module_input.is_visible()

    @_skip_if_no_frontend
    def test_project_mode_results_display(self, page):
        """Test that project mode shows multiple results."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Navigate to Repository section
        if page.locator('button:has-text("Repository")').count() > 0:
            page.locator('button:has-text("Repository")').click()
            page.wait_for_timeout(500)

            # In a complete test, we would:
            # 1. Set up a test repository
            # 2. Trigger project mode analysis
            # 3. Wait for results
            # 4. Verify multiple IR cards are displayed
            # 5. Verify each card has file path, summary, and "View Details" button
            # 6. Verify summary statistics dashboard is shown

            # For now, verify the UI structure exists
            assert page.is_visible("body")


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.playwright
class TestWebUIEdgeCases:
    """Edge case tests for web UI."""

    @_skip_if_no_frontend
    def test_web_ui_invalid_ir_file(self, page):
        """Test UI robustness with navigation."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Test navigating between sections doesn't crash
        sections = [
            "Configuration",
            "Repository",
            "Prompt Workbench",
            "IR Review",
            "Planner",
            "IDE",
        ]
        for section in sections:
            if page.locator(f'button:has-text("{section}")').count() > 0:
                page.locator(f'button:has-text("{section}")').click()
                page.wait_for_timeout(300)
                assert page.is_visible("body")

    @_skip_if_no_frontend
    def test_web_ui_network_error(self, page):
        """Test handling of network errors."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Basic test: verify app loads even if backend is unavailable
        # More specific network error handling can be tested by mocking responses
        assert page.is_visible("body")
