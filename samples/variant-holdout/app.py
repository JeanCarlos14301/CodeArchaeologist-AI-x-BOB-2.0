from datetime import date
from decimal import Decimal

from flask import Flask, abort, jsonify, redirect, render_template_string, request, session, url_for
from markupsafe import escape

import config
from auth import authenticate, login_required
from billing import calculate, create_invoice
from customers import get_customer, invoice_count_for_customer, list_customers
from db import close_db, get_db, invoice_by_id, invoice_items
from reports import monthly_report
from utils import amount


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(config)
    if test_config:
        app.config.update(test_config)
    app.teardown_appcontext(close_db)

    @app.route("/")
    def index():
        if "user_id" not in session:
            return redirect(url_for("login"))
        return render_template_string("""<!doctype html><title>FacturaYa</title>
        <h1>FacturaYa</h1><nav><a href="/customers">Clientes</a> |
        <a href="/invoices">Facturas</a> | <a href="/invoices/new">Nueva factura</a> |
        <a href="/reports/monthly">Reporte mensual</a> |
        <form method="post" action="/logout"><button>Salir</button></form></nav>""")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template_string("""<!doctype html><title>Entrar</title>
            <h1>Entrar</h1><form method="post"><label>Usuario <input name="username" required></label>
            <label>Clave <input name="password" type="password" required></label>
            <button>Entrar</button></form>""")
        user = authenticate(get_db(), request.form.get("username", ""), request.form.get("password", ""))
        if user is None:
            return "Credenciales incorrectas", 401
        session.clear()
        session["user_id"] = user["id"]
        return redirect(url_for("index"))

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/customers")
    @login_required
    def customers_list():
        customers = list_customers(get_db(), session["user_id"])
        return render_template_string("""<!doctype html><title>Clientes</title><h1>Clientes</h1>
        <a href="/">Inicio</a><ul>{% for c in customers %}<li>
        <a href="{{ url_for('customer_detail', customer_id=c['id']) }}">{{ c['name'] }}</a>
        </li>{% endfor %}</ul>""", customers=customers)

    @app.get("/customers/<int:customer_id>")
    @login_required
    def customer_detail(customer_id):
        customer = get_customer(get_db(), customer_id, session["user_id"])
        if customer is None:
            abort(404)
        count = invoice_count_for_customer(get_db(), customer_id)
        return render_template_string("""<!doctype html><title>Cliente</title><h1>{{ c['name'] }}</h1>
        <p>{{ c['email'] }}</p><p>Facturas: {{ count }}</p><a href="/customers">Volver</a>""",
                                      c=customer, count=count)

    @app.get("/invoices")
    @login_required
    def invoices_list():
        search = request.args.get("q", "")
        connection = get_db()
        if search:
            sql = "SELECT id, number, issue_date, total FROM invoices WHERE owner_id = " + str(session["user_id"]) + " AND number LIKE '%" + search + "%' ORDER BY id DESC"
            rows = connection.execute(sql).fetchall()
        else:
            rows = connection.execute(
                "SELECT id, number, issue_date, total FROM invoices WHERE owner_id = ? ORDER BY id DESC",
                (session["user_id"],),
            ).fetchall()
        return render_template_string("""<!doctype html><title>Facturas</title><h1>Facturas</h1>
        <form><input name="q" value="{{ q }}"><button>Buscar</button></form>
        <a href="/invoices/new">Nueva</a><ul>{% for i in rows %}<li>
        <a href="{{ url_for('invoice_html', invoice_id=i['id']) }}">{{ i['number'] }}</a>
        {{ i['issue_date'] }} — {{ i['total'] }}</li>{% endfor %}</ul>""", rows=rows, q=search)

    @app.get("/invoices/<int:invoice_id>")
    @login_required
    def invoice_json(invoice_id):
        invoice = invoice_by_id(get_db(), invoice_id)
        if invoice is None:
            abort(404)
        items = invoice_items(get_db(), invoice_id)
        return jsonify({
            "id": invoice["id"], "number": invoice["number"],
            "customer": {"id": invoice["customer_id"], "name": invoice["customer_name"]},
            "date": invoice["issue_date"],
            "items": [{"description": item["description"], "quantity": item["quantity"],
                       "unit_price": amount(item["unit_price"]), "line_total": amount(item["line_total"])}
                      for item in items],
            "subtotal": amount(invoice["subtotal"]), "discount": amount(invoice["discount"]),
            "total": amount(invoice["total"]), "status": invoice["status"],
        })

    @app.get("/invoices/<int:invoice_id>/view")
    @login_required
    def invoice_html(invoice_id):
        invoice = invoice_by_id(get_db(), invoice_id)
        if invoice is None or invoice["owner_id"] != session["user_id"]:
            abort(404)
        items = invoice_items(get_db(), invoice_id)
        return render_template_string("""<!doctype html><title>Factura</title>
        <h1>{{ i['number'] }}</h1><p>Cliente: {{ i['customer_name'] }}</p>
        <p>Fecha: {{ i['issue_date'] }} | Estado: {{ i['status'] }}</p>
        <table><tr><th>Descripción</th><th>Cantidad</th><th>Precio</th><th>Total</th></tr>
        {% for item in items %}<tr><td>{{ item['description'] }}</td><td>{{ item['quantity'] }}</td>
        <td>{{ item['unit_price'] }}</td><td>{{ item['line_total'] }}</td></tr>{% endfor %}</table>
        <p>Subtotal: {{ i['subtotal'] }} | Descuento: {{ i['discount'] }} | Total: {{ i['total'] }}</p>
        <a href="/invoices">Volver</a>""", i=invoice, items=items)

    @app.route("/invoices/new", methods=["GET", "POST"])
    @login_required
    def invoice_new():
        connection = get_db()
        owner_id = session["user_id"]
        customers = list_customers(connection, owner_id)
        errors = []
        selected_customer = ""
        selected_date = date.today().isoformat()
        selected_status = "pending"
        submitted_rows = []
        preview = None
        customer_name = None
        item_count = 0
        if request.method == "POST":
            selected_customer = request.form.get("customer_id", "").strip()
            selected_date = request.form.get("issue_date", "").strip()
            selected_status = request.form.get("status", "").strip()
            raw_descriptions = request.form.getlist("description")
            raw_quantities = request.form.getlist("quantity")
            raw_prices = request.form.getlist("unit_price")
            if not selected_customer.isdigit():
                errors.append("Seleccione un cliente válido.")
            else:
                customer = get_customer(connection, int(selected_customer), owner_id)
                if customer is None:
                    errors.append("El cliente no está disponible.")
                else:
                    customer_name = customer["name"]
            try:
                parsed_date = date.fromisoformat(selected_date)
                if parsed_date.isoformat() != selected_date:
                    errors.append("La fecha debe tener formato AAAA-MM-DD.")
                if parsed_date.year < 2000 or parsed_date.year > 2100:
                    errors.append("La fecha está fuera del período permitido.")
            except ValueError:
                errors.append("La fecha debe tener formato AAAA-MM-DD.")
            if selected_status not in {"pending", "paid"}:
                errors.append("El estado no es válido.")
            if not raw_descriptions:
                errors.append("Agregue al menos un ítem.")
            if len(raw_descriptions) != len(raw_quantities):
                errors.append("Faltan cantidades.")
            if len(raw_descriptions) != len(raw_prices):
                errors.append("Faltan precios.")
            if len(raw_descriptions) > 20:
                errors.append("Máximo 20 ítems.")
            if len(raw_descriptions) == len(raw_quantities) == len(raw_prices):
                item_count = len(raw_descriptions)
            if not errors:
                for index, raw_description in enumerate(raw_descriptions):
                    description = raw_description.strip()
                    quantity_text = raw_quantities[index].strip()
                    price_text = raw_prices[index].strip()
                    if not description:
                        errors.append(f"Ítem {index + 1}: falta descripción.")
                    if len(description) > 120:
                        errors.append(f"Ítem {index + 1}: descripción demasiado larga.")
                    if not quantity_text.isdigit():
                        errors.append(f"Ítem {index + 1}: cantidad inválida.")
                    else:
                        quantity = int(quantity_text)
                        if quantity < 1 or quantity > 10000:
                            errors.append(f"Ítem {index + 1}: cantidad fuera de rango.")
                    try:
                        price = Decimal(price_text)
                        if not price.is_finite() or price < 0 or price > 1000000:
                            errors.append(f"Ítem {index + 1}: precio fuera de rango.")
                        if price.as_tuple().exponent < -2:
                            errors.append(f"Ítem {index + 1}: máximo dos decimales.")
                        if len(price_text) > 16:
                            errors.append(f"Ítem {index + 1}: precio demasiado largo.")
                    except Exception:
                        errors.append(f"Ítem {index + 1}: precio inválido.")
                    submitted_rows.append({
                        "description": description,
                        "quantity": quantity_text,
                        "unit_price": price_text,
                    })
            if not errors:
                try:
                    normalized, subtotal, discount, total = calculate(submitted_rows)
                    preview = {"items": normalized, "subtotal": subtotal,
                               "discount": discount, "total": total}
                except (ValueError, KeyError, OverflowError):
                    errors.append("No se pudo calcular la factura.")
            if not errors:
                try:
                    invoice_id = create_invoice(
                        connection, owner_id, int(selected_customer), selected_date,
                        selected_status, submitted_rows,
                    )
                    return redirect(url_for("invoice_html", invoice_id=invoice_id))
                except ValueError:
                    errors.append("No se pudo guardar la factura.")
        if not submitted_rows:
            submitted_rows = [
                {"description": "", "quantity": "1", "unit_price": "0.00"},
                {"description": "", "quantity": "1", "unit_price": "0.00"},
            ]
        parts = ["<!doctype html><html lang='es'><meta charset='utf-8'><title>Nueva factura</title>"]
        parts.append("<h1>Nueva factura</h1><a href='/invoices'>Volver a facturas</a>")
        parts.append("<p>Complete el cliente, la fecha y al menos un ítem.</p>")
        parts.append("<p>Los precios aceptan hasta dos decimales.</p>")
        parts.append("<p>Las facturas pueden quedar pendientes o pagadas.</p>")
        if customer_name:
            parts.append("<p>Cliente seleccionado: " + str(escape(customer_name)) + "</p>")
        if request.method == "POST":
            parts.append("<p>Ítems enviados: " + str(item_count) + "</p>")
        for error in errors:
            parts.append("<p role='alert'>" + str(escape(error)) + "</p>")
        if errors:
            parts.append("<p>Corrija los campos y vuelva a enviar el formulario.</p>")
        parts.append("<form method='post'>")
        parts.append("<fieldset><legend>Datos de la factura</legend>")
        parts.append("<label>Cliente <select name='customer_id' required>")
        parts.append("<option value=''>Seleccione</option>")
        for customer in customers:
            cid = str(customer["id"])
            name = str(escape(customer["name"]))
            selected = " selected" if cid == selected_customer else ""
            parts.append("<option value='" + cid + "'" + selected + ">" + name + "</option>")
        parts.append("</select></label>")
        parts.append("<label>Fecha <input type='date' name='issue_date' value='" + str(escape(selected_date)) + "' required></label>")
        parts.append("<small>La fecha se guarda en formato AAAA-MM-DD.</small>")
        parts.append("<label>Estado <select name='status'>")
        for status, label in (("pending", "Pendiente"), ("paid", "Pagada")):
            selected = " selected" if selected_status == status else ""
            parts.append("<option value='" + status + "'" + selected + ">" + label + "</option>")
        parts.append("</select></label></fieldset>")
        parts.append("<fieldset><legend>Ítems</legend>")
        parts.append("<p>Puede añadir hasta 20 ítems en una solicitud.</p>")
        for index, row in enumerate(submitted_rows):
            parts.append("<div><strong>Ítem " + str(index + 1) + "</strong>")
            parts.append("<label>Descripción <input name='description' value='" + str(escape(row["description"])) + "' required></label>")
            parts.append("<label>Cantidad <input type='number' name='quantity' min='1' value='" + str(escape(row["quantity"])) + "' required></label>")
            parts.append("<label>Precio <input name='unit_price' value='" + str(escape(row["unit_price"])) + "' required></label>")
            parts.append("<small>El precio corresponde a una unidad.</small>")
            parts.append("</div>")
        parts.append("</fieldset>")
        parts.append("<button type='submit'>Crear factura</button></form>")
        if preview:
            parts.append("<section><h2>Cálculo</h2>")
            parts.append("<table><thead><tr><th>Descripción</th><th>Cantidad</th>")
            parts.append("<th>Precio</th><th>Importe</th></tr></thead><tbody>")
            for item in preview["items"]:
                parts.append("<tr><td>" + str(escape(item["description"])) + "</td>")
                parts.append("<td>" + str(item["quantity"]) + "</td>")
                parts.append("<td>" + item["unit_price"] + "</td>")
                parts.append("<td>" + item["line_total"] + "</td></tr>")
            parts.append("</tbody></table>")
            parts.append("<p>Subtotal " + preview["subtotal"] + "</p>")
            parts.append("<p>Descuento " + preview["discount"] + "</p>")
            parts.append("<p>Total " + preview["total"] + "</p></section>")
        parts.append("<footer><a href='/'>Inicio</a></footer>")
        parts.append("</html>")
        return "\n".join(parts), 400 if errors else 200

    @app.get("/reports/monthly")
    @login_required
    def report_monthly():
        month = request.args.get("month", "2024-01")
        try:
            date.fromisoformat(month + "-01")
        except ValueError:
            abort(400)
        rows = monthly_report(get_db(), session["user_id"], month)
        return render_template_string("""<!doctype html><title>Reporte</title><h1>Reporte {{ month }}</h1>
        <form><input type="month" name="month" value="{{ month }}"><button>Consultar</button></form>
        <table><tr><th>Factura</th><th>Total en reporte</th></tr>
        {% for row in rows %}<tr><td>{{ row['number'] }}</td><td>{{ row['report_total'] }}</td></tr>
        {% endfor %}</table>""", month=month, rows=rows)

    return app


app = create_app()
