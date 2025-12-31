"""
Database Initialization Script for Hospital Management System

This script programmatically creates all database tables and seeds initial data.
Run this script to set up the database without using any manual DB browser.

Usage:
    python db_init.py

Features:
- Creates all database tables
- Creates predefined roles (Admin, Doctor, Patient)
- Creates initial admin user
- Seeds medical departments
- Seeds sample doctors with availability
- Seeds sample patients
- Seeds sample appointments
"""

import os
import sys
from datetime import datetime, timedelta, time
from werkzeug.security import generate_password_hash

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import (
    Role, User, Admin, Department, Doctor, DoctorAvailability,
    Patient, Appointment, Treatment, MedicalRecord
)


def create_tables():
    # function to create tables
    print("Creating database tables...")
    with app.app_context():
        db.create_all()
        print("Tables created!")


def create_roles():
    """Create predefined user roles"""
    print("\n👥 Creating user roles...")
    with app.app_context():
        roles_data = [
            {'name': 'Admin'},
            {'name': 'Doctor'},
            {'name': 'Patient'}
        ]
        
        for role_data in roles_data:
            role = Role.query.filter_by(name=role_data['name']).first()
            if not role:
                new_role = Role(**role_data)
                db.session.add(new_role)
                print(f"  ✓ Created role: {role_data['name']}")
            else:
                print(f"  ℹ Role already exists: {role_data['name']}")
        
        db.session.commit()
        print("Roles created!")


def create_admin():
    """Create predefined admin user"""
    print("\n🔐 Creating admin user...")
    with app.app_context():
        admin_email = 'jannu@gmail.com'
        admin_user = User.query.filter_by(email=admin_email).first()
        admin_role = Role.query.filter_by(name='Admin').first()
        
        if not admin_user:
            admin_password = generate_password_hash('admin123')
            admin_user = User(
                email=admin_email,
                password=admin_password,
                first_name='Admin',
                last_name='User',
                phone='9999999999',
                address='Hospital Address',
                is_active=True
            )
            admin_user.roles.append(admin_role)
            db.session.add(admin_user)
            db.session.flush()
            
            # Create admin profile
            admin_profile = Admin(
                user_id=admin_user.id,
                is_super_admin=True,
                last_login=datetime.utcnow()
            )
            db.session.add(admin_profile)
            print(f"  ✓ Created admin user: {admin_email}")
        else:
            print(f"  ℹ Admin user already exists: {admin_email}")
            if admin_role not in admin_user.roles:
                admin_user.roles.append(admin_role)
                print(f"  ✓ Added Admin role to existing user")
        
        db.session.commit()
        print("Admin user created!")
        print("Email: " + admin_email)
        print("Password: admin123")


def seed_departments():
    """Seed medical departments/specializations"""
    print("\n🏥 Seeding departments...")
    with app.app_context():
        departments_data = [
            {
                'name': 'Cardiology',
                'description': 'Heart and cardiovascular system disease treatment'
            },
            {
                'name': 'Neurology',
                'description': 'Brain and nervous system disorder treatment'
            },
            {
                'name': 'Orthopedics',
                'description': 'Bones, joints and musculoskeletal system treatment'
            },
            {
                'name': 'Pediatrics',
                'description': 'Child healthcare and treatment'
            },
            {
                'name': 'Oncology',
                'description': 'Cancer treatment and care'
            },
            {
                'name': 'Dermatology',
                'description': 'Skin and dermatological disorders treatment'
            },
            {
                'name': 'Psychiatry',
                'description': 'Mental health and psychiatric care'
            },
            {
                'name': 'General Surgery',
                'description': 'Surgical procedures and operations'
            }
        ]
        
        for dept_data in departments_data:
            dept = Department.query.filter_by(name=dept_data['name']).first()
            if not dept:
                new_dept = Department(**dept_data)
                db.session.add(new_dept)
                print(f"  ✓ Created department: {dept_data['name']}")
            else:
                print(f"  ℹ Department already exists: {dept_data['name']}")
        
        db.session.commit()
        print("✅ Departments seeded successfully!")

















def print_database_summary():
    """Print database summary"""
    print("\n" + "="*60)
    print("📊 DATABASE SUMMARY")
    print("="*60)
    with app.app_context():
        print(f"Users: {User.query.count()}")
        print(f"Admins: {Admin.query.count()}")
        print(f"Doctors: {Doctor.query.count()}")
        print(f"Patients: {Patient.query.count()}")
        print(f"Departments: {Department.query.count()}")
        print(f"Appointments: {Appointment.query.count()}")
        print(f"Treatments: {Treatment.query.count()}")
        print(f"Doctor Availability Slots: {DoctorAvailability.query.count()}")
        print("="*60)


def main():
    """Main initialization function"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "Hospital Management System - DB Initialization" + " "*2 + "║")
    print("╚" + "="*58 + "╝")
    
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--recreate', action='store_true', help='Delete the existing sqlite DB and recreate tables')
    args = parser.parse_args()

    try:
        if args.recreate:
            db_path = os.path.join(os.path.dirname(__file__), 'instance', 'hmdbms.sql')
            if os.path.exists(db_path):
                print(f"Removing existing DB at {db_path}")
                os.remove(db_path)
            else:
                print("No existing DB file found; continuing to create new DB.")
        # Step 1: Create tables
        create_tables()
        
        # Step 2: Create roles
        create_roles()
        
        # Step 3: Create admin
        create_admin()
        
        # Step 4: Seed departments
        seed_departments()
        

        
        # Print summary
        print_database_summary()
        
        print("\n✅ Database initialization completed successfully!")
        print("\n🔐 Predefined Credentials:")
        print("   Admin Email: jannu@gmail.com")
        print("   Admin Password: admin123")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error during database initialization: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
