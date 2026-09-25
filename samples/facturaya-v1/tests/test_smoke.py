def test_import_and_home(client):
    assert client.get("/").status_code == 302
    assert client.get("/login").status_code == 200


def test_login_logout(client, login):
    assert client.post("/login", data={"username": "ana", "password": "wrong"}).status_code == 401
    assert login().status_code == 302
    assert client.get("/").status_code == 200
    assert client.post("/logout").status_code == 302
    assert client.get("/invoices/1").status_code == 401


def test_customers_and_invoice_creation(client, login):
    login()
    assert b"Cliente Demo 01" in client.get("/customers").data
    assert client.get("/customers/1").status_code == 200
    assert client.get("/customers/2").status_code == 404
    response = client.post("/invoices/new", data={
        "customer_id": "1", "issue_date": "2024-12-31", "status": "pending",
        "description": ["Consultoría", "Soporte"], "quantity": ["2", "1"],
        "unit_price": ["30.00", "40.00"],
    })
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/invoices/201/view")
    assert b"FY-00201" in client.get("/invoices/201/view").data
    payload = client.get("/invoices/201").json
    assert (payload["subtotal"], payload["discount"], payload["total"]) == ("100.00", "7.50", "92.50")


def test_invoice_rejects_non_iso_date(client, login):
    login()
    response = client.post("/invoices/new", data={
        "customer_id": "1", "issue_date": "20241231", "status": "pending",
        "description": ["Trabajo"], "quantity": ["1"], "unit_price": ["10.00"],
    })
    assert response.status_code == 400
