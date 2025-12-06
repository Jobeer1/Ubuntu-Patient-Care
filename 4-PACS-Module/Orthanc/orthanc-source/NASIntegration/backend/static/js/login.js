/* Login Page JavaScript - South African Medical Imaging System */

// Handle login form submission
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const userType = document.getElementById('userType').value;
    const messageDiv = document.getElementById('errorMessage');
    const loginBtn = document.querySelector('.login-btn');

    // Validation
    if (!username || !password || !userType) {
        showError('Please fill in all fields');
        return;
    }

    // Show loading state
    const originalText = loginBtn.textContent;
    loginBtn.textContent = '🔄 Logging in...';
    loginBtn.disabled = true;
    hideError();

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                password: password,
                user_type: userType
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Success - show success message and redirect
            showSuccess('✅ Login successful! Redirecting...');
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        } else {
            // Error - show message
            showError(`❌ ${data.message || 'Login failed'}`);
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('❌ Network error - please try again');
    } finally {
        // Reset button text and enable it
        loginBtn.textContent = originalText;
        loginBtn.disabled = false;
    }
}
// Show error message to user
function showError(message) {
    const messageDiv = document.getElementById('errorMessage');
    messageDiv.textContent = message;
    messageDiv.style.display = 'block';
}

// Show success message to user
function showSuccess(message) {
    const messageDiv = document.getElementById('errorMessage');
    messageDiv.textContent = message;
    messageDiv.style.display = 'block';
    messageDiv.style.background = '#c6f6d5';
    messageDiv.style.color = '#22543d';
}

// Hide error message
function hideError() {
    const messageDiv = document.getElementById('errorMessage');
    messageDiv.style.display = 'none';
    messageDiv.style.background = '#fed7d7';
    messageDiv.style.color = '#c53030';
}

// Auto-fill demo credentials when user type changes
function handleUserTypeChange() {
    const userType = document.getElementById('userType').value;
    const usernameField = document.getElementById('username');
    const passwordField = document.getElementById('password');
    
    if (userType === 'admin') {
        usernameField.value = 'admin';
        passwordField.value = 'admin';
    } else if (userType === 'doctor') {
        usernameField.value = 'doctor';
        passwordField.value = 'doctor';
    } else if (userType === 'user') {
        usernameField.value = 'user';
        passwordField.value = 'user';
    } else {
        usernameField.value = '';
        passwordField.value = '';
    }
}

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set up form submission handler
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Set up user type change handler
    const userTypeSelect = document.getElementById('userType');
    if (userTypeSelect) {
        userTypeSelect.addEventListener('change', handleUserTypeChange);
    }
    
    // Focus on username field
    const usernameField = document.getElementById('username');
    if (usernameField) {
        usernameField.focus();
    }
});
