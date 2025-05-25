release: python -c "from app import app, db; with app.app_context(): db.create_all()"
web: gunicorn app:app
