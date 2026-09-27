# Daniel's screenshots

- `2026-09-26_blast-radius-guard01.png` and `2026-09-26_blast-radius-guard02.png`: headless `bob run --mode blast-radius-guard` from the Bob IDE terminal. They show the command, activation of the `blast-radius-simulation` skill, dependency inspection around `samples/facturaya-v1/db.py` (`auth.py`, `customers.py`, `reports.py`, and `utils.py`), and a **Task Summary** with real cost (0.068 bobcoins), duration (8.3 s), and task ID `4a259689353baa35cef59f5765c01578`. This run reached its three-turn limit with zero assistant messages, so it should be replaced with a completed run that includes Bob's answer.
- `test1.png` and `test2.png`: runs of the backend test suite (`pytest backend/tests`) in VS Code.
- `test3.png`: the security test suite against the local API (`backend/tests/dast_runner.py`, 25/25).
