"""Minimal seeder: creates 6 doctors and 30 days of availability.
Run from project root after activating venv:

    source .venv/bin/activate
    python scripts/seed_minimal.py

This script is safe to run multiple times: it checks for existing emails and avoids duplicates.
"""
from datetime import date, time, timedelta
from werkzeug.security import generate_password_hash
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Role, User, Doctor, Patient, Department, Appointment, Treatment, DoctorAvailability, MedicalRecord

# Allow a clean run that wipes non-admin users and related data first
CLEAN_RUN = '--clean' in sys.argv


def ensure_roles():
    # making sure roles exist
    with app.app_context():
        for name in ('Admin', 'Doctor', 'Patient'):
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name))
        db.session.commit()
        print("Roles ensured")


def get_or_create_department(name='General'):
    dept = Department.query.filter_by(name=name).first()
    if not dept:
        dept = Department(name=name, description=f'{name} department')
        db.session.add(dept)
        db.session.commit()
    return dept


def create_doctor(email, first, last, dept):
    if User.query.filter_by(email=email).first():
        return User.query.filter_by(email=email).first(), False
    doctor_role = Role.query.filter_by(name='Doctor').first()
    user = User(email=email, password=generate_password_hash('doctor123'), first_name=first, last_name=last, phone='0000000000', is_active=True)
    user.roles.append(doctor_role)
    db.session.add(user)
    db.session.flush()
    doc = Doctor(user_id=user.id, department_id=dept.id, specialization='General', license_number=f'LIC-{user.id:06d}', qualification='MBBS', experience_years=1, is_available=True)
    db.session.add(doc)
    db.session.commit()
    return user, True


def create_availability(doctor, start_date, days, start_time, end_time):
    # Create availability slots for a doctor over a range of days
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        existing = DoctorAvailability.query.filter_by(doctor_id=doctor.id, date=day).first()
        if existing:
            continue
        slot = DoctorAvailability(
            doctor_id=doctor.id,
            date=day,
            start_time=start_time,
            end_time=end_time,
            is_available=True,
        )
        db.session.add(slot)
    db.session.commit()


def main():
    with app.app_context():
        print('Creating tables (if missing)...')
        db.create_all()
        ensure_roles()
        print("Tables and roles ready")
        if CLEAN_RUN:
            print('Clean mode: removing non-admin users and related data...')
            # Delete dependent records first
            try:
                Appointment.query.delete()
                Treatment.query.delete()
                MedicalRecord.query.delete()
                DoctorAvailability.query.delete()
                Doctor.query.delete()
                Patient.query.delete()
                db.session.commit()
            except Exception:
                db.session.rollback()
                print('Warning: error while deleting dependent records; continuing.')

            # Remove users who do NOT have the Admin role
            admin_role = Role.query.filter_by(name='Admin').first()
            admin_user_ids = [u.id for u in User.query.join(User.roles).filter(Role.id == admin_role.id).all()] if admin_role else []
            users_to_delete = User.query.filter(~User.id.in_(admin_user_ids)).all() if admin_user_ids else User.query.all()
            for u in users_to_delete:
                db.session.delete(u)
            db.session.commit()
        dept = get_or_create_department('General')

        # Create 6 doctors (Indian-origin names) with richer profile details
        docs = []
        docs_data = [
            {
                'email': 'dr.rajeev@hospital.test',
                'first': 'Rajeev',
                'last': 'Sharma',
                'specialization': 'Cardiology',
                'qualification': 'MBBS, MD (Cardiology)',
                'experience_years': 12,
                'consultation_fee': 600.0,
                'bio': 'Experienced interventional cardiologist with a focus on patient-centered care.'
            },
            {
                'email': 'dr.priya@hospital.test',
                'first': 'Priya',
                'last': 'Patel',
                'specialization': 'Pediatrics',
                'qualification': 'MBBS, MD (Pediatrics)',
                'experience_years': 8,
                'consultation_fee': 400.0,
                'bio': 'Pediatrician with a gentle approach and expertise in child development.'
            },
        ]
        for ddata in docs_data:
            email = ddata['email']
            first = ddata['first']
            last = ddata['last']
            # create or update
            user = User.query.filter_by(email=email).first()
            if user:
                # update basic name fields
                user.first_name = first
                user.last_name = last
                if not any(r.name == 'Doctor' for r in [role for role in user.roles]):
                    doctor_role = Role.query.filter_by(name='Doctor').first()
                    user.roles.append(doctor_role)
                db.session.commit()
                doc = Doctor.query.filter_by(user_id=user.id).first()
                if not doc:
                    doc = Doctor(user_id=user.id, department_id=dept.id)
                    db.session.add(doc)
                    db.session.commit()
                # update profile details
                doc.specialization = ddata.get('specialization')
                doc.qualification = ddata.get('qualification')
                doc.experience_years = ddata.get('experience_years')
                doc.consultation_fee = ddata.get('consultation_fee')
                doc.bio = ddata.get('bio')
                doc.is_available = True
                db.session.commit()
                created = False
                user_obj = user
            else:
                user_obj, created = create_doctor(email, first, last, dept)
                # set richer profile fields for newly created doctor
                doc = Doctor.query.filter_by(user_id=user_obj.id).first()
                doc.specialization = ddata.get('specialization')
                doc.qualification = ddata.get('qualification')
                doc.experience_years = ddata.get('experience_years')
                doc.consultation_fee = ddata.get('consultation_fee')
                doc.bio = ddata.get('bio')
                doc.is_available = True
                db.session.commit()
                user = user_obj
            docs.append(Doctor.query.filter_by(user_id=user.id).first())
            print(f"Doctor: {email} {'created' if created else 'updated'}")

        # Create availability for the next 30 days for each doctor
        today = date.today()
        start_time = time(9, 0)
        end_time = time(17, 0)
        for d in docs:
            create_availability(d, today, 30, start_time, end_time)
            print(f"Availability created for doctor {d.user.email} from {today} for 30 days")

        # Summary
        print('\nSummary:')
        print('Users:', User.query.count())
        print('Doctors:', Doctor.query.count())
        print('Availability slots:', DoctorAvailability.query.count())


if __name__ == '__main__':
    main()
