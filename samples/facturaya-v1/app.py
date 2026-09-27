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
        <h1>FacturaYa</h1><nav><a href="/customers">Customers</a> |
        <a href="/invoices">Invoices</a> | <a href="/invoices/new">New invoice</a> |
        <a href="/reports/monthly">Monthly report</a> |
        <form method="post" action="/logout"><button>Log out</button></form></nav>""")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template_string("""<!doctype html><title>Login</title>
            <h1>Login</h1><form method="post"><label>Username <input name="username" required></label>
            <label>Password <input name="password" type="password" required></label>
            <button>Log in</button></form>""")
        user = authenticate(get_db(), request.form.get("username", ""), request.form.get("password", ""))
        if user is None:
            return "Invalid credentials", 401
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
        return render_template_string("""<!doctype html><title>Customers</title><h1>Customers</h1>
        <a href="/">Home</a><ul>{% for c in customers %}<li>
        <a href="{{ url_for('customer_detail', customer_id=c['id']) }}">{{ c['name'] }}</a>
        </li>{% endfor %}</ul>""", customers=customers)

    @app.get("/customers/<int:customer_id>")
    @login_required
    def customer_detail(customer_id):
        customer = get_customer(get_db(), customer_id, session["user_id"])
        if customer is None:
            abort(404)
        count = invoice_count_for_customer(get_db(), customer_id)
        return render_template_string("""<!doctype html><title>Customer</title><h1>{{ c['name'] }}</h1>
        <p>{{ c['email'] }}</p><p>Invoices: {{ count }}</p><a href="/customers">Back</a>""",
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
        return render_template_string("""<!doctype html><title>Invoices</title><h1>Invoices</h1>
        <form><input name="q" value="{{ q }}"><button>Search</button></form>
        <a href="/invoices/new">New</a><ul>{% for i in rows %}<li>
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
        return render_template_string("""<!doctype html><title>Invoice</title>
        <h1>{{ i['number'] }}</h1><p>Customer: {{ i['customer_name'] }}</p>
        <p>Date: {{ i['issue_date'] }} | Status: {{ i['status'] }}</p>
        <table><tr><th>Description</th><th>Quantity</th><th>Unit Price</th><th>Total</th></tr>
        {% for item in items %}<tr><td>{{ item['description'] }}</td><td>{{ item['quantity'] }}</td>
        <td>{{ item['unit_price'] }}</td><td>{{ item['line_total'] }}</td></tr>{% endfor %}</table>
        <p>Subtotal: {{ i['subtotal'] }} | Discount: {{ i['discount'] }} | Total: {{ i['total'] }}</p>
        <a href="/invoices">Back</a>""", i=invoice, items=items)

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
                errors.append("Select a valid customer.")
            else:
                customer = get_customer(connection, int(selected_customer), owner_id)
                if customer is None:
                    errors.append("Customer is unavailable.")
                else:
                    customer_name = customer["name"]
            try:
                parsed_date = date.fromisoformat(selected_date)
                if parsed_date.isoformat() != selected_date:
                    errors.append("Date must be in YYYY-MM-DD format.")
                if parsed_date.year < 2000 or parsed_date.year > 2100:
                    errors.append("Date is outside the allowed range.")
            except ValueError:
                errors.append("Date must be in YYYY-MM-DD format.")
            if selected_status not in {"pending", "paid"}:
                errors.append("Invalid status.")
            if not raw_descriptions:
                errors.append("Add at least one item.")
            if len(raw_descriptions) != len(raw_quantities):
                errors.append("Missing quantities.")
            if len(raw_descriptions) != len(raw_prices):
                errors.append("Missing unit prices.")
            if len(raw_descriptions) > 20:
                errors.append("Maximum 20 items.")
            if len(raw_descriptions) == len(raw_quantities) == len(raw_prices):
                item_count = len(raw_descriptions)
            if not errors:
                for index, raw_description in enumerate(raw_descriptions):
                    description = raw_description.strip()
                    quantity_text = raw_quantities[index].strip()
                    price_text = raw_prices[index].strip()
                    if not description:
                        errors.append(f"Item {index + 1}: missing description.")
                    if len(description) > 120:
                        errors.append(f"Item {index + 1}: description too long.")
                    if not quantity_text.isdigit():
                        errors.append(f"Item {index + 1}: invalid quantity.")
                    else:
                        quantity = int(quantity_text)
                        if quantity < 1 or quantity > 10000:
                            errors.append(f"Item {index + 1}: quantity out of range.")
                    try:
                        price = Decimal(price_text)
                        if not price.is_finite() or price < 0 or price > 1000000:
                            errors.append(f"Item {index + 1}: unit price out of range.")
                        if price.as_tuple().exponent < -2:
                            errors.append(f"Item {index + 1}: maximum two decimal places.")
                        if len(price_text) > 16:
                            errors.append(f"Item {index + 1}: unit price too long.")
                    except Exception:
                        errors.append(f"Item {index + 1}: invalid unit price.")
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
                    errors.append("Could not calculate invoice.")
            if not errors:
                try:
                    invoice_id = create_invoice(
                        connection, owner_id, int(selected_customer), selected_date,
                        selected_status, submitted_rows,
                    )
                    return redirect(url_for("invoice_html", invoice_id=invoice_id))
                except ValueError:
                    errors.append("Could not save invoice.")
        if not submitted_rows:
            submitted_rows = [
                {"description": "", "quantity": "1", "unit_price": "0.00"},
                {"description": "", "quantity": "1", "unit_price": "0.00"},
            ]
        parts = ["<!doctype html><html lang='en'><meta charset='utf-8'><title>New Invoice</title>"]
        parts.append("<h1>New Invoice</h1><a href='/invoices'>Back to invoices</a>")
        parts.append("<p>Fill in the customer, date, and at least one item.</p>")
        parts.append("<p>Unit prices accept up to two decimal places.</p>")
        parts.append("<p>Invoices can be pending or paid.</p>")
        if customer_name:
            parts.append("<p>Selected customer: " + str(escape(customer_name)) + "</p>")
        if request.method == "POST":
            parts.append("<p>Items submitted: " + str(item_count) + "</p>")
        for error in errors:
            parts.append("<p role='alert'>" + str(escape(error)) + "</p>")
        if errors:
            parts.append("<p>Please correct the errors and resubmit the form.</p>")
        parts.append("<form method='post'>")
        parts.append("<fieldset><legend>Invoice Details</legend>")
        parts.append("<label>Customer <select name='customer_id' required>")
        parts.append("<option value=''>Select</option>")
        for customer in customers:
            cid = str(customer["id"])
            name = str(escape(customer["name"]))
            selected = " selected" if cid == selected_customer else ""
            parts.append("<option value='" + cid + "'" + selected + ">" + name + "</option>")
        parts.append("</select></label>")
        parts.append("<label>Date <input type='date' name='issue_date' value='" + str(escape(selected_date)) + "' required></label>")
        parts.append("<small>Date is stored in YYYY-MM-DD format.</small>")
        parts.append("<label>Status <select name='status'>")
        for status, label in (("pending", "Pending"), ("paid", "Paid")):
            selected = " selected" if selected_status == status else ""
            parts.append("<option value='" + status + "'" + selected + ">" + label + "</option>")
        parts.append("</select></label></fieldset>")
        parts.append("<fieldset><legend>Items</legend>")
        parts.append("<p>You can add up to 20 items per request.</p>")
        for index, row in enumerate(submitted_rows):
            parts.append("<div><strong>Item " + str(index + 1) + "</strong>")
            parts.append("<label>Description <input name='description' value='" + str(escape(row["description"])) + "' required></label>")
            parts.append("<label>Quantity <input type='number' name='quantity' min='1' value='" + str(escape(row["quantity"])) + "' required></label>")
            parts.append("<label>Unit Price <input name='unit_price' value='" + str(escape(row["unit_price"])) + "' required></label>")
            parts.append("<small>Price corresponds to a single unit.</small>")
            parts.append("</div>")
        parts.append("</fieldset>")
        parts.append("<button type='submit'>Create invoice</button></form>")
        if preview:
            parts.append("<section><h2>Calculation</h2>")
            parts.append("<table><thead><tr><th>Description</th><th>Quantity</th>")
            parts.append("<th>Unit Price</th><th>Line Total</th></tr></thead><tbody>")
            for item in preview["items"]:
                parts.append("<tr><td>" + str(escape(item["description"])) + "</td>")
                parts.append("<td>" + str(item["quantity"]) + "</td>")
                parts.append("<td>" + item["unit_price"] + "</td>")
                parts.append("<td>" + item["line_total"] + "</td></tr>")
            parts.append("</tbody></table>")
            parts.append("<p>Subtotal " + preview["subtotal"] + "</p>")
            parts.append("<p>Discount " + preview["discount"] + "</p>")
            parts.append("<p>Total " + preview["total"] + "</p></section>")
        parts.append("<footer><a href='/'>Home</a></footer>")
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
        return render_template_string("""<!doctype html><title>Report</title><h1>Report {{ month }}</h1>
        <form><input type="month" name="month" value="{{ month }}"><button>View Report</button></form>
        <table><tr><th>Invoice</th><th>Report Total</th></tr>
        {% for row in rows %}<tr><td>{{ row['number'] }}</td><td>{{ row['report_total'] }}</td></tr>
        {% endfor %}</table>""", month=month, rows=rows)

    return app


app = create_app()
