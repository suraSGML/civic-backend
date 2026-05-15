release: cd backend && python manage.py migrate && python manage.py seed_data
web: cd backend && gunicorn civic_system.wsgi --log-file - --bind 0.0.0.0:$PORT

