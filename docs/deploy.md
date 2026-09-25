# Despliegue (J-02 / J-03)

Un solo contenedor (D11) construido desde el `Dockerfile` y desplegado en **Render**. Cada push a
`main` dispara el CI (`.github/workflows/ci.yml`); si pasa, Render reconstruye y publica la
misma URL (`render.yaml` → `autoDeployTrigger: checksPass`).

```
push a main ──► CI: pytest + build frontend + build y prueba de humo de la imagen
                    │ pasa
                    ▼
               Render reconstruye el Dockerfile ──► https://<servicio>.onrender.com
```

## Primera vez (≈10 min, lo hace Jean una sola vez)

1. Fusionar a `main` las ramas que ya estén aprobadas; Render despliega solo desde `main`.
2. Entrar a <https://dashboard.render.com> con la cuenta de GitHub que tenga acceso al repo.
3. **New → Blueprint**, elegir el repo. Render lee `render.yaml` y propone el servicio
   `codearchaeologist` (plan free, runtime Docker).
4. Cuando pida `BOB_API_KEY`, pegar la API key de Bob (scope *Inference*). Solo se guarda en
   Render, nunca en el repo (SECURITY.md).
5. **Apply**. El primer build tarda varios minutos (instala Python, Node 24 y Bob Shell).
6. En **Environment**, copiar el valor de `LIVE_AUDIT_TOKEN` (Render lo generó al azar) y
   compartirlo solo con el equipo y, si hace falta, con el jurado.
7. Recomendado: en GitHub → *Settings → Branches*, proteger `main` exigiendo los checks
   `backend`, `frontend` y `docker` del CI. Así nadie rompe la URL pública con un push directo.

## Verificar un despliegue

```bash
curl https://<servicio>.onrender.com/health          # {"status":"ok"}
curl https://<servicio>.onrender.com/api/bob/status  # installed, api_key_configured y live_requires_token en true
```

En la interfaz: **Ejemplo** e **Importado** funcionan para cualquiera. **Live** muestra un campo
de token y solo arranca con el `LIVE_AUDIT_TOKEN` correcto.

## Local, igual que en Render

```bash
docker compose up --build        # http://127.0.0.1:8000, lee .env si existe
```

Sin `LIVE_AUDIT_TOKEN` en `.env`, live queda abierto (como en desarrollo).

## Límites del plan free

- **Se duerme tras 15 min sin tráfico**: la primera visita tarda ~1 min. Abrir la URL un par
  de minutos antes de grabar el video o de que la pruebe el jurado.
- **512 MB de RAM**: Ejemplo e Importado van sobrados. Una auditoría **Live** lanza Bob Shell
  dentro del contenedor y **aún no está probada con ese límite**; si falla por memoria, las
  opciones son subir de plan en Render o grabar la parte live desde un PC (Plan B de D11/D12).
- **Disco efímero**: el historial de jobs (`artifacts/`) se borra en cada despliegue o reinicio.
  Para la demo no importa: Ejemplo e Importado siempre están disponibles.

## Si algo sale mal

- **Deshacer un despliegue**: Render → *Deploys* → *Rollback* sobre el último que funcionaba,
  o `git revert` del commit y push a `main`.
- **`A license agreement is required`**: falta `BOB_ACCEPT_LICENSE=true` en Environment.
- **`Falta BOB_API_KEY`**: la variable está vacía en Environment.
- **El build falla en el CI**: Render no despliega; la URL sigue sirviendo la versión anterior.
