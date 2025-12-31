// static/js/validation.js
function validateDoctorForm() {
    const form = document.getElementById('doctorForm');
    const email = document.getElementById('email');
    const phone = document.getElementById('phone');
    const license = document.getElementById('license_number');

    // Email validation
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(email.value)) {
        alert('Please enter a valid email address');
        return false;
    }
    // Phone validation
    const phonePattern = /^\d{10,15}$/;
    if (!phonePattern.test(phone.value)) {
        alert('Phone number must be 10-15 digits');
        return false;
    }
    return true;
}