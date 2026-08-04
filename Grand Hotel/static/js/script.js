// Hotel Billing System - Clean JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.display = 'none';
        }, 5000);
    });
    
    // Highlight current page in navigation
    highlightCurrentPage();
    
    // Phone validation
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(input => {
        input.addEventListener('blur', function() {
            validatePhone(this);
        });
    });
    
    // Email validation
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateEmail(this);
        });
    });
    
    // Set minimum date for check-in to today
    const checkInInputs = document.querySelectorAll('input[name="check_in_date"]');
    checkInInputs.forEach(input => {
        const today = new Date().toISOString().split('T')[0];
        input.setAttribute('min', today);
    });
    
    // Set minimum date for check-out based on check-in
    const checkInDate = document.querySelector('input[name="check_in_date"]');
    const checkOutDate = document.querySelector('input[name="check_out_date"]');
    
    if (checkInDate && checkOutDate) {
        checkInDate.addEventListener('change', function() {
            checkOutDate.setAttribute('min', this.value);
            if (checkOutDate.value && checkOutDate.value < this.value) {
                checkOutDate.value = this.value;
            }
        });
    }
});

// Highlight current page in navigation
function highlightCurrentPage() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-menu a');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.style.background = 'rgba(255, 255, 255, 0.15)';
            link.style.color = 'white';
        }
    });
}

// Phone number validation
function validatePhone(input) {
    const phoneRegex = /^[0-9]{10}$/;
    if (!phoneRegex.test(input.value.replace(/\D/g, ''))) {
        input.setCustomValidity('Please enter a valid 10-digit phone number');
    } else {
        input.setCustomValidity('');
    }
}

// Email validation
function validateEmail(input) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (input.value && !emailRegex.test(input.value)) {
        input.setCustomValidity('Please enter a valid email address');
    } else {
        input.setCustomValidity('');
    }
}

// Format currency
function formatCurrency(amount) {
    return '₹' + parseFloat(amount).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Calculate number of days between dates
function calculateDays(startDate, endDate) {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end - start);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : 1;
}

// Table filtering function for search functionality
function filterTable(searchInputId, tableId) {
    const input = document.getElementById(searchInputId);
    const filter = input.value.toLowerCase().trim();
    const table = document.getElementById(tableId);
    const tbody = table.querySelector('tbody');
    const rows = tbody.getElementsByTagName('tr');
    
    // Loop through all table rows and hide those that don't match the search query
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const cells = row.getElementsByTagName('td');
        let found = false;
        
        // Search through all cells in the row
        for (let j = 0; j < cells.length; j++) {
            const cellText = cells[j].textContent || cells[j].innerText;
            if (cellText.toLowerCase().indexOf(filter) > -1) {
                found = true;
                break;
            }
        }
        
        // Show or hide the row based on whether a match was found
        if (found || filter === '') {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    }
}

// Confirm before submission
function confirmAction(message) {
    return confirm(message);
}
