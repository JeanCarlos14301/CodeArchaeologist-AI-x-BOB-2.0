from functools import wraps

from flask import abort, redirect, request, session, url_for
from werkzeug.security import check_password_hash


def authenticate(connection, username, password):
    user = connection.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/invoices/") and request.path.rsplit("/", 1)[-1].isdigit():
                abort(401)
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped
