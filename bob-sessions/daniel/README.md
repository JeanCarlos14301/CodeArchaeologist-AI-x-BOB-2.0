# Capturas de Daniel

- `2026-09-26_blast-radius-guard01.png`, `2026-09-26_blast-radius-guard02.png`: ejecución headless de `bob run --mode blast-radius-guard` desde la terminal del Bob IDE. Muestra la invocación del comando, la activación del skill `blast-radius-simulation`, la inspección de dependencias sobre `samples/facturaya-v1/db.py` (`auth.py`, `customers.py`, `reports.py`, `utils.py`), y el bloque **Task Summary** con costo real (0,068 bobcoins, 8,3 s, tarea `4a259689353baa35cef59f5765c01578`).
- `test1.png`, `test2.png`: ejecuciones de la suite de pruebas del backend (`pytest backend/tests`) en VS Code.
- `test3.png`: la batería de pruebas de seguridad contra la API local (`backend/tests/dast_runner.py`, 25/25).
