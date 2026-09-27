# FacturaYa v1

Sample legacy billing application for local evaluation. Requires Python 3.11+, Flask, and SQLite.

From this directory:

```powershell
python -m pip install -r requirements.txt
python seed.py facturaya.sqlite3
python -m flask --app app run --host 127.0.0.1
```

Navigate to http://127.0.0.1:5000/login in your browser. Synthetic demo credentials are listed in the repository root README.

Notice: Deliberately vulnerable application designed for local evaluation with synthetic data. Do not expose this service to untrusted networks or the public Internet.
