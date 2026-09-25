# FacturaYa v1

Aplicación de facturación de muestra para evaluación local. Requiere Python 3.11, Flask y SQLite.

Desde este directorio:

```powershell
python -m pip install -r requirements.txt
python seed.py facturaya.sqlite3
python -m flask --app app run --host 127.0.0.1
```

Abra http://127.0.0.1:5000/login. Las cuentas sintéticas figuran en el README del repositorio.

Aviso: aplicación deliberadamente vulnerable para evaluación local con datos sintéticos. No la exponga a Internet.
