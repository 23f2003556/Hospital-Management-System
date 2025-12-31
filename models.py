"""
Database Models for Hospital Management System

Models:
- Role: User roles (Admin, Doctor, Patient)
- User: Base user model with authentication
- Admin: Admin user profile
- Doctor: Doctor profile with specialization
- Patient: Patient profile with medical info
- Department: Medical departments/specializations
- DoctorAvailability: Doctor availability slots
- Appointment: Appointment booking system
- Treatment: Treatment records linked to appointments
- MedicalRecord: Additional patient medical records

Relationships:
- User (1) -> (many) Roles
- Doctor (1) -> (many) Appointments
- Patient (1) -> (many) Appointments
- Doctor (1) -> (many) Availability Slots
- Department (1) -> (many) Doctors
- Appointment (1) -> (1) Treatment
- Patient (1) -> (many) MedicalRecords
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import UniqueConstraint

# initializing sqlalchemy
db = SQLAlchemy()

# this table is for user roles (many to many)
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)


class Role(db.Model):
    """User roles for RBAC"""
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # Admin, Doctor, Patient
    
    def __repr__(self):
        # printing the role name
        return '<Role %r>' % self.name


class User(db.Model, UserMixin):
    """Base User model with authentication"""
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False) # first name
    last_name = db.Column(db.String(100), nullable=False) # last name
    phone = db.Column(db.String(15)) # phone number
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    roles = db.relationship('Role', secondary=user_roles, backref='users')
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)
    
    def __repr__(self):
        return '<User %r>' % self.email

class Admin(db.Model):
    """Admin user profile (predefined)"""
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False)  # For multi-level admin
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='admin_profile')
    
    def __repr__(self):
        return f'<Admin {self.user.first_name} {self.user.last_name}>'


class Department(db.Model):
    """Medical departments/specializations"""
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    head_doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    doctors = db.relationship('Doctor', backref='department', lazy='dynamic', foreign_keys='Doctor.department_id')
    
    def __repr__(self):
        return f'<Department {self.name}>'

class Doctor(db.Model):
    """Doctor profile with specialization"""
    __tablename__ = 'doctor'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False, index=True)
    specialization = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    qualification = db.Column(db.String(200))
    experience_years = db.Column(db.Integer, default=0)
    is_available = db.Column(db.Boolean, default=True)
    consultation_fee = db.Column(db.Float, default=0.0)
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='doctor_profile')
    appointments = db.relationship('Appointment', backref='doctor', lazy='dynamic', foreign_keys='Appointment.doctor_id')
    availability_slots = db.relationship('DoctorAvailability', backref='doctor', lazy='dynamic')
    
    def __repr__(self):
        return f'<Doctor Dr. {self.user.first_name} {self.user.last_name}>'

class DoctorAvailability(db.Model):
    """Doctor availability slots"""
    __tablename__ = 'doctor_availability'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    day_of_week = db.Column(db.String(10))  # Monday, Tuesday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    slot_duration = db.Column(db.Integer, default=30)  # Slot duration in minutes
    is_available = db.Column(db.Boolean, default=True)
    is_recurring = db.Column(db.Boolean, default=False)  # For recurring slots
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Availability {self.date} {self.start_time}-{self.end_time}>'

class Patient(db.Model):
    """Patient profile with medical information"""
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False, index=True)
    date_of_birth = db.Column(db.Date)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))  # Male, Female, Other
    blood_group = db.Column(db.String(5))  # A+, B+, etc.
    weight = db.Column(db.Float)  # in kg
    height = db.Column(db.Float)  # in cm
    emergency_contact = db.Column(db.String(15))
    emergency_contact_name = db.Column(db.String(100))
    allergies = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    chronic_diseases = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='patient_profile')
    appointments = db.relationship('Appointment', backref='patient', lazy='dynamic', foreign_keys='Appointment.patient_id')
    medical_records = db.relationship('MedicalRecord', backref='patient', lazy='dynamic')
    
    def __repr__(self):
        return f'<Patient {self.user.first_name} {self.user.last_name}>'

class Appointment(db.Model):
    """Appointment booking system"""
    __tablename__ = 'appointment'
    __table_args__ = (
        UniqueConstraint('doctor_id', 'appointment_date', 'appointment_time', name='uix_doctor_datetime'),
    )
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False, index=True)
    appointment_date = db.Column(db.Date, nullable=False, index=True)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Booked', index=True)  # Booked, Completed, Cancelled, No-Show
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)  # Notes from patient about symptoms
    is_online = db.Column(db.Boolean, default=False)  # Online or in-person
    meeting_link = db.Column(db.String(255))  # For online appointments
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    treatment = db.relationship('Treatment', backref='appointment', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Appointment {self.id} - {self.status}>'


class Treatment(db.Model):
    """Treatment records linked to appointments"""
    __tablename__ = 'treatment'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), unique=True, nullable=False, index=True)
    diagnosis = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text)
    medicines = db.Column(db.Text)  # Detailed medicine info with dosage
    notes = db.Column(db.Text)
    follow_up_date = db.Column(db.Date)
    follow_up_required = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Treatment for Appointment {self.appointment_id}>'


class MedicalRecord(db.Model):
    """Additional patient medical records"""
    __tablename__ = 'medical_record'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False, index=True)
    record_type = db.Column(db.String(50), nullable=False)  # Lab Report, X-Ray, Test, etc.
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(255))  # For storing document URLs/paths
    recorded_date = db.Column(db.Date, nullable=False, default=datetime.now)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MedicalRecord {self.record_type} - {self.patient_id}>'
