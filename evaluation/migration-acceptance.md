# Future Migration Acceptance Criteria

A future migration of the `GET /invoices/{invoice_id}` endpoint must preserve the contract for the invoice owner: `id`, `number`, `customer` with `id` and `name`, `date` in ISO `YYYY-MM-DD` format, `items` with `description`, `quantity`, `unit_price`, and `line_total`, plus `subtotal`, `discount`, `total`, and `status`. All monetary amounts must be strings formatted to two decimal places.

The calculation formula:
- Unit prices and line totals quantized to cents.
- Subtotal is the exact sum of line totals.
- A 7.5% discount applies if subtotal ≥ 100.00, rounded once to cents using `ROUND_HALF_UP`.
- Total equals subtotal minus discount.
- Anchor invoice `FY-00001` must evaluate to: subtotal `100.07`, discount `7.51`, total `92.56`.

Baseline legacy behavior: 200 OK for existing owned invoices with active session, 401 Unauthorized without session, 404 Not Found if invoice does not exist, and 200 OK when requesting another user's invoice (legacy BOLA vulnerability).

**Target security fix for modernized service:** Requests for foreign invoices must return 404 Not Found. Compatibility suites should not reject this intentional security remediation; they must verify ownership authorization, response schema, monetary precision, dates, and error status codes independently.
