// Main JS for Dashboard

document.addEventListener('DOMContentLoaded', function() {
    console.log('AI Teleradiology Dashboard Loaded');
    
    // Poll for stats updates every 30 seconds
    setInterval(updateStats, 30000);
});

function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update DOM elements if they existed with specific IDs
            // For now, just log
            console.log('Stats updated:', data);
        })
        .catch(error => console.error('Error fetching stats:', error));
}
