"""
CLI commands untuk manajemen database SIGAROB.
Jalankan: flask --app run seed-admin
"""
import click
from flask import current_app
from app import db
from app.models.user import User


def register_commands(app):
    @app.cli.command("seed-admin")
    @click.option("--username", default="admin", help="Username admin")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def seed_admin(username, password):
        """Buat akun admin pertama."""
        with app.app_context():
            existing = User.query.filter_by(username=username).first()
            if existing:
                click.echo(f"[!] User '{username}' sudah ada.")
                return

            admin = User(username=username, role="admin")
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            click.echo(f"[✓] Admin '{username}' berhasil dibuat.")

    @app.cli.command("create-tables")
    def create_tables():
        """Buat semua tabel (jika belum ada)."""
        with app.app_context():
            db.create_all()
            click.echo("[✓] Tabel berhasil dibuat.")
