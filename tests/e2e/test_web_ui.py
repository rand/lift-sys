"""Playwright-powered E2E tests for the web workflow."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

_ = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.e2e


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
                irPanel.textContent = 'ir sample_module {\n  intent: Demo\n  assert: - placeholder predicate\n  <?hole_id: Predicate?>\n}';
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
