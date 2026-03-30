// ═══════════════════════════════════════════════════════════════
// POWER GYM & POWER BOX — Layout Manager
// Inyecta Sidebar, TopBar y Footer de forma dinámica.
// Un solo archivo controla el diseño de TODAS las páginas.
// ═══════════════════════════════════════════════════════════════

// ── Theme (se ejecuta ANTES de renderizar para evitar flash) ─
(function initTheme() {
    const saved = localStorage.getItem('gym_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
})();

/**
 * Inyecta el layout completo (sidebar + topbar + wrapper) en el <body>.
 * @param {string} activePage — 'index','clientes','productos','historial','usuarios'
 */
function initLayout(activePage) {
    const links = [
        { href: 'index.html',      icon: 'bi-lightning-charge-fill', label: 'Ventas',    key: 'index' },
        { href: 'clientes.html',   icon: 'bi-people-fill',          label: 'Clientes',  key: 'clientes' },
        { href: 'productos.html',  icon: 'bi-box-seam-fill',        label: 'Productos', key: 'productos' },
        { href: 'historial.html',  icon: 'bi-clock-history',        label: 'Historial', key: 'historial' },
        { href: 'usuarios.html',   icon: 'bi-shield-lock-fill',     label: 'Usuarios',  key: 'usuarios', id: 'navUsuarios', hidden: true },
        { href: 'configuracion.html', icon: 'bi-gear-fill',           label: 'Configuración', key: 'configuracion', id: 'navConfiguracion', hidden: true },
    ];

    const navHTML = links.map(l => {
        const active = l.key === activePage ? ' active' : '';
        const id = l.id ? ` id="${l.id}"` : '';
        const hide = l.hidden ? ' style="display:none;"' : '';
        return `<a${id} href="${l.href}" class="sidebar-link${active}"${hide}><i class="bi ${l.icon}"></i> ${l.label}</a>`;
    }).join('\n            ');

    // ── Sede dinámica ──
    const sede = localStorage.getItem('sede_activa') || '';
    const esBox = sede === 'box';
    const sedeName = esBox ? 'POWER BOX' : 'POWER GYM';
    const sedeClass = esBox ? 'sede-box' : 'sede-gym';

    // ── Sidebar ──
    const sidebarHTML = `
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-brand-block">
            <a href="index.html" class="sidebar-brand">
                <img id="sidebar-logo" src="" alt="Logo" style="display:none;" class="w-full max-w-[140px] h-auto object-contain mx-auto mb-2">
            </a>
            <span class="sidebar-sede-label ${sedeClass}">${sedeName}</span>
        </div>
        <nav class="sidebar-nav">
            ${navHTML}
        </nav>
        <div class="sidebar-footer">&copy; 2026 POWER GYM &amp; BOX</div>
    </aside>`;

    // ── TopBar ──
    const topbarHTML = `
    <header class="topbar">
        <div class="topbar-left">
            <button class="topbar-hamburger" onclick="toggleSidebar()"><i class="bi bi-list"></i></button>
        </div>
        <div class="topbar-right">
            <button class="theme-toggle" onclick="toggleTheme()" title="Cambiar tema">
                <i class="bi bi-moon-fill" id="themeIcon"></i>
            </button>
            <div class="profile-capsule" id="profileCapsule" onclick="toggleProfileMenu()">
                <div class="profile-avatar" id="profileAvatar">?</div>
                <div class="profile-info">
                    <span class="profile-name" id="profileName">Cargando…</span>
                    <span class="profile-role" id="profileRole"></span>
                </div>
                <i class="bi bi-chevron-down profile-chevron" id="profileChevron"></i>
            </div>
            <div class="profile-dropdown" id="profileDropdown">
                <div class="profile-dropdown-header">
                    <div class="profile-avatar-lg" id="profileAvatarLg">?</div>
                    <div>
                        <p class="profile-dd-name" id="profileDdName">…</p>
                        <p class="profile-dd-role" id="profileDdRole">…</p>
                    </div>
                </div>
                <div class="profile-dropdown-divider"></div>
                <button class="profile-dropdown-item" onclick="cerrarSesion()">
                    <i class="bi bi-box-arrow-right"></i> Cerrar Sesión
                </button>
            </div>
        </div>
    </header>`;

    // Inyectar en el DOM
    const existingMain = document.querySelector('main.main-content, div.main-content');
    let mainEl;

    if (existingMain) {
        mainEl = existingMain;
        mainEl.insertAdjacentHTML('beforebegin', sidebarHTML + topbarHTML);
    } else {
        const bodyContent = document.body.innerHTML;
        document.body.innerHTML = '';
        document.body.insertAdjacentHTML('afterbegin', sidebarHTML + topbarHTML);
        mainEl = document.createElement('main');
        mainEl.className = 'main-content';
        mainEl.innerHTML = bodyContent;
        document.body.appendChild(mainEl);
    }

    // ── Footer ──
    if (!mainEl.querySelector('.footer-premium')) {
        mainEl.insertAdjacentHTML('beforeend', `
        <footer class="footer-premium">
            <p>&copy; 2026 POWER GYM &amp; BOX &nbsp;|&nbsp; El Triunfo, Ecuador &nbsp;|&nbsp; Gestión Profesional de Gimnasio</p>
        </footer>`);
    }

    // Icono de tema correcto
    const saved = localStorage.getItem('gym_theme') || 'dark';
    const icon = document.getElementById('themeIcon');
    if (icon) icon.className = saved === 'dark' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';

    // Cerrar dropdown al hacer click fuera
    document.addEventListener('click', function(e) {
        const capsule = document.getElementById('profileCapsule');
        const dropdown = document.getElementById('profileDropdown');
        if (capsule && dropdown && !capsule.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.remove('open');
            const chev = document.getElementById('profileChevron');
            if (chev) chev.classList.remove('rotated');
        }
    });

    // Cargar logo y favicon dinámicos desde la BD
    loadDynamicConfig();
}

// ── Profile Dropdown Toggle ─────────────────────────────────
function toggleProfileMenu() {
    const dd = document.getElementById('profileDropdown');
    const chev = document.getElementById('profileChevron');
    if (dd) dd.classList.toggle('open');
    if (chev) chev.classList.toggle('rotated');
}

// ── Theme Toggle ────────────────────────────────────────────
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('gym_theme', next);
    const icon = document.getElementById('themeIcon');
    if (icon) icon.className = next === 'dark' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
}

// ── Sidebar Toggle (responsive) ────────────────────────────
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
    document.getElementById('sidebarOverlay').classList.toggle('active');
}
