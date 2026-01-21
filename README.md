# Hospital Management System

A role-based hospital management web application for handling patient registrations, doctor schedules, appointment booking, and treatment records.

## Core Features

### Admin
- Dashboard with totals and stats (doctors, patients, appointments, pending bookings)
- Predefined admin user created programmatically (no admin self‑registration)
- Add, edit, deactivate/activate, and safely delete doctors and patients
- View all appointments with filters for status and time (upcoming / past)
- Search doctors by name or specialization
- Search patients by name, ID, or contact number
- View full patient history (appointments, treatments, medical records)

### Doctor
- Dedicated doctor dashboard
  - Today’s appointments
  - Upcoming week’s appointments
  - List of assigned patients
- Mark appointments as **Completed** or **Cancelled** (with status validation)
- Provide 7‑day availability and update time slots
- Add/update treatment details for each visit
  - Diagnosis, prescriptions, medicines, notes
  - Follow‑up required flag and date
- View complete medical history for any assigned patient

### Patient
- Self registration and login
- Patient dashboard showing:
  - All departments/specializations
  - Doctors’ availability for the next 7 days
  - Upcoming appointments with cancel option
  - Past appointments with diagnosis summary
- Quick doctor search by name/specialization and department
- View doctor profiles and availability
- Book appointments with doctors (respecting availability and conflicts)
- Reschedule or cancel booked appointments
- Update own profile (contact details, DOB, gender, blood group, allergies, etc.)
- View full personal history: appointments, treatments, and medical records


## Default Login

- Admin: `jannu@gmail.com` / `admin123`
- Doctors: `dr.rajeev@hospital.test` and `dr.priya@hospital.test` / `doctor123`
- Patients: *None seeded by default*

## Technologies

- Backend: Flask
- Frontend: Jinja2 templates, Bootstrap 5, HTML5, CSS3
- Database: SQLite (via SQLAlchemy / Flask‑SQLAlchemy)
- Authentication: Flask‑Login
- Forms & validation: Flask‑WTF

## Database Schema (High Level)

- `user` with many‑to‑many `role`
- `admin`, `doctor`, `patient` profiles (one‑to‑one with `user`)
- `department` (one‑to‑many with `doctor`)
- `appointment` (many‑to‑one with `doctor` and `patient`)
- `treatment` (one‑to‑one with `appointment`)
- `doctor_availability` (one‑to‑many with `doctor`)
- `medical_record` (one‑to‑many with `patient`)
