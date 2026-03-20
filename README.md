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

## Premium Responsive Experience

The Hospital Management System has been fully optimized for a **seamless multi-device experience**, ensuring clinicians and patients can access critical data on any screen size.

- **Multi-Device Support**: Specially tailored layouts for **mobile phones, tablets, and laptops**.
- **Responsive Dashboards**: All Admin, Doctor, and Patient dashboards now feature **horizontal-scroll enabled data tables** and stacking grid layouts.
- **Mobile Navigation**: A dedicated slide-out mobile menu for the landing page and a standard Bootstrap collapse menu for the internal application.
- **Glassmorphism & 3D Effects**: Maintained high-end visual fidelity (glassmorphism, 3D tilt, magnetic buttons) while ensuring performance on mobile browsers.
- **Touch-Friendly UI**: Larger hit targets for buttons and interactive elements to improve usability on touchscreens.

## Technologies

- Backend: Flask
- Frontend: Jinja2 templates, Vanilla CSS3 (Custom Design System), HTML5
- Database: SQLite (via SQLAlchemy / Flask‑SQLAlchemy)
- Authentication: Flask‑Login
- Forms & validation: Flask‑WTF
- Interactivity: IntersectionObserver API, custom CSS Keyframe animations, magnetic logic.

## Database Schema (High Level)

- `user` with many‑to‑many `role`
- `admin`, `doctor`, `patient` profiles (one‑to‑one with `user`)
- `department` (one‑to‑many with `doctor`)
- `appointment` (many‑to‑one with `doctor` and `patient`)
- `treatment` (one‑to‑one with `appointment`)
- `doctor_availability` (one‑to‑many with `doctor`)
- `medical_record` (one‑to‑many with `patient`)
