PRAGMA foreign_keys = ON;
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL
);
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    number TEXT NOT NULL UNIQUE,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    issue_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','paid')),
    subtotal TEXT NOT NULL,
    discount TEXT NOT NULL,
    total TEXT NOT NULL
);
CREATE TABLE invoice_items (
    id INTEGER PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price TEXT NOT NULL,
    line_total TEXT NOT NULL
);
CREATE INDEX idx_invoice_owner_date ON invoices(owner_id, issue_date);
CREATE INDEX idx_invoice_customer ON invoices(customer_id);
