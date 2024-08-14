import reflex as rx

config = rx.Config(
    app_name="core",
    db_url="sqlite:///data/db.sqlite3",
    frontend_port=8000,
    backend_port=8001,
    frontend_url="http://localhost:8000",
    backend_url="http://localhost:8001",
)