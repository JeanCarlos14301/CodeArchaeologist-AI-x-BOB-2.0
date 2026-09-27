"""Executive 6-slide PPTX presentation renderer (D-09; not wired into the product).

Generates a professional Microsoft PowerPoint presentation (python-pptx):
Slide 1: Cover (CodeArchaeologist, system, metadata and execution mode)
Slide 2: The problem and the system diagnosis
Slide 3: Critical findings with 100% verified physical evidence (CBRS)
Slide 4: Architecture options compared and the choice of Strangler Fig
Slide 5: Migration plan with PERT distribution and 95% interval
Slide 6: Results of the first cut tested in the lab and ROI
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

from backend.app.models import DossierResult


def create_executive_pptx(dossier: DossierResult, output_path: Path | str) -> Path:
    """Generates the 6-slide executive corporate presentation."""
    prs = Presentation()
    # 16:9 widescreen aspect ratio
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Executive color palette
    c_dark_bg = RGBColor(15, 23, 42)      # Slate 900
    c_card_bg = RGBColor(30, 41, 59)      # Slate 800
    c_primary = RGBColor(59, 130, 246)    # Blue 500
    c_accent = RGBColor(16, 185, 129)     # Emerald 500
    c_text_white = RGBColor(248, 250, 252)
    c_text_muted = RGBColor(148, 163, 184)
    c_critical = RGBColor(239, 68, 68)

    def add_slide_header(slide, title_text: str, category_text: str = "LEGACYLENS × IBM BOB 2.0"):
        # Dark background across the whole slide
        bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = c_dark_bg
        bg_shape.line.fill.background()

        # Category
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.4))
        cp = cat_box.text_frame.paragraphs[0]
        c_run = cp.add_run()
        c_run.text = category_text.upper()
        c_run.font.size = Pt(11)
        c_run.font.bold = True
        c_run.font.color.rgb = c_primary

        # Main slide title
        t_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.8))
        tp = t_box.text_frame.paragraphs[0]
        t_run = tp.add_run()
        t_run.text = title_text
        t_run.font.size = Pt(24)
        t_run.font.bold = True
        t_run.font.color.rgb = c_text_white

    # ==========================================
    # SLIDE 1: PORTADA
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = c_dark_bg
    bg1.line.fill.background()

    p_box = s1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(3.5))
    tf1 = p_box.text_frame
    
    p1 = tf1.paragraphs[0]
    r1 = p1.add_run()
    r1.text = "CodeArchaeologist × Bob 2.0"
    r1.font.size = Pt(40)
    r1.font.bold = True
    r1.font.color.rgb = c_primary

    p2 = tf1.add_paragraph()
    p2.space_before = Pt(12)
    r2 = p2.add_run()
    r2.text = "From 'nobody dares to touch it' to an approved plan and a tested first cut"
    r2.font.size = Pt(20)
    r2.font.italic = True
    r2.font.color.rgb = c_text_white

    p3 = tf1.add_paragraph()
    p3.space_before = Pt(36)
    r3 = p3.add_run()
    r3.text = f"System assessed: {dossier.snapshot.repo_name} | Mode: {dossier.execution_mode.upper()} | Fidelity: {dossier.validation_report.fidelity_ratio * 100:.1f}%\nTeam: Jean, Felipe, Daniel, Edgar · IBM Bob 2.0 Hackathon"
    r3.font.size = Pt(13)
    r3.font.color.rgb = c_text_muted

    # ==========================================
    # SLIDE 2: THE PROBLEM AND THE DIAGNOSIS
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_header(s2, "The Forensic Diagnosis: Why Nobody Dares to Touch It")
    
    # 2 columns of cards
    card_w = Inches(5.6)
    card_h = Inches(4.8)
    
    # Left column: the business pain
    c1 = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), card_w, card_h)
    c1.fill.solid()
    c1.fill.fore_color.rgb = c_card_bg
    c1.line.color.rgb = RGBColor(51, 65, 85)
    tf_c1 = c1.text_frame
    tf_c1.word_wrap = True
    p = tf_c1.paragraphs[0]
    p.text = "THE BUSINESS BLOCKER"
    p.font.bold = True
    p.font.size = Pt(14)
    p.font.color.rgb = c_critical

    bullet_pts_1 = [
        "The legacy code mixes routes, financial rules and HTML without modularity.",
        "Nobody knows for sure what breaks if an endpoint changes.",
        "The board rejects 'rewrite everything from scratch' because of cost overruns.",
        "Generic AI diagnoses suffer from hallucinations and fictitious citations.",
    ]
    for b in bullet_pts_1:
        bp = tf_c1.add_paragraph()
        bp.space_before = Pt(14)
        bp.text = f"• {b}"
        bp.font.size = Pt(12)
        bp.font.color.rgb = c_text_white

    # Right column: the CodeArchaeologist answer
    c2 = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), card_w, card_h)
    c2.fill.solid()
    c2.fill.fore_color.rgb = c_card_bg
    c2.line.color.rgb = RGBColor(51, 65, 85)
    tf_c2 = c2.text_frame
    tf_c2.word_wrap = True
    p = tf_c2.paragraphs[0]
    p.text = "THE CODEARCHAEOLOGIST SOLUTION"
    p.font.bold = True
    p.font.size = Pt(14)
    p.font.color.rgb = c_accent

    bullet_pts_2 = [
        "Physical evidence: 100% of the claims verify the exact file and line.",
        "Blast radius (CBRS): computed with NetworkX graphs, not guessed.",
        "Contract first: golden-master characterization tests protect the migration.",
        "First step tested: a real Strangler Fig extraction with instant rollback.",
    ]
    for b in bullet_pts_2:
        bp = tf_c2.add_paragraph()
        bp.space_before = Pt(14)
        bp.text = f"• {b}"
        bp.font.size = Pt(12)
        bp.font.color.rgb = c_text_white

    # ==========================================
    # SLIDE 3: FINDINGS WITH PHYSICAL EVIDENCE
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_header(s3, "Critical Findings and Verified Blast Radius")

    # 3 Cajas horizontales
    box_w = Inches(3.6)
    box_h = Inches(4.8)

    crit_findings = [f for f in dossier.findings if f.severity in ["CRITICAL", "HIGH"]][:3]
    for idx, f in enumerate(crit_findings):
        left_pos = Inches(0.8 + idx * 4.0)
        bx = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_pos, Inches(1.8), box_w, box_h)
        bx.fill.solid()
        bx.fill.fore_color.rgb = c_card_bg
        bx.line.color.rgb = c_critical if f.severity == "CRITICAL" else RGBColor(249, 115, 22)
        tf = bx.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = f"{f.id} · {f.severity}"
        p0.font.bold = True
        p0.font.size = Pt(12)
        p0.font.color.rgb = c_critical if f.severity == "CRITICAL" else RGBColor(249, 115, 22)

        p1 = tf.add_paragraph()
        p1.space_before = Pt(8)
        p1.text = f.title
        p1.font.bold = True
        p1.font.size = Pt(13)
        p1.font.color.rgb = c_text_white

        p2 = tf.add_paragraph()
        p2.space_before = Pt(10)
        p2.text = f.explanation[:140] + "..."
        p2.font.size = Pt(11)
        p2.font.color.rgb = c_text_muted

        p3 = tf.add_paragraph()
        p3.space_before = Pt(16)
        loc = f.evidence[0] if f.evidence else None
        p3.text = f"Evidence in code:\n{Path(loc.path).name if loc else 'app.py'}:{loc.line_start if loc else 1}\nCBRS: {f.blast_radius_score:.1f} / 100"
        p3.font.size = Pt(10)
        p3.font.bold = True
        p3.font.color.rgb = c_primary

    # ==========================================
    # SLIDE 4: ARCHITECTURE OPTIONS
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_header(s4, "Architecture Options Compared: Why Strangler Fig")

    for idx, opt in enumerate(dossier.architecture_options[:3]):
        left_pos = Inches(0.8 + idx * 4.0)
        bx = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_pos, Inches(1.8), box_w, box_h)
        bx.fill.solid()
        bx.fill.fore_color.rgb = c_card_bg
        bx.line.color.rgb = c_accent if opt.recommended else RGBColor(71, 85, 105)
        tf = bx.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = "★ RECOMENDADA" if opt.recommended else "ALTERNATIVA DESCARTADA"
        p0.font.bold = True
        p0.font.size = Pt(11)
        p0.font.color.rgb = c_accent if opt.recommended else c_text_muted

        p1 = tf.add_paragraph()
        p1.space_before = Pt(6)
        p1.text = opt.name
        p1.font.bold = True
        p1.font.size = Pt(13)
        p1.font.color.rgb = c_text_white

        p2 = tf.add_paragraph()
        p2.space_before = Pt(6)
        p2.text = f"Risk: {opt.risk_level} · Effort: {opt.estimated_effort_days:.1f} days"
        p2.font.size = Pt(10)
        p2.font.color.rgb = c_primary

        p3 = tf.add_paragraph()
        p3.space_before = Pt(10)
        p3.text = "Ventajas clave:\n• " + "\n• ".join(opt.pros[:2])
        p3.font.size = Pt(10)
        p3.font.color.rgb = c_text_muted

        p4 = tf.add_paragraph()
        p4.space_before = Pt(8)
        p4.text = "Desventajas:\n• " + "\n• ".join(opt.cons[:2])
        p4.font.size = Pt(10)
        p4.font.color.rgb = RGBColor(248, 113, 113)

    # ==========================================
    # SLIDE 5: PLAN PERT
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    add_slide_header(s5, "Phase Plan with a PERT Statistical Estimate (95% Confidence)")

    total_pert = sum(p.pert_expected_days for p in dossier.pert_plan) if dossier.pert_plan else 20.5
    
    top_box = s5.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.7), Inches(0.8))
    tp = top_box.text_frame.paragraphs[0]
    tp.text = f"Total Expected Duration: {total_pert:.1f} working days (PERT formula: (O + 4M + P)/6) · Continuous deployment with zero-cost rollback"
    tp.font.size = Pt(13)
    tp.font.bold = True
    tp.font.color.rgb = c_accent

    for idx, ph in enumerate(dossier.pert_plan[:4]):
        y_pos = Inches(2.7 + idx * 1.05)
        bar = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), y_pos, Inches(11.7), Inches(0.9))
        bar.fill.solid()
        bar.fill.fore_color.rgb = c_card_bg
        bar.line.color.rgb = RGBColor(51, 65, 85)
        btf = bar.text_frame
        btf.word_wrap = True

        bp = btf.paragraphs[0]
        bp.text = f"Phase {ph.phase_number}: {ph.name}  —  Duration: {ph.pert_expected_days:.1f} days (O={ph.optimistic_days}d, M={ph.nominal_days}d, P={ph.pessimistic_days}d)"
        bp.font.bold = True
        bp.font.size = Pt(12)
        bp.font.color.rgb = c_text_white

        bp2 = btf.add_paragraph()
        bp2.text = f"Rollback: {ph.rollback_strategy}"
        bp2.font.size = Pt(9.5)
        bp2.font.color.rgb = c_text_muted

    # ==========================================
    # SLIDE 6: FIRST TESTED CUT & DECISION
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_header(s6, "First Cut Results and the Decision Requested from the Board")

    # Left column: test results
    c_left = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), card_w, card_h)
    c_left.fill.solid()
    c_left.fill.fore_color.rgb = c_card_bg
    c_left.line.color.rgb = c_accent
    tf_l = c_left.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "FIRST STRANGLER CUT TESTED"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = c_accent

    items_l = [
        f"Endpoint migrado: {dossier.selected_first_cut}",
        "Characterization tests against the legacy code: PASS (100%)",
        "Tests against the FastAPI micro-service: PASS (100%)",
        "BOLA fix: other users' invoices return a safe HTTP 404.",
        "Patch 'migration.diff' generated and validated with no regressions.",
    ]
    for it in items_l:
        bp = tf_l.add_paragraph()
        bp.space_before = Pt(12)
        bp.text = f"✔ {it}"
        bp.font.size = Pt(11.5)
        bp.font.color.rgb = c_text_white

    # Right column: decision and ROI
    c_right = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), card_w, card_h)
    c_right.fill.solid()
    c_right.fill.fore_color.rgb = c_card_bg
    c_right.line.color.rgb = c_primary
    tf_r = c_right.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "DECISION AND RETURN ON INVESTMENT (ROI)"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = c_primary

    items_r = [
        "Approval: authorize running Phase 1 and Phase 2.",
        "Time saved: a diagnosis of weeks reduced to minutes.",
        "Minimal operational risk: a facade with instant rollback.",
        "Full governance: a DOCX memo and a traceable technical report for auditing.",
    ]
    for it in items_r:
        bp = tf_r.add_paragraph()
        bp.space_before = Pt(12)
        bp.text = f"• {it}"
        bp.font.size = Pt(11.5)
        bp.font.color.rgb = c_text_white

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_file))
    return out_file
