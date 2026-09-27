"""Deterministic pipeline orchestrator (D6).

Stages of an audit (`evidence_audit.run_evidence_audit`):
   1. Safe ingestion and inventory (Python; uploaded code never runs).
   2. evidence-auditor (Bob, read-only; delegates modules to read-only subagents).
   3. Evidence validator (Python): each cited file, line range and snippet is checked against the code.
   4. Risk, blast radius and route ranking (Python), plus migration-architect (Bob, live audits only).
   5. First reference cut with characterization tests (registered samples only) and PERT effort.
   6. Renderers: dossier JSON and the board memo (DOCX).

Every result carries execution_mode: live, imported or example (D8).
"""
