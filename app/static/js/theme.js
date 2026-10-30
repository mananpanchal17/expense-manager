// Apply the saved theme before the page paints. Storage may be unavailable.
(() => {
  let theme = 'light';
  try { theme = localStorage.getItem('expense-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); } catch (_) {}
  document.documentElement.dataset.bsTheme = theme === 'dark' ? 'dark' : 'light';
})();
