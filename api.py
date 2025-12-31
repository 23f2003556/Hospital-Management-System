from flask import Blueprint, request, jsonify, current_app
from models import db, User, Doctor, Patient, Appointment, Treatment, Department
from functools import wraps
from flask_login import current_user
from datetime import datetime


def check_appointment_conflict(doctor_id, appointment_date, appointment_time, exclude_id=None):
    from models import Appointment
    query = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.appointment_time == appointment_time,
        Appointment.status == 'Booked'
    )
    if exclude_id:
        query = query.filter(Appointment.id != exclude_id)
    return query.first() is not None

api = Blueprint('api', __name__, url_prefix='/api')


def role_required_api(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            if not any(r.name in roles for r in current_user.roles):
                return jsonify({'error': 'Forbidden'}), 403
            return f(*args, **kwargs)
        return decorated
    return wrapper


# Serializers
def doctor_to_dict(doc):
    return {
        'id': doc.id,
        'user_id': doc.user_id,
        'first_name': doc.user.first_name,
        'last_name': doc.user.last_name,
        'specialization': doc.specialization,
        'department_id': doc.department_id,
        'qualification': doc.qualification,
        'experience_years': doc.experience_years,
        'consultation_fee': doc.consultation_fee
    }


def patient_to_dict(p):
    return {
        'id': p.id,
        'user_id': p.user_id,
        'first_name': p.user.first_name,
        'last_name': p.user.last_name,
        'date_of_birth': p.date_of_birth.isoformat() if p.date_of_birth else None,
        'gender': p.gender,
        'blood_group': p.blood_group
    }


def appointment_to_dict(a):
    return {
        'id': a.id,
        'patient_id': a.patient_id,
        'doctor_id': a.doctor_id,
        'appointment_date': a.appointment_date.isoformat(),
        'appointment_time': a.appointment_time.strftime('%H:%M:%S'),
        'status': a.status,
        'reason': a.reason
    }


# Doctor endpoints
@api.route('/doctors', methods=['GET'])
def api_get_doctors():
    q = request.args.get('q', '').strip()
    query = Doctor.query.join(User)
    if q:
        like_q = f"%{q}%"
        query = query.filter((User.first_name.ilike(like_q)) | (User.last_name.ilike(like_q)) | (Doctor.specialization.ilike(like_q)))
    docs = query.all()
    return jsonify([doctor_to_dict(d) for d in docs])


@api.route('/doctors/<int:doctor_id>', methods=['GET'])
def api_get_doctor(doctor_id):
    d = Doctor.query.get_or_404(doctor_id)
    return jsonify(doctor_to_dict(d))


@api.route('/doctors', methods=['POST'])
@role_required_api('Admin')
def api_create_doctor():
    data = request.get_json() or {}
    # Minimal creation: admin will have created User first via UI; here we only create doctor profile
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    if Doctor.query.filter_by(user_id=user_id).first():
        return jsonify({'error': 'Doctor profile already exists for this user'}), 400
    doc = Doctor(
        user_id=user_id,
        department_id=data.get('department_id'),
        specialization=data.get('specialization'),
        qualification=data.get('qualification'),
        experience_years=data.get('experience_years') or 0,
        consultation_fee=data.get('consultation_fee') or 0.0
    )
    db.session.add(doc)
    db.session.commit()
    return jsonify(doctor_to_dict(doc)), 201


@api.route('/doctors/<int:doctor_id>', methods=['PUT'])
@role_required_api('Admin')
def api_update_doctor(doctor_id):
    d = Doctor.query.get_or_404(doctor_id)
    data = request.get_json() or {}
    d.specialization = data.get('specialization') or d.specialization
    d.qualification = data.get('qualification') or d.qualification
    d.experience_years = data.get('experience_years') or d.experience_years
    d.consultation_fee = data.get('consultation_fee') or d.consultation_fee
    db.session.commit()
    return jsonify(doctor_to_dict(d))


@api.route('/doctors/<int:doctor_id>', methods=['DELETE'])
@role_required_api('Admin')
def api_delete_doctor(doctor_id):
    d = Doctor.query.get_or_404(doctor_id)
    db.session.delete(d)
    db.session.commit()
    return jsonify({'status': 'deleted'})


# Patient endpoints
@api.route('/patients', methods=['GET'])
@role_required_api('Admin', 'Doctor')
def api_get_patients():
    q = request.args.get('q', '').strip()
    query = Patient.query.join(User)
    if q:
        like_q = f"%{q}%"
        query = query.filter((User.first_name.ilike(like_q)) | (User.last_name.ilike(like_q)) | (User.phone.ilike(like_q)))
    patients = query.all()
    return jsonify([patient_to_dict(p) for p in patients])


@api.route('/patients/<int:patient_id>', methods=['GET'])
@role_required_api('Admin', 'Doctor')
def api_get_patient(patient_id):
    p = Patient.query.get_or_404(patient_id)
    return jsonify(patient_to_dict(p))


@api.route('/patients/<int:patient_id>/history', methods=['GET'])
@role_required_api('Admin', 'Doctor')
def api_get_patient_history(patient_id):
    p = Patient.query.get_or_404(patient_id)
    # treatments and appointments
    appts = Appointment.query.filter_by(patient_id=p.id).all()
    treatments = []
    for a in appts:
        if a.treatment:
            treatments.append({
                'appointment_id': a.id,
                'diagnosis': a.treatment.diagnosis,
                'prescription': a.treatment.prescription,
                'medicines': a.treatment.medicines
            })
    return jsonify({'appointments': [appointment_to_dict(a) for a in appts], 'treatments': treatments})


# Appointment endpoints
@api.route('/appointments', methods=['GET'])
def api_get_appointments():
    # Public: allow filtering
    doctor_id = request.args.get('doctor_id')
    patient_id = request.args.get('patient_id')
    status = request.args.get('status')
    query = Appointment.query
    if doctor_id:
        query = query.filter_by(doctor_id=int(doctor_id))
    if patient_id:
        query = query.filter_by(patient_id=int(patient_id))
    if status:
        query = query.filter_by(status=status)
    appts = query.order_by(Appointment.appointment_date.desc()).all()
    return jsonify([appointment_to_dict(a) for a in appts])


@api.route('/appointments', methods=['POST'])
@role_required_api('Patient')
def api_create_appointment():
    data = request.get_json() or {}
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    doctor_id = data.get('doctor_id')
    if not doctor_id:
        return jsonify({'error': 'doctor_id required'}), 400
    appt_date = data.get('appointment_date')
    appt_time = data.get('appointment_time')
    try:
        appt_date_obj = datetime.fromisoformat(appt_date).date()
        appt_time_obj = datetime.strptime(appt_time, '%H:%M').time()
    except Exception:
        return jsonify({'error': 'Invalid date/time format'}), 400

    # Check availability
    from models import DoctorAvailability
    availability = DoctorAvailability.query.filter_by(doctor_id=doctor_id, date=appt_date_obj, is_available=True).first()
    if not availability or not (availability.start_time <= appt_time_obj <= availability.end_time):
        return jsonify({'error': 'Doctor not available at that time'}), 400

    if check_appointment_conflict(doctor_id, appt_date_obj, appt_time_obj):
        return jsonify({'error': 'Time slot already booked'}), 409

    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor_id,
        appointment_date=appt_date_obj,
        appointment_time=appt_time_obj,
        reason=data.get('reason'),
        status='Booked'
    )
    db.session.add(appt)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Could not create appointment', 'detail': str(e)}), 500

    return jsonify(appointment_to_dict(appt)), 201


@api.route('/appointments/<int:appt_id>', methods=['PUT'])
@role_required_api('Patient')
def api_update_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if appt.patient_id != patient.id:
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json() or {}
    # allow reschedule
    if 'appointment_date' in data and 'appointment_time' in data:
        try:
            new_date = datetime.fromisoformat(data.get('appointment_date')).date()
            new_time = datetime.strptime(data.get('appointment_time'), '%H:%M').time()
        except Exception:
            return jsonify({'error': 'Invalid date/time'}), 400
        if check_appointment_conflict(appt.doctor_id, new_date, new_time, exclude_id=appt.id):
            return jsonify({'error': 'Time slot not available'}), 409
        appt.appointment_date = new_date
        appt.appointment_time = new_time
        appt.status = 'Booked'
    db.session.commit()
    return jsonify(appointment_to_dict(appt))


@api.route('/appointments/<int:appt_id>', methods=['DELETE'])
@role_required_api('Patient')
def api_delete_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if appt.patient_id != patient.id:
        return jsonify({'error': 'Forbidden'}), 403
    appt.status = 'Cancelled'
    db.session.commit()
    return jsonify({'status': 'cancelled'})
