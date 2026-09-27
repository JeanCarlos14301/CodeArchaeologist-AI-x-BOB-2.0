"""Tests for the DOCX, HTML and PPTX artifact renderers (D-05, D-08, D-09)."""

import json
from pathlib import Path
from docx import Document
from pptx import Presentation
import pytest

from backend.app.models import DossierResult
from backend.app.renderers.docx_renderer import render_dossier_to_docx
from backend.app.renderers.html_renderer import render_dossier_to_html
from backend.app.renderers.pptx_renderer import create_executive_pptx

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def sample_dossier() -> DossierResult:
    fixture_path = BASE_DIR / "contracts" / "fixtures" / "valid-dossier.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    return DossierResult.model_validate(data)


def test_docx_renderer_produces_valid_word_document(sample_dossier: DossierResult, tmp_path: Path):
    """Checks that the DOCX renderer produces a 7-section document that opens cleanly in Word."""
    out_docx = tmp_path / "board_memo_test.docx"
    render_dossier_to_docx(sample_dossier, out_docx)

    assert out_docx.exists()
    assert out_docx.stat().st_size > 5000

    # Open with python-docx to check it is not corrupt
    doc = Document(str(out_docx))
    assert len(doc.paragraphs) > 10
    assert len(doc.tables) >= 4  # Findings, Options, PERT, etc.

    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Executive Summary and Decision Requested" in full_text
    assert "System Diagnosis and Verified Physical Evidence" in full_text
    assert "Risk Assessment and Blast Radius" in full_text
    assert "Architecture Options Compared" in full_text
    assert "Migration Phase Plan with PERT Distribution" in full_text
    assert "Results of the First Cut Tested" in full_text
    assert "Roadmap for the Next 30 Days" in full_text


def test_html_renderer_produces_interactive_report(sample_dossier: DossierResult, tmp_path: Path):
    """Checks that the HTML renderer produces a standalone file with Mermaid diagrams."""
    out_html = tmp_path / "report_test.html"
    render_dossier_to_html(sample_dossier, out_html)

    assert out_html.exists()
    content = out_html.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "CodeArchaeologist" in content
    assert "erDiagram" in content or "mermaid" in content
    assert "Evidence Fidelity" in content
    assert "EF-1" in content


def test_pptx_renderer_produces_6_slides_presentation(sample_dossier: DossierResult, tmp_path: Path):
    """Checks that the PPTX renderer produces an executive presentation of exactly 6 slides."""
    out_pptx = tmp_path / "presentation_test.pptx"
    create_executive_pptx(sample_dossier, out_pptx)

    assert out_pptx.exists()
    assert out_pptx.stat().st_size > 10000

    # Open with python-pptx
    prs = Presentation(str(out_pptx))
    assert len(prs.slides) == 6, f"Esperadas 6 diapositivas, generadas {len(prs.slides)}"
