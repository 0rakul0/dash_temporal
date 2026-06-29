const sharedIconSvg = {
  home: `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.5V20h13V9.5"/><path d="M10 20v-6h4v6"/></svg>`,
  "users-plus": `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><path d="M15 19c0-2.8-2.6-5-6-5s-6 2.2-6 5"/><circle cx="9" cy="8" r="3.5"/><path d="M19 8v6"/><path d="M16 11h6"/></svg>`,
  "user-minus": `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><path d="M15 19c0-2.8-2.6-5-6-5s-6 2.2-6 5"/><circle cx="9" cy="8" r="3.5"/><path d="M16 11h6"/></svg>`,
  building: `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><path d="M4 20V4h10v16"/><path d="M14 20v-9h6v9"/><path d="M8 8h2"/><path d="M8 12h2"/><path d="M8 16h2"/><path d="M17 14h1"/><path d="M17 17h1"/></svg>`,
  users: `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><circle cx="8" cy="8" r="3"/><circle cx="16.5" cy="9" r="2.5"/><path d="M2.5 19c0-2.8 2.6-5 5.5-5s5.5 2.2 5.5 5"/><path d="M13 18.5c.5-1.8 2.1-3.2 4.3-3.2 2.4 0 4.2 1.4 4.7 3.2"/></svg>`,
  scale: `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><path d="M12 4v16"/><path d="M6 8h12"/><path d="M4 8l-2 4h4l-2-4Z"/><path d="M20 8l-2 4h4l-2-4Z"/><path d="M8 20h8"/></svg>`,
  timeline: `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><path d="M6 6h12"/><path d="M6 12h7"/><path d="M6 18h10"/><circle cx="17" cy="12" r="2"/></svg>`,
  file: `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z"/><path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h6"/></svg>`,
  download: `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 21h16"/></svg>`,
  bell: `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><path d="M6 9a6 6 0 1 1 12 0c0 6 2 7 2 7H4s2-1 2-7"/><path d="M10 20a2 2 0 0 0 4 0"/></svg>`,
  info: `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><circle cx="12" cy="12" r="9"/><path d="M12 10v6"/><path d="M12 7h.01"/></svg>`,
  calendar: `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4"/><path d="M8 3v4"/><path d="M3 10h18"/></svg>`,
  refresh: `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg>`,
};

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-icon]").forEach((node) => {
    const key = node.dataset.icon;
    node.innerHTML = sharedIconSvg[key] || "";
  });

  const sidebar = document.getElementById("sidebar");
  const menuButtons = [document.getElementById("menu-toggle"), document.getElementById("mobile-menu")].filter(Boolean);

  menuButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      sidebar.classList.toggle("is-open");
    });
  });
});
