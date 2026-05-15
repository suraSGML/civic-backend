web: gunicorn civic_system.wsgi --log-file - --bind 0.0.0.0:$PORT
worker: celery -A civic_system worker -l info
beat: celery -A civic_system beat -l info
