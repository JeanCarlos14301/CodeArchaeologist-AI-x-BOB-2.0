Síntesis de hallazgos (estado a las 20:00, H10)
Lo que ya está bien:

Datos falsos: no queda ninguno en la interfaz.
Subida de ZIP: real y segura, con token.
Arquitectura y radio de impacto: medidos con código.
Codificación: las tildes ya salen bien.
Pruebas: pasan 126.
Críticos (bloquean la entrega):

Privacidad: cualquiera puede listar los trabajos subidos y leer su código, su grafo y su expediente sin token.
Sin token no se ve nada: no hay vitrina importada ni demo de FacturaYa en un clic, y cada demo gasta bobcoins.
Faltan las entregas 2 y 3: el DOCX para la junta y el primer corte probado no están en el producto, y el README los promete.
Afirmaciones falsas en el repo: el README anuncia los 4 pilares y CBRS; bob-usage.md cita db_pool.py y legacy_db.py, que no existen.
Capturas de sesión de Bob: 0 de 4 en main.
Importantes:
6. PERT: se eliminó, pero el memo necesita rangos de esfuerzo.
7. Holdout: variant-holdout es una copia idéntica de FacturaYa.
8. Deuda técnica: /api/jobs sigue en el código aunque esté apagado, un test falla de forma intermitente por tiempo, requirements.txt quedó sin versiones fijas y la rama develop sigue existiendo.
9. Decisiones del plan: no están registradas. Hay que numerarlas desde D22, porque D13–D21 ya existen.
10. Render: no está verificado, y el modo live no se ha probado con 512 MB.

Plan único de solución
Bloque 0 · Seguridad y acceso público (ahora → 21:30)
S1. Cerrar la fuga de privacidad

GET /api/audits lista solo las muestras registradas. Los trabajos subidos aparecen únicamente si la petición trae un X-Live-Token válido.
GET /api/audits/{id}, /source, /graph, /architecture y /files/{name} exigen el token cuando el trabajo es una subida.
El frontend envía el token en esas lecturas y oculta del historial las subidas cuando no hay token.
Listo cuando: hay pruebas que verifican 403 sin token y 200 con token en cada una de esas rutas.
S2. Vitrina pública honesta

El modo imported vuelve a funcionar solo para las muestras registradas (FacturaYa) y sin token. Reproduce la corrida real del 25/09 a las 15:22 (job 02833a24a7a7, 12/13 validados).
Va marcado como "importado" y con su fecha original.
En la interfaz, dos botones: "Ver auditoría real de FacturaYa" (público) y "Auditar en vivo" (con token, para FacturaYa o un ZIP).
Listo cuando: un visitante sin token recorre el expediente, el mapa y la arquitectura de FacturaYa sin gastar bobcoins.
S3. Higiene del repo

Commitear la captura de Jean.
Registrar las decisiones como D22–D27 en docs/decisions.md.
Borrar la rama develop y las ramas viejas.
Bloque 1 · Recuperar las entregas 2 y 3 (21:30 → 02:00)
E2a. Riesgo y esfuerzo calculados desde hechos

Matriz de riesgo por hallazgo validado: severidad × radio de impacto, tomando los llamadores que ya calcula el grafo.
PERT del primer corte con una fórmula escrita, en función de las rutas, funciones, líneas y complejidad afectadas. Cada cifra lleva su texto de supuestos.
Listo cuando: dos repos distintos dan cifras distintas y cada cifra muestra de dónde sale.
E2b. Memo de Bob verificado por código (modo board-narrator)

Todo número del memo debe existir en el JSON de entrada. Si no, se rechaza y se reintenta una vez.
Si vuelve a fallar, el memo sale solo con datos, sin narrativa de Bob, y marcado como tal.
Listo cuando: una prueba demuestra que un memo con una cifra inventada se rechaza.
E2c. DOCX desde la auditoría real

El renderizador existente recibe el expediente real (hallazgos, riesgo, PERT y memo) a través de un mapeo.
Se agrega board_memo.docx a las descargas de /api/audits/{id}/files/.
Sin "LegacyLens", sin CBRS y sin cifras sin fuente.
Listo cuando: el DOCX de una auditoría real abre en Word con el mismo id de trabajo, hash y modo que la web.
E3a. Primer corte probado de verdad (solo muestras registradas)

Nueva etapa en AuditService:
Copiar el código a un sandbox.
Aplicar la implementación de referencia (modern/invoices_api.py y facade.py).
Correr la suite de caracterización (test_invoice_contract.py y las pertinentes) contra el legado y contra el código moderno, sin credenciales.
El resultado se reporta por prueba: pasó, falló o no ejecutada. En las subidas de usuarios se reporta "no ejecutada" con el motivo.
El .diff se puede descargar.
Listo cuando: al romper una línea del código moderno, la etapa muestra una prueba fallida.
E3b. Vista de Migración mínima

Código legado y moderno lado a lado, más el panel de pruebas reales.
Etiqueta visible: "implementación de referencia del equipo; no generada por Bob".
Listo cuando: la vista refleja el resultado real de E3a, incluida una falla.
🚪 Puerta 02:00 (H16): S1 y S2 listos, y el DOCX se descarga desde una auditoría real (aunque el memo todavía sea solo datos).

Bloque 2 · Veracidad y estabilidad (sábado 06:00 → 12:00)
C1. README veraz

Quitar los 4 pilares y CBRS.
Describir las 3 entregas tal como existen en el producto.
Probar el Quick start desde un clon limpio.
C2. Log de Bob respaldado

Las entradas de bob-usage.md se respaldan con su bob-result.json o una captura, o se marcan "diseño, no ejecutado".
evaluation/score.py debe reproducir el 5/6 de la corrida live.
C3. Holdout: real o fuera

Hacerlo real con 2 o 3 cambios que solo conozca una persona, o quitarlo del README, la interfaz y el repo.
C4. Retirar /api/jobs

Borrar sus routers, el worker y run_bob_command, conservando los módulos que se reutilizan.
Eliminar o corregir el test inestable y volver a fijar las versiones de requirements.txt.
C5. Render

Verificar la URL y hacer una auditoría live con token en el plan de 512 MB.
Si se queda sin memoria: pagar el plan superior o grabar la parte live del video en local.
BOB_API_KEY y LIVE_AUDIT_TOKEN viven solo en Render, nunca en el repo.
C6. Estados de la interfaz

Mensajes claros para 403, 409, fallo de Bob y una corrida live de 2–3 minutos con progreso visible.
Revisión en ancho de teléfono y en modo oscuro.
Mermaid con carga diferida, si todavía no la tiene.
C7. Capturas de sesión de Bob: 4 de 4 en main, de sesiones con trabajo real y sin credenciales visibles.

🚪 Puerta 10:00 (H24): primer corte con pytest real visible, DOCX con memo verificado y README veraz.

Bloque 3 · Congelamiento (12:00 → 16:00)
Prueba de aceptación: el recorrido completo pasa 3 veces seguidas en la URL pública.
Tag v1.0 a las 16:00 (H30). Desde ahí, lo que esté roto se quita, no se arregla.
Bloque 4 · Entrega (sábado 18:00 → domingo 06:00)
Video: MP4 de máximo 3:00, con al menos 90 segundos del producto en vivo. Recorrido: vitrina o live → etapas → hallazgo con evidencia → mapa y radio de impacto → primer corte con pruebas → DOCX.
Textos del formulario: Long Description e IBM Bob Usage Statement, de máximo 500 palabras cada uno, y solo con afirmaciones respaldadas.
Envío: antes del domingo 06:00, verificado desde otra cuenta.
Si falta tiempo, se recorta en este orden
Holdout.
Narrativa de Bob en el memo (queda el memo solo con datos, marcado como tal).
Mejoras de estados de la interfaz.
No se recorta nunca: la privacidad (S1), la vitrina pública (S2), el DOCX real, el primer corte con pytest real y el README veraz.

Opcional, solo si todo lo anterior está listo antes de las 12:00: las 3 opciones de arquitectura con Bob, que Bob escriba las pruebas y la migración, e importar desde una URL de GitHub.