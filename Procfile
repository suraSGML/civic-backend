release: python manage.py init_db
web: gunicorn civic_system.wsgi --log-file - --bind 0.0.0.0:$PORT

