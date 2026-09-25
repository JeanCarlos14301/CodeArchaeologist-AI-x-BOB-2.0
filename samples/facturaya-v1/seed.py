import argparse
import hashlib
import random
from datetime import date
from pathlib import Path

from billing import create_invoice
from db import connect, init_db


def seed(path, reset=False):
    target = Path(path)
    if target.exists():
        if not reset:
            raise FileExistsError(f"Database exists: {target}")
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20240115)
    connection = connect(str(target))
    try:
        init_db(connection)
        users = (("ana", "DemoAna!2024", "Ana Demo"),
                 ("bruno", "DemoBruno!2024", "Bruno Demo"),
                 ("carla", "DemoCarla!2024", "Carla Demo"))
        for index, (username, password, name) in enumerate(users, 1):
            salt = f"demo{index:02d}salt"
            digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 1000).hex()
            password_hash = f"pbkdf2:sha256:1000${salt}${digest}"
            connection.execute(
                "INSERT INTO users(id, username, password_hash, display_name) VALUES (?, ?, ?, ?)",
                (index, username, password_hash, name),
            )
        for index in range(1, 31):
            connection.execute(
                "INSERT INTO customers(id, owner_id, name, email) VALUES (?, ?, ?, ?)",
                (index, ((index - 1) % 3) + 1, f"Cliente Demo {index:02d}", f"cliente{index:02d}@example.invalid"),
            )
        connection.commit()
        for index in range(200):
            owner_id = (index % 3) + 1
            customer_id = owner_id + 3 * ((index // 3) % 10)
            month = (index % 12) + 1
            day = (index % 27) + 1
            issue_date = date(2024, month, day).isoformat()
            if index == 0:
                items = [
                    {"description": "Caso redondeo A", "quantity": 1, "unit_price": "50.03"},
                    {"description": "Caso redondeo B", "quantity": 1, "unit_price": "50.04"},
                ]
            else:
                items = [
                    {"description": f"Servicio {index:03d}-A", "quantity": rng.randint(1, 3),
                     "unit_price": f"{rng.randint(8, 45)}.{rng.randint(0, 99):02d}"},
                    {"description": f"Servicio {index:03d}-B", "quantity": rng.randint(1, 2),
                     "unit_price": f"{rng.randint(5, 38)}.{rng.randint(0, 99):02d}"},
                    {"description": f"Servicio {index:03d}-C", "quantity": 1,
                     "unit_price": f"{rng.randint(2, 22)}.{rng.randint(0, 99):02d}"},
                ]
            create_invoice(connection, owner_id, customer_id, issue_date,
                           "paid" if index % 4 == 0 else "pending", items, commit=False)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database", help="Path to a new SQLite database")
    parser.add_argument("--reset", action="store_true")
    arguments = parser.parse_args()
    seed(arguments.database, arguments.reset)
    print(f"Seeded {arguments.database}")
