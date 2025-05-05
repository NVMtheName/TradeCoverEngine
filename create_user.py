from app import app, db
from models import User, Settings

with app.app_context():
    # Check if user already exists
    existing_user = User.query.filter_by(username='admin').first()
    if existing_user:
        print('User already exists!')
    else:
        # Create user
        user = User(username='admin', email='admin@example.com')
        user.set_password('password123')
        
        # Create settings
        settings = Settings(
            user=user,
            api_provider='schwab',
            is_paper_trading=True,
            force_simulation_mode=True,
            risk_level='moderate',
            max_position_size=5000.0
        )
        
        # Save to database
        db.session.add(user)
        db.session.add(settings)
        db.session.commit()
        print('User created successfully!')
