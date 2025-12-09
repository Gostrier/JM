document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    const currentTheme = localStorage.getItem('theme');

    if (currentTheme) {
        body.classList.add(currentTheme);
        if (currentTheme === 'dark-theme') {
            themeToggle.checked = true;
        }
    } else {
        // Default to light theme if no preference is found
        body.classList.remove('dark-theme');
    }

    if (themeToggle) {
        themeToggle.addEventListener('change', () => {
            if (themeToggle.checked) {
                body.classList.add('dark-theme');
                localStorage.setItem('theme', 'dark-theme');
            } else {
                body.classList.remove('dark-theme');
                localStorage.setItem('theme', 'light-theme');
            }
        });
    }
});