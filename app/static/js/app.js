const toggle = document.getElementById('theme-toggle');
function updateToggle() {
  const dark = document.documentElement.dataset.bsTheme === 'dark';
  toggle.textContent = dark ? 'Light mode' : 'Dark mode';
  toggle.setAttribute('aria-pressed', String(dark));
}
if (toggle) {
  updateToggle();
  toggle.addEventListener('click', () => {
    const theme = document.documentElement.dataset.bsTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.bsTheme = theme;
    try { localStorage.setItem('expense-theme', theme); } catch (_) {}
    updateToggle();
    window.dispatchEvent(new Event('themechange'));
  });
}
// Confirmation is a convenience. Authorization and CSRF are enforced in Python.
document.querySelectorAll('form[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});
