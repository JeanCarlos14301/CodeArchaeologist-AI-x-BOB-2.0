# Historical task plan

Format: `ID | Owner | Window | Task | Acceptance`. Hours H0–H48 start at kickoff. The historical
`create_issues.sh` script reads this table; update the script if the format changes.

Milestones use the end of each window: `milestone:H3`, `milestone:H8`, `milestone:H24`, `milestone:H32`,
`milestone:H44`, and `milestone:continuous`.

| ID | Owner | Window | Task | Acceptance |
|---|---|---|---|---|
| J-01 | Jean | H0–H1 | Resolve kickoff questions | Answers in `decisions.md` |
| J-02 | Jean | H0–H3 | Deploy Dockerfile + FastAPI `/health` | Public URL responds |
| J-03 | Jean | H3–H8 | Automatic deployment from `main` | Push updates the URL |
| J-04 | Jean | H4–H10 | Two sourced market figures + business slides | Source links |
| J-05 | Jean | H8–H12 | Test the judge journey | Prioritized issues |
| J-06 | Jean | H12–H20 | Video script | Timed script |
| J-07 | Jean | H20–H24 | Manual measurement against tool | Figure with method |
| J-08 | Jean | H24–H30 | Acceptance and v1.0 tag | Journey passes three times |
| J-09 | Jean | H32–H38 | Record and edit video | ≤ 3 minutes, ≥ 90 s live demo |
| J-10 | Jean | H36–H44 | Final README and submission | Verified from another account |
| J-11 | Jean | continuous | Bob session-summary screenshot from own account | Image in `bob-sessions/jean/` |
| F-01 | Felipe | H0–H2 | Bob Shell + sanitized real JSON | File in `contracts/` |
| F-02 | Felipe | H1–H3 | `AGENTS.md` and five working modes | `bob run --mode` responds |
| F-03 | Felipe | H3–H8 | `evidence-auditor` returns schema v1 | Passes Pydantic |
| F-04 | Felipe | H8–H14 | `migration-architect`: three options and first cut | Justified |
| F-05 | Felipe | H12–H18 | `contract-keeper`: characterization tests | Pass on legacy |
| F-06 | Felipe | H16–H24 | `strangler-surgeon`: FastAPI + facade | Tests green |
| F-07 | Felipe | H18–H24 | Precision and recall against expected findings | Table in `evaluation/` |
| F-08 | Felipe | H24–H30 | `board-narrator` + holdout test | **Canceled:** the variant was a copy; active DOCX uses data-only narrative |
| F-09 | Felipe | continuous | `bob-usage.md` and exported report | File in report directory |
| F-10 | Felipe | H4–H10 | Polyglot migration modes and FastAPI→NestJS/Express skill | Catalog and matrices complete |
| F-11 | Felipe | H8–H16 | Shift-left blast-radius simulator and pre-PR gate | **Design only; not shipped** |
| F-12 | Felipe | H12–H20 | Adversarial tribunal: architect vs skeptic | Four-round protocol with verdict |
| F-13 | Felipe | H16–H24 | AST Cartographer + PyDriller Git archaeology | Call and Mermaid ER graphs |
| F-14 | Felipe | H20–H28 | FastMCP telemetry: DuckDB / GitHub connectors | Operational enrichment active |
| F-15 | Felipe | continuous | Bob session-summary screenshot from own account | Image in `bob-sessions/felipe/` |
| D-01 | Daniel | H0–H3 | Pydantic models + schema v1 + two fixtures | **Completed:** generated and validated in backend and contracts |
| D-02 | Daniel | H2–H6 | Job API, SQLite, worker, events | **Deprecated and removed:** replaced by unified `/api/audits` pipeline |
| D-03 | Daniel | H3–H6 | Secure ZIP ingestion + extractors | **Completed:** anti-ZipSlip, 5MB/20MB/300-file limits, AST/Radon/SQL extraction |
| D-04 | Daniel | H5–H8 | BobAdapter with timeout and modes | **Completed:** safe `subprocess`, `shell=False`, live/imported/example |
| D-05 | Daniel | H6–H8 | Minimal DOCX | **Completed:** downloadable executive rendering |
| D-06 | Daniel | H8–H16 | Validator, blast radius, risk, PERT | **Completed:** deterministic ranking and wave PERT |
| D-07 | Daniel | H12–H22 | Pytest sandbox + migration endpoint | **Completed:** ten ranked candidates, three waves, migration endpoint |
| D-08 | Daniel | H16–H24 | Complete DOCX + standalone HTML | **Completed:** seven-section Word document + interactive Mermaid HTML |
| D-09 | Daniel | H24–H30 | PPTX, diff download, failure handling | **Completed:** six-slide 16:9 PPTX + downloadable diff |
| D-10 | Daniel | continuous | Audit CLI, tests, Bob session | **Completed:** test, SAST, DAST, and live Bob checks recorded at the time |
| E-01 | Edgar | H0–H3 | Vite + React + Tailwind | Build served by FastAPI |
| E-02 | Edgar | H3–H8 | Input and timeline with fixture | Complete journey |
| E-03 | Edgar | H6–H8 | Connect real API | Visible tracer bullet |
| E-04 | Edgar | H8–H16 | Findings and evidence viewer | Every finding opens its file |
| E-05 | Edgar | H12–H20 | Current vs target architecture | Observed vs inferred |
| E-06 | Edgar | H16–H24 | Split view + test panel | Real data |
| E-07 | Edgar | H20–H28 | Downloads, visible mode, errors | No blank screens |
| E-08 | Edgar | H26–H32 | Polish and screenshots | Value is clear in 30 seconds |
| E-09 | Edgar | continuous | Bob session-summary screenshot from own account | Image in `bob-sessions/edgar/` |
