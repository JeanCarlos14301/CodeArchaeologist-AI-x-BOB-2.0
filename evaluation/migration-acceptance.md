# Criterio de aceptación de la futura migración

La migración futura de `GET /invoices/{invoice_id}` debe conservar el contrato para el usuario propietario: `id`, `number`, `customer` con `id` y `name`, `date` ISO `YYYY-MM-DD`, `items` con `description`, `quantity`, `unit_price` y `line_total`, `subtotal`, `discount`, `total` y `status`. Los importes son cadenas con dos decimales.

La fórmula es: precio y línea a centavos, subtotal como suma de líneas, descuento de 7.5 % si subtotal ≥ 100.00, redondeado una sola vez con `ROUND_HALF_UP`, total igual a subtotal menos descuento. El ejemplo fijo `FY-00001` debe ser subtotal `100.07`, descuento `7.51`, total `92.56`.

Comportamiento base: 200 para factura existente con sesión, 401 sin sesión, 404 si no existe y 200 para factura ajena. **Corrección de seguridad intencional en la versión futura:** una factura ajena debe devolver 404. Las pruebas de compatibilidad no deben rechazar esa corrección; deben comprobar propietarios, estructura, importes, fecha y errores por separado.
