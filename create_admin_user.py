#!/usr/bin/env python3
"""
Create Admin User Script for Arbion Trading Platform
This script creates the admin user with proper authentication.
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_admin_user():
    """Create or update admin user with proper credentials"""
    
    with app.app_context():
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        
        if admin:
            print("Admin user exists, updating password...")
            admin.set_password('admin123')
            admin.is_admin = True
            admin.access_level = 'admin'
            admin.email = 'admin@arbion.ai'
        else:
            print("Creating new admin user...")
            admin = User(
                username='admin',
                email='admin@arbion.ai',
                is_admin=True,
                access_level='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
        
        try:
            db.session.commit()
            print(f"Admin user created/updated successfully:")
            print(f"  Username: {admin.username}")
            print(f"  Email: {admin.email}")
            print(f"  Admin status: {admin.is_admin}")
            print(f"  Password hash exists: {bool(admin.password_hash)}")
            
            # Test password verification
            test_result = admin.check_password('admin123')
            print(f"  Password verification test: {'PASS' if test_result else 'FAIL'}")
            
            return True
            
        except Exception as e:
            print(f"Error creating admin user: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = create_admin_user()
    if success:
        print("\nAdmin user is ready for login!")
    else:
        print("\nFailed to create admin user.")