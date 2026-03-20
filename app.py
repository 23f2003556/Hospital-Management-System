from flask import Flask, render_template, redirect, url_for, flash, request, make_response
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, timedelta
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
import csv
from io import StringIO
from markupsafe import escape

from models import db, User, Role, Patient, Doctor, Department, Appointment, Treatment, DoctorAvailability, MedicalRecord
from config import Config
from forms import LoginForm, RegistrationForm
from flask_wtf import FlaskForm
from wtforms import DateField, TimeField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError


# --------------------- App Setup ---------------------
# creating the flask app here
app = Flask(__name__)
# loading config from the config file
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Register API blueprint (JSON endpoints)
from api import api as api_bp
app.register_blueprint(api_bp)


# --------------------- User Loader ---------------------
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        db.session.rollback()
        return None


# --------------------- Role-Based Decorator ---------------------
def role_required(*roles):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if not current_user.has_role(roles[0]) and not any(current_user.has_role(role) for role in roles):
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
            return func(*args, **kwargs)
        return decorated_view
    return wrapper


# --------------------- Utility Functions ---------------------
def sanitize_input(text):
    """Remove potentially harmful characters from input"""
    if text:
        return escape(text).strip()
    return text


def check_appointment_conflict(doctor_id, appointment_date, appointment_time, exclude_id=None):
    """Check if appointment slot conflicts with existing appointments."""
    query = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.appointment_time == appointment_time,
        Appointment.status == 'Booked'
    )
    if exclude_id:
        query = query.filter(Appointment.id != exclude_id)
    return query.first() is not None


def validate_status_transition(current_status, new_status):
    """Validate appointment status transitions."""
    valid_transitions = {
        'Booked': ['Completed', 'Cancelled'],
        'Completed': [],
        'Cancelled': []
    }
    return new_status in valid_transitions.get(current_status, [])


# --------------------- Appointment Form ---------------------
class AppointmentForm(FlaskForm):
    appointment_date = DateField('Appointment Date',
        validators=[DataRequired()],
        format='%Y-%m-%d'
    )
    appointment_time = TimeField('Appointment Time',
        validators=[DataRequired()]
    )
    reason = TextAreaField('Reason for Visit',
        validators=[DataRequired(), Length(min=10, max=500)]
    )
    submit = SubmitField('Book Appointment')

    def validate_appointment_date(self, field):
        if field.data < date.today():
            raise ValidationError('Cannot book appointments in the past')


# --------------------- Setup Route (Run once on Vercel) ---------------------
@app.route('/setup-db')
def setup_db():
    try:
        # Check if we are using SQLite or Postgres
        is_postgres = app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql')
        print(f"Initializing database. Connection type: {'PostgreSQL' if is_postgres else 'SQLite'}")
        
        db.create_all()
        
        # Also create initial roles if they don't exist
        from models import Role
        roles = ['Admin', 'Doctor', 'Patient']
        for r_name in roles:
            try:
                if not Role.query.filter_by(name=r_name).first():
                    db.session.add(Role(name=r_name))
            except Exception:
                db.session.rollback()
                db.session.add(Role(name=r_name))
                
        db.session.commit()
        return "Database tables and roles created successfully! You can now register or login."
    except Exception as e:
        db.session.rollback()
        return f"Error creating database: {str(e)} <br><br> Check your DATABASE_URL in Vercel settings."

# --------------------- Core Routes ---------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    # check if user is already logged in
    if current_user.is_authenticated:
        print("User is already logged in, redirecting to dashboard")
        return redirect(url_for('dashboard'))
    
    # create the login form
    form = LoginForm()
    if form.validate_on_submit():
        print("Form validated successfully")
        # get the user from database
        user = User.query.filter_by(email=form.email.data).first()
        
        # check if user exists and password is correct
        if user and check_password_hash(user.password, form.password.data):
            print("Password check passed")
            if user.is_active:
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash('Your account has been deactivated.', 'danger')
        else:
            print("Invalid login attempt")
            flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Server-side validation: enforce password length
        if not form.password.data or len(form.password.data) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html', form=form)
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            email=sanitize_input(form.email.data),
            password=hashed_password,
            first_name=sanitize_input(form.first_name.data),
            last_name=sanitize_input(form.last_name.data),
            phone=sanitize_input(form.phone.data)
        )
        patient_role = Role.query.filter_by(name='Patient').first()
        user.roles.append(patient_role)
        db.session.add(user)
        db.session.commit()

        patient = Patient(user_id=user.id)
        db.session.add(patient)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    # logging out the user
    logout_user()
    print("User logged out")
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.has_role('Admin'):
        print("Redirecting to admin dashboard")
        return redirect(url_for('admin_dashboard'))
    elif current_user.has_role('Doctor'):
        print("Redirecting to doctor dashboard")
        return redirect(url_for('doctor_dashboard'))
    elif current_user.has_role('Patient'):
        print("Redirecting to patient dashboard")
        return redirect(url_for('patient_dashboard'))
    else:
        print("Unknown role")
        flash('Role not recognized.', 'danger')
        return redirect(url_for('index'))


# --------------------- Admin Routes ---------------------
@app.route('/admin/dashboard')
@role_required('Admin')
def admin_dashboard():
    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    pending_appointments = Appointment.query.filter_by(status='Booked').count()
    
    recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(10).all()
    # Provide lists for quick admin actions on dashboard
    doctors = Doctor.query.join(User).order_by(User.first_name.asc()).limit(10).all()
    patients = Patient.query.join(User).order_by(User.first_name.asc()).limit(10).all()
    today = date.today()
    upcoming_appointments = Appointment.query.filter(Appointment.appointment_date >= today).order_by(Appointment.appointment_date.asc()).limit(10).all()

    return render_template('admin/dashboard.html',
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=total_appointments,
        pending_appointments=pending_appointments,
        recent_appointments=recent_appointments,
        doctors=doctors,
        patients=patients,
        upcoming_appointments=upcoming_appointments
    )


@app.route('/api/admin/stats')
@role_required('Admin')
def api_admin_stats():
    # Return totals for charts
    data = {
        'total_doctors': Doctor.query.count(),
        'total_patients': Patient.query.count(),
        'total_appointments': Appointment.query.count(),
    }
    return data


@app.route('/api/doctor/appointments_distribution')
@role_required('Doctor')
def api_doctor_appointments_distribution():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    # Count appointments per status
    counts = {}
    for status, label in [('Booked', 'Booked'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')]:
        counts[status] = Appointment.query.filter_by(doctor_id=doctor.id, status=status).count()
    return counts


@app.route('/api/patient/treatments')
@role_required('Patient')
def api_patient_treatments():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient.id).order_by(Treatment.created_at.desc()).all()
    data = [{'date': t.created_at.strftime('%Y-%m-%d'), 'diagnosis': t.diagnosis} for t in treatments]
    return {'treatments': data}


@app.route('/admin/doctor/add', methods=['GET', 'POST'])
@role_required('Admin')
def admin_add_doctor():
    """Add a new doctor (Admin-only)."""
    if request.method == 'POST':
        email = sanitize_input(request.form.get('email'))
        password = request.form.get('password')
        first_name = sanitize_input(request.form.get('first_name'))
        last_name = sanitize_input(request.form.get('last_name'))
        phone = sanitize_input(request.form.get('phone'))
        specialization = sanitize_input(request.form.get('specialization'))
        department_id = request.form.get('department_id')
        # Server-side validation
        if not email or '@' not in email:
            flash('A valid email is required.', 'danger')
            return redirect(url_for('admin_add_doctor'))
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('admin_add_doctor'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'danger')
            return redirect(url_for('admin_add_doctor'))

        hashed_password = generate_password_hash(password)
        user = User(
            email=email,
            password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
        doctor_role = Role.query.filter_by(name='Doctor').first()
        user.roles.append(doctor_role)
        db.session.add(user)
        db.session.flush()

        doctor = Doctor(
            user_id=user.id,
            department_id=department_id,
            specialization=specialization,
            license_number=f"DOC-{user.id:04d}",
            qualification="MBBS",
            experience_years=0
        )
        db.session.add(doctor)
        db.session.flush()

        # Seed default availability for the newly created doctor for the next 7 days
        today = date.today()
        for offset in range(7):
            slot_date = today + timedelta(days=offset)
            morning_start = datetime.strptime('09:00', '%H:%M').time()
            morning_end = datetime.strptime('13:00', '%H:%M').time()
            afternoon_start = datetime.strptime('15:00', '%H:%M').time()
            afternoon_end = datetime.strptime('18:00', '%H:%M').time()

            morning_slot = DoctorAvailability(
                doctor_id=doctor.id,
                date=slot_date,
                day_of_week=slot_date.strftime('%A'),
                start_time=morning_start,
                end_time=morning_end,
                slot_duration=30,
                is_available=True,
                is_recurring=False
            )
            afternoon_slot = DoctorAvailability(
                doctor_id=doctor.id,
                date=slot_date,
                day_of_week=slot_date.strftime('%A'),
                start_time=afternoon_start,
                end_time=afternoon_end,
                slot_duration=30,
                is_available=True,
                is_recurring=False
            )
            db.session.add(morning_slot)
            db.session.add(afternoon_slot)

        db.session.commit()

        flash(f'Doctor {first_name} {last_name} added successfully!', 'success')
        return redirect(url_for('admin_doctors'))

    departments = Department.query.all()
    return render_template('admin/add_doctor.html', departments=departments)


@app.route('/admin/doctors')
@role_required('Admin')
def admin_doctors():
    # Search and filter support
    q = request.args.get('q', '').strip()
    specialization = request.args.get('specialization', '').strip()

    query = Doctor.query.join(User)
    if q:
        like_q = f"%{q}%"
        query = query.filter(or_(User.first_name.ilike(like_q), User.last_name.ilike(like_q)))

    if specialization:
        spec_like = f"%{specialization}%"
        query = query.filter(Doctor.specialization.ilike(spec_like))

    doctors = query.all()
    return render_template('admin/doctors.html', doctors=doctors, q=q, specialization=specialization)


@app.route('/admin/patients')
@role_required('Admin')
def admin_patients():
    q = request.args.get('q', '').strip()
    contact = request.args.get('contact', '').strip()

    query = Patient.query.join(User)
    if q:
        # If query looks like an integer, allow searching by patient ID as well
        if q.isdigit():
            query = query.filter(or_(Patient.id == int(q), User.first_name.ilike(f"%{q}%"), User.last_name.ilike(f"%{q}%")))
        else:
            like_q = f"%{q}%"
            query = query.filter(or_(User.first_name.ilike(like_q), User.last_name.ilike(like_q)))
    if contact:
        like_c = f"%{contact}%"
        query = query.filter(User.phone.ilike(like_c))

    patients = query.all()
    return render_template('admin/patients.html', patients=patients, q=q, contact=contact)


@app.route('/admin/patient/<int:patient_id>/history')
@role_required('Admin')
def admin_view_patient_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    medical_records = patient.medical_records.order_by(MedicalRecord.recorded_date.desc()).all()
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient.id).order_by(Treatment.created_at.desc()).all()
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.appointment_date.desc()).all()
    return render_template('admin/patient_history.html', patient=patient, medical_records=medical_records, treatments=treatments, appointments=appointments)


@app.route('/admin/appointments')
@role_required('Admin')
def admin_appointments():
    status_filter = request.args.get('status', 'all')
    when = request.args.get('when', 'all')  # upcoming, past, all

    query = Appointment.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    today = date.today()
    if when == 'upcoming':
        query = query.filter(Appointment.appointment_date >= today)
    elif when == 'past':
        query = query.filter(Appointment.appointment_date < today)

    appointments = query.order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('admin/appointments.html', 
        appointments=appointments,
        status_filter=status_filter,
        when=when
    )


@app.route('/admin/doctor/edit/<int:doctor_id>', methods=['GET', 'POST'])
@role_required('Admin')
def admin_edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    if request.method == 'POST':
        # Update basic profile fields
        doctor.specialization = sanitize_input(request.form.get('specialization'))
        doctor.qualification = sanitize_input(request.form.get('qualification'))
        doctor.experience_years = int(request.form.get('experience_years') or 0)
        doctor.consultation_fee = float(request.form.get('consultation_fee') or 0.0)
        doctor.bio = sanitize_input(request.form.get('bio'))
        db.session.commit()
        flash('Doctor profile updated successfully.', 'success')
        return redirect(url_for('admin_doctors'))

    departments = Department.query.all()
    return render_template('admin/edit_doctor.html', doctor=doctor, departments=departments)


@app.route('/admin/patient/edit/<int:patient_id>', methods=['GET', 'POST'])
@role_required('Admin')
def admin_edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    user = patient.user
    if request.method == 'POST':
        # Update user fields
        user.first_name = sanitize_input(request.form.get('first_name')) or user.first_name
        user.last_name = sanitize_input(request.form.get('last_name')) or user.last_name
        user.phone = sanitize_input(request.form.get('phone')) or user.phone
        user.address = sanitize_input(request.form.get('address')) or user.address

        # Update patient-specific fields
        dob = request.form.get('date_of_birth')
        try:
            patient.date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date() if dob else patient.date_of_birth
        except Exception:
            # ignore invalid date format and keep existing
            pass
        patient.gender = sanitize_input(request.form.get('gender')) or patient.gender
        patient.blood_group = sanitize_input(request.form.get('blood_group')) or patient.blood_group
        patient.allergies = sanitize_input(request.form.get('allergies')) or patient.allergies
        patient.medical_history = sanitize_input(request.form.get('medical_history')) or patient.medical_history
        db.session.commit()
        flash('Patient information updated successfully.', 'success')
        return redirect(url_for('admin_patients'))

    return render_template('admin/edit_patient.html', patient=patient, user=user)


@app.route('/admin/toggle_user/<string:user_type>/<int:user_id>', methods=['POST'])
@role_required('Admin')
def admin_toggle_user(user_type, user_id):
    # user_type: 'doctor' or 'patient'
    if user_type == 'doctor':
        doctor = Doctor.query.get_or_404(user_id)
        user = doctor.user
    elif user_type == 'patient':
        patient = Patient.query.get_or_404(user_id)
        user = patient.user
    else:
        flash('Invalid user type.', 'danger')
        return redirect(url_for('admin_dashboard'))

    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.first_name} {user.last_name} has been {status}.', 'info')
    return redirect(request.referrer or url_for('admin_dashboard'))


@app.route('/admin/delete_user/<string:user_type>/<int:user_id>', methods=['POST'])
@role_required('Admin')
def admin_delete_user(user_type, user_id):
    # Attempt to safely delete a doctor or patient only if no linked appointments exist
    if user_type == 'doctor':
        doctor = Doctor.query.get_or_404(user_id)
        appt_count = Appointment.query.filter_by(doctor_id=doctor.id).count()
        if appt_count > 0:
            flash('Cannot delete doctor with existing appointments. Consider blacklisting instead.', 'danger')
            return redirect(request.referrer or url_for('admin_dashboard'))
        user = doctor.user
        db.session.delete(doctor)
        # delete user only if no other profiles tied
        db.session.delete(user)
        db.session.commit()
        flash('Doctor deleted successfully.', 'success')
        return redirect(request.referrer or url_for('admin_dashboard'))
    elif user_type == 'patient':
        patient = Patient.query.get_or_404(user_id)
        appt_count = Appointment.query.filter_by(patient_id=patient.id).count()
        if appt_count > 0:
            flash('Cannot delete patient with existing appointments. Consider blacklisting instead.', 'danger')
            return redirect(request.referrer or url_for('admin_dashboard'))
        user = patient.user
        db.session.delete(patient)
        db.session.delete(user)
        db.session.commit()
        flash('Patient deleted successfully.', 'success')
        return redirect(request.referrer or url_for('admin_dashboard'))
    else:
        flash('Invalid user type for deletion.', 'danger')
        return redirect(request.referrer or url_for('admin_dashboard'))


@app.route('/admin/export/appointments')
@role_required('Admin')
def admin_export_appointments():
    appointments = Appointment.query.all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Patient', 'Doctor', 'Date', 'Time', 'Status', 'Reason'])
    
    for appt in appointments:
        writer.writerow([
            appt.id,
            f"{appt.patient.user.first_name} {appt.patient.user.last_name}",
            f"Dr. {appt.doctor.user.first_name} {appt.doctor.user.last_name}",
            appt.appointment_date,
            appt.appointment_time,
            appt.status,
            appt.reason
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=appointments.csv"
    output.headers["Content-type"] = "text/csv"
    return output


# --------------------- Doctor Dashboard ---------------------
@app.route('/doctor/dashboard')
@role_required('Doctor')
def doctor_dashboard():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    today = date.today()
    todays_appointments = Appointment.query.filter_by(
        doctor_id=doctor.id,
        appointment_date=today,
        status='Booked'
    ).all()
    week_end = today + timedelta(days=7)
    week_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date >= today,
        Appointment.appointment_date <= week_end,
        Appointment.status == 'Booked'
    ).all()
    # List distinct patients assigned to this doctor
    patients = Patient.query.join(Appointment).filter(Appointment.doctor_id == doctor.id).distinct(Patient.id).all()
    patient_count = len(patients)
    
    return render_template('doctor/dashboard.html',
        doctor=doctor,
        todays_appointments=todays_appointments,
        week_appointments=week_appointments,
        patient_count=patient_count,
        patients=patients
    )


@app.route('/doctor/appointment/<int:appointment_id>/status', methods=['POST'])
@role_required('Doctor')
def doctor_update_appointment_status(appointment_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.doctor_id != doctor.id:
        flash('You are not authorized to update this appointment.', 'danger')
        return redirect(url_for('doctor_dashboard'))

    new_status = request.form.get('status')
    if not validate_status_transition(appt.status, new_status):
        flash('Invalid status transition.', 'danger')
        return redirect(url_for('doctor_dashboard'))

    appt.status = new_status
    db.session.commit()
    flash(f'Appointment {appt.id} marked as {new_status}.', 'success')
    return redirect(url_for('doctor_dashboard'))


@app.route('/doctor/appointment/<int:appointment_id>/treatment', methods=['GET', 'POST'])
@role_required('Doctor')
def doctor_add_treatment(appointment_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.doctor_id != doctor.id:
        flash('You are not authorized to add treatment to this appointment.', 'danger')
        return redirect(url_for('doctor_dashboard'))

    if request.method == 'POST':
        diagnosis = sanitize_input(request.form.get('diagnosis'))
        # Server-side validation
        if not diagnosis or len(diagnosis) < 5:
            flash('Diagnosis is required and must be at least 5 characters.', 'danger')
            return redirect(url_for('doctor_add_treatment', appointment_id=appointment_id))
        prescription = sanitize_input(request.form.get('prescription'))
        medicines = sanitize_input(request.form.get('medicines'))
        notes = sanitize_input(request.form.get('notes'))
        follow_up = request.form.get('follow_up_date')
        follow_up_required = bool(request.form.get('follow_up_required'))

        # Ensure appointment is marked Completed
        appt.status = 'Completed'

        # Create or update treatment
        treatment = appt.treatment
        if not treatment:
            treatment = Treatment(appointment_id=appt.id, diagnosis=diagnosis)
            db.session.add(treatment)
        treatment.diagnosis = diagnosis
        treatment.prescription = prescription
        treatment.medicines = medicines
        treatment.notes = notes
        treatment.follow_up_required = follow_up_required
        if follow_up:
            try:
                treatment.follow_up_date = datetime.strptime(follow_up, '%Y-%m-%d').date()
            except Exception:
                treatment.follow_up_date = None

        db.session.commit()
        flash('Treatment saved successfully.', 'success')
        return redirect(url_for('doctor_dashboard'))

    return render_template('doctor/add_treatment.html', appointment=appt)


@app.route('/doctor/appointment/<int:appointment_id>/update_history', methods=['GET', 'POST'])
@role_required('Doctor')
def doctor_update_patient_history(appointment_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.doctor_id != doctor.id:
        flash('You are not authorized to update this appointment history.', 'danger')
        return redirect(url_for('doctor_dashboard'))

    if request.method == 'POST':
        visit_type = sanitize_input(request.form.get('visit_type'))
        test_done = sanitize_input(request.form.get('test_done'))
        diagnosis = sanitize_input(request.form.get('diagnosis'))
        medicines = sanitize_input(request.form.get('medicines'))
        prescription = sanitize_input(request.form.get('prescription'))
        notes = sanitize_input(request.form.get('notes'))

        # Ensure appointment is marked Completed
        appt.status = 'Completed'

        # Create or update treatment
        treatment = appt.treatment
        if not treatment:
            treatment = Treatment(appointment_id=appt.id, diagnosis=diagnosis or 'No diagnosis provided')
            db.session.add(treatment)
        treatment.diagnosis = diagnosis or treatment.diagnosis
        treatment.prescription = prescription or treatment.prescription
        treatment.medicines = medicines or treatment.medicines
        treatment.notes = notes or treatment.notes

        # Optionally add a medical record entry (e.g., test/result)
        record_type = sanitize_input(request.form.get('record_type'))
        record_title = sanitize_input(request.form.get('record_title'))
        record_description = sanitize_input(request.form.get('record_description'))
        if record_type and record_title:
            mr = MedicalRecord(patient_id=appt.patient_id, record_type=record_type, title=record_title, description=record_description)
            db.session.add(mr)

        db.session.commit()
        flash('Patient history updated successfully.', 'success')
        return redirect(url_for('doctor_dashboard'))

    return render_template('doctor/update_patient_history.html', appointment=appt, patient=appt.patient)


@app.route('/doctor/patient/<int:patient_id>/history')
@role_required('Doctor')
def doctor_view_patient_history(patient_id):
    # Doctors can view full medical history of a patient
    patient = Patient.query.get_or_404(patient_id)
    medical_records = patient.medical_records.order_by(MedicalRecord.recorded_date.desc()).all()
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient.id).order_by(Treatment.created_at.desc()).all()
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.appointment_date.desc()).all()
    return render_template('doctor/patient_history.html', patient=patient, medical_records=medical_records, treatments=treatments, appointments=appointments)


@app.route('/doctor/availability', methods=['GET', 'POST'])
@role_required('Doctor')
def doctor_manage_availability():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    today = date.today()
    end_date = today + timedelta(days=7)

    if request.method == 'POST':
        # Expected form: date, start_time, end_time, is_available
        slot_date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        is_available = bool(request.form.get('is_available'))
        try:
            slot_date_obj = datetime.strptime(slot_date, '%Y-%m-%d').date()
            start_time_obj = datetime.strptime(start_time, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time, '%H:%M').time()
        except Exception:
            flash('Invalid date/time format.', 'danger')
            return redirect(url_for('doctor_manage_availability'))

        # Find existing slot or create
        slot = DoctorAvailability.query.filter_by(doctor_id=doctor.id, date=slot_date_obj).first()
        if not slot:
            slot = DoctorAvailability(doctor_id=doctor.id, date=slot_date_obj)
            db.session.add(slot)

        slot.start_time = start_time_obj
        slot.end_time = end_time_obj
        slot.is_available = is_available
        db.session.commit()
        flash('Availability updated.', 'success')
        return redirect(url_for('doctor_manage_availability'))

    # Show next 7 days availability
    slots = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= end_date
    ).order_by(DoctorAvailability.date.asc()).all()

    # Build a map of date -> slot for easy template rendering
    slots_map = {s.date: s for s in slots}
    days = [(today + timedelta(days=i)) for i in range(8)]
    return render_template('doctor/manage_availability.html', doctor=doctor, days=days, slots_map=slots_map)


# --------------------- Patient Dashboard ---------------------
@app.route('/patient/dashboard')
@role_required('Patient')
def patient_dashboard():
    # Show departments, upcoming and past appointments for the logged-in patient
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    departments = Department.query.all()

    today = date.today()
    upcoming = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_date >= today,
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date.asc()).all()
    past = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_date < today
    ).order_by(Appointment.appointment_date.desc()).all()

    # Build doctor availability for next 7 days to show on dashboard
    end_date = today + timedelta(days=7)
    doctors = Doctor.query.join(User).all()
    doctors_availability = []
    for d in doctors:
        slots = DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == d.id,
            DoctorAvailability.date >= today,
            DoctorAvailability.date <= end_date,
            DoctorAvailability.is_available == True
        ).order_by(DoctorAvailability.date.asc()).all()
        doctors_availability.append({'doctor': d, 'slots': slots})

    return render_template('patient/patient_dashboard.html', departments=departments, upcoming=upcoming, past=past, doctors_availability=doctors_availability)


@app.route('/patient/profile', methods=['GET', 'POST'])
@role_required('Patient')
def patient_profile():
    user = User.query.get_or_404(current_user.id)
    patient = Patient.query.filter_by(user_id=user.id).first()
    if request.method == 'POST':
        user.first_name = sanitize_input(request.form.get('first_name'))
        user.last_name = sanitize_input(request.form.get('last_name'))
        user.phone = sanitize_input(request.form.get('phone'))
        user.address = sanitize_input(request.form.get('address'))
        dob_str = request.form.get('date_of_birth')
        if dob_str:
            try:
                patient.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except Exception:
                # Ignore invalid date formats and keep existing value
                pass
        patient.gender = sanitize_input(request.form.get('gender')) or patient.gender
        patient.blood_group = sanitize_input(request.form.get('blood_group')) or patient.blood_group
        patient.allergies = sanitize_input(request.form.get('allergies')) or patient.allergies
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('patient_profile'))

    return render_template('patient/profile.html', user=user, patient=patient)


@app.route('/patient/doctors')
@role_required('Patient')
def patient_doctors():
    # List doctors filtered by department or search query
    dept_id = request.args.get('department')
    q = request.args.get('q', '').strip()

    query = Doctor.query.join(User)
    if dept_id:
        query = query.filter(Doctor.department_id == int(dept_id))
    if q:
        like_q = f"%{q}%"
        query = query.filter(or_(User.first_name.ilike(like_q), User.last_name.ilike(like_q), Doctor.specialization.ilike(like_q)))

    doctors = query.all()
    departments = Department.query.all()
    return render_template('patient/doctors.html', doctors=doctors, departments=departments, q=q, dept_id=dept_id)


@app.route('/patient/doctor/<int:doctor_id>')
@role_required('Patient')
def patient_doctor_profile(doctor_id):
    # Show full doctor profile and next 7 days availability
    doctor = Doctor.query.get_or_404(doctor_id)
    today = date.today()
    end_date = today + timedelta(days=7)
    slots = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= end_date,
        DoctorAvailability.is_available == True
    ).order_by(DoctorAvailability.date.asc(), DoctorAvailability.start_time.asc()).all()

    return render_template('patient/doctor_profile.html', doctor=doctor, slots=slots)


@app.route('/patient/cancel/<int:appointment_id>', methods=['POST'])
@role_required('Patient')
def patient_cancel_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if appt.patient_id != patient.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('patient_dashboard'))
    appt.status = 'Cancelled'
    db.session.commit()
    flash('Appointment cancelled.', 'info')
    return redirect(url_for('patient_dashboard'))


@app.route('/patient/reschedule/<int:appointment_id>', methods=['GET', 'POST'])
@role_required('Patient')
def patient_reschedule_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if appt.patient_id != patient.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('patient_dashboard'))

    doctor = appt.doctor
    form = AppointmentForm()
    if form.validate_on_submit():
        new_date = form.appointment_date.data
        new_time = form.appointment_time.data

        if check_appointment_conflict(doctor.id, new_date, new_time, exclude_id=appt.id):
            flash('Selected slot is not available.', 'danger')
            return redirect(url_for('patient_reschedule_appointment', appointment_id=appointment_id))

        availability = DoctorAvailability.query.filter_by(doctor_id=doctor.id, date=new_date, is_available=True).first()
        if not availability or not (availability.start_time <= new_time <= availability.end_time):
            flash('Doctor not available at that time.', 'danger')
            return redirect(url_for('patient_reschedule_appointment', appointment_id=appointment_id))

        appt.appointment_date = new_date
        appt.appointment_time = new_time
        appt.status = 'Booked'
        db.session.commit()
        flash('Appointment rescheduled.', 'success')
        return redirect(url_for('patient_dashboard'))

    return render_template('patient/reschedule.html', appointment=appt, form=form)


@app.route('/patient/history')
@role_required('Patient')
def patient_history():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    medical_records = patient.medical_records.order_by(MedicalRecord.recorded_date.desc()).all()
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient.id).order_by(Treatment.created_at.desc()).all()
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.appointment_date.desc()).all()
    return render_template('patient/history.html', patient=patient, medical_records=medical_records, treatments=treatments, appointments=appointments)


@app.route('/patient/book/<int:doctor_id>', methods=['GET', 'POST'])
@role_required('Patient')
def patient_book_appointment(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    form = AppointmentForm()

    # If a specific date is passed from the dashboard (e.g., ?date=2025-12-01),
    # pre-fill the appointment_date field on initial GET so the patient
    # doesn't have to reselect it.
    prefill_date = request.args.get('date')
    if request.method == 'GET' and prefill_date:
        try:
            form.appointment_date.data = datetime.strptime(prefill_date, '%Y-%m-%d').date()
        except Exception:
            # Ignore invalid date formats and fall back to default behavior
            pass

    if form.validate_on_submit():
        appointment_date = form.appointment_date.data
        appointment_time = form.appointment_time.data
        reason = sanitize_input(form.reason.data)

        if check_appointment_conflict(doctor_id, appointment_date, appointment_time):
            flash('This time slot is already booked.', 'danger')
            return redirect(url_for('patient_book_appointment', doctor_id=doctor_id))

        availability = DoctorAvailability.query.filter_by(
            doctor_id=doctor_id,
            date=appointment_date,
            is_available=True
        ).first()

        if not availability:
            flash('Doctor not available on this date.', 'danger')
            return redirect(url_for('patient_book_appointment', doctor_id=doctor_id))

        if not (availability.start_time <= appointment_time <= availability.end_time):
            flash('Selected time is outside doctor availability.', 'danger')
            return redirect(url_for('patient_book_appointment', doctor_id=doctor_id))

        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
            status='Booked'
        )
        db.session.add(appointment)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('This time slot was just booked by someone else. Please choose another slot.', 'danger')
            return redirect(url_for('patient_book_appointment', doctor_id=doctor_id))

        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('patient_dashboard'))

    today = date.today()
    available_dates = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.date >= today,
        DoctorAvailability.is_available == True
    ).all()

    return render_template('patient/book_appointment.html', 
        doctor=doctor, 
        available_dates=available_dates,
        form=form
    )


# --------------------- Error Handlers ---------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# --------------------- Admin Setup ---------------------
def create_admin_and_roles():
    with app.app_context():
        db.create_all()
        roles_list = ['Admin', 'Doctor', 'Patient']
        for role_name in roles_list:
            if not Role.query.filter_by(name=role_name).first():
                db.session.add(Role(name=role_name))
        db.session.commit()

        admin_email = 'jannu@gmail.com'
        admin = User.query.filter_by(email=admin_email).first()
        admin_role = Role.query.filter_by(name='Admin').first()

        # Create or update admin
        if not admin:
            admin_password = generate_password_hash('admin123')
            admin = User(email=admin_email, password=admin_password,
                         first_name='Admin', last_name='User')
            admin.roles.append(admin_role)
            db.session.add(admin)
        elif admin_role not in admin.roles:
            admin.roles.append(admin_role)

        db.session.commit()
        print(f"✅ Admin ensured: {admin_email} / admin123")


# --------------------- Run App ---------------------
if __name__ == '__main__':
    create_admin_and_roles()
    app.run(debug=True, port=5001)
