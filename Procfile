web: gunicorn --workers=2 --bind 0.0.0.0:$PORT --timeout 60 main:app
release: python -c "from app import app, db; app.app_context().push(); db.create_all()"