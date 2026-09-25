def test_first_invoice_exact_contract(client, login):
    login()
    assert client.get("/invoices/1").json == {
        "id": 1, "number": "FY-00001", "customer": {"id": 1, "name": "Cliente Demo 01"},
        "date": "2024-01-01", "items": [
            {"description": "Caso redondeo A", "quantity": 1, "unit_price": "50.03", "line_total": "50.03"},
            {"description": "Caso redondeo B", "quantity": 1, "unit_price": "50.04", "line_total": "50.04"},
        ], "subtotal": "100.07", "discount": "7.51", "total": "92.56", "status": "paid",
    }


def test_contract_errors(client, login):
    assert client.get("/invoices/1").status_code == 401
    login()
    assert client.get("/invoices/9999").status_code == 404
