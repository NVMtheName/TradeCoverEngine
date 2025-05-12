# Heroku Procfile Options

## Current Procfile
Your current Procfile is very simple:
```
web: gunicorn main:app
```

This defines a single `web` process type that runs the command `gunicorn main:app`.

## Available Process Types

### 1. Web Process (Required for Web Apps)
The `web` process type is special - it's the only process that can receive external HTTP traffic from Heroku's routers.
```
web: gunicorn main:app
```

Options for your web process:
- **Bind to the correct port**: `gunicorn --bind 0.0.0.0:$PORT main:app`
- **Add workers**: `gunicorn --workers=4 main:app`
- **Configure timeout**: `gunicorn --timeout 60 main:app`
- **Enable threading**: `gunicorn --workers=2 --threads=4 main:app`

### 2. Worker Processes
For background processing tasks:
```
worker: python worker.py
```

### 3. One-off Processes
For initialization or maintenance tasks:
```
release: python manage.py migrate
```

The `release` process type runs after the build but before new web processes are started during deployments.

### 4. Clock Processes
For scheduled tasks:
```
clock: python clock.py
```

## Enhanced Procfile Example
Here's a more comprehensive example with multiple process types:

```
web: gunicorn --workers=2 --bind 0.0.0.0:$PORT --log-file=- main:app
worker: python trading_bot/worker.py
clock: python trading_bot/scheduler.py
release: python manage.py migrate
```

## Procfile for Your Trading Bot

Based on your app's architecture, here's an optimized Procfile:

```
web: gunicorn --workers=2 --bind 0.0.0.0:$PORT --timeout 60 main:app
worker: python -m trading_bot.auto_trader
clock: python -m trading_bot.scheduler
release: python -c "from app import app, db; from models import User, Settings, Trade, WatchlistItem; app.app_context().push(); db.create_all()"
```

This setup would:
1. Run your Flask app with gunicorn (web)
2. Run your auto trader in a separate worker process
3. Run a scheduler for periodic tasks
4. Initialize your database during deployment

## Additional Considerations

### Process Formation
You can control how many dynos run for each process type using the `heroku ps:scale` command:
```
heroku ps:scale web=1 worker=2 clock=1
```

### Resource Allocation
Different process types can use different dyno sizes:
```
heroku ps:resize web=standard-2x worker=performance-m
```

### Local Testing
You can use the Procfile locally with:
```
heroku local
```
Or run specific process types:
```
heroku local web
```

### Environment Variables
All process types will have access to the same environment variables.

## Recommended Next Steps

1. Determine if you need worker processes for background tasks
2. Consider adding a release command for database migrations
3. Optimize your web process configuration for performance