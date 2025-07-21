// Main JavaScript file for Metal History Knowledge Graph

// HTMX configuration
document.body.addEventListener('htmx:configRequest', (event) => {
    // Add any custom headers if needed
});

// Handle HTMX errors
document.body.addEventListener('htmx:responseError', (event) => {
    console.error('HTMX request failed:', event.detail);
    // Could show user-friendly error message
});

// Dark mode toggle (if needed later)
function toggleDarkMode() {
    document.documentElement.classList.toggle('dark');
    localStorage.setItem('darkMode', document.documentElement.classList.contains('dark'));
}

// Initialize dark mode based on user preference
if (localStorage.getItem('darkMode') === 'true') {
    document.documentElement.classList.add('dark');
}