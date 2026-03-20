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

## Premium Landing Experience

The landing page has been re-engineered for a **500-bed Indian Multespecialty Hospital** context, focusing on high-impact facility-level metrics and premium UX:

-   **Hospital-Specific Narrative**: Updated with realistic 500-bed facility data (e.g., **15k+ daily physical files**, **22-min emergency retrieval delays**, etc.).
-   **Vertical Flow Thread**: A subtle gradient "thread" that visually connects all sections, creating a seamless storytelling journey.
-   **Premium Scroll Mouse**: A custom-animated 3D mouse icon replacing generic indicators.
-   **Facility-Level Impact**: Displays projected annual returns like **3,500+ weekly clinician hours saved** and **₹1.8 Cr annual recovery**.
-   **Fully Responsive**: Optimized for modern aesthetics with glassmorphism, 3D tilt effects, and magnetic interactions.

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
