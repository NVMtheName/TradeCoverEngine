from app import app, db
from models import Settings
from sqlalchemy import text

with app.app_context():
    # Update settings using SQLAlchemy's text() function
    db.session.execute(text("UPDATE settings SET force_simulation_mode = 0"))
    db.session.commit()
    
    # Print the results
    results = db.session.execute(text("SELECT id, user_id, api_provider, is_paper_trading, force_simulation_mode FROM settings")).fetchall()
    print("Updated settings to disable simulation mode:")
    for row in results:
        print(f"ID: {row[0]}, User: {row[1]}, Provider: {row[2]}, Paper Trading: {row[3]}, Force Simulation: {row[4]}")
