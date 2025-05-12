# Contributing Guide

This document provides guidelines and instructions for contributing to this trading bot project.

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/schwab-trading-bot.git
cd schwab-trading-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with the following:
```
DATABASE_URL=sqlite:///instance/tradingbot.db
SCHWAB_API_KEY=your_schwab_api_key
SCHWAB_API_SECRET=your_schwab_api_secret
SECRET_KEY=your_secret_key
OPENAI_API_KEY=your_openai_api_key
```

5. Run the application:
```bash
python main.py
```

## Running Tests

Run tests using pytest:
```bash
pytest
```

## Deployment to Heroku

Follow the instructions in [final_heroku_fix.md](final_heroku_fix.md).

## Project Structure

- `app.py` - Main Flask application
- `models.py` - Database models
- `forms.py` - Flask-WTF forms
- `trading_bot/` - Core trading functionality
  - `api_connector.py` - API integrations (Schwab, Alpaca, etc.)
  - `strategies.py` - Trading strategies
  - `ai_advisor.py` - AI-powered market analysis
- `templates/` - HTML templates
- `static/` - Static assets (CSS, JS, images)
- `tests/` - Test suite

## Contribution Guidelines

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

Thank you for contributing!