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
 * Debe llamarse al inicio del <script> de cada página.
 *
 * @param {string} activePage — Nombre del archivo activo: 'index','clientes','productos','historial','usuarios'
 */
function initLayout(activePage) {
    const links = [
        { href: 'index.html',      icon: 'bi-lightning-charge-fill', label: 'Ventas',    key: 'index' },
        { href: 'clientes.html',   icon: 'bi-people-fill',          label: 'Clientes',  key: 'clientes' },
        { href: 'productos.html',  icon: 'bi-box-seam-fill',        label: 'Productos', key: 'productos' },
        { href: 'historial.html',  icon: 'bi-clock-history',        label: 'Historial', key: 'historial' },
        { href: 'usuarios.html',   icon: 'bi-shield-lock-fill',     label: 'Usuarios',  key: 'usuarios', id: 'navUsuarios', hidden: true },
    ];

    const navHTML = links.map(l => {
        const active = l.key === activePage ? ' active' : '';
        const id = l.id ? ` id="${l.id}"` : '';
        const hide = l.hidden ? ' style="display:none;"' : '';
        return `<a${id} href="${l.href}" class="sidebar-link${active}"${hide}><i class="bi ${l.icon}"></i> ${l.label}</a>`;
    }).join('\n            ');

    // ── Sidebar ──
    const sidebarHTML = `
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
    <aside class="sidebar" id="sidebar">
        <a href="index.html" class="sidebar-brand">
            <img src="https://cdn-icons-png.flaticon.com/512/3003/3003984.png" alt="Logo">
            <span>POWER GYM &amp; POWER BOX</span>
        </a>
        <nav class="sidebar-nav">
            ${navHTML}
        </nav>
        <div class="sidebar-footer">&copy; 2026 POWER GYM &amp; POWER BOX</div>
    </aside>`;

    // ── TopBar ──
    const topbarHTML = `
    <header class="topbar">
        <div class="topbar-sede">
            <button class="topbar-hamburger" onclick="toggleSidebar()"><i class="bi bi-list"></i></button>
            <span id="sedeIndicator">📍 Sede: —</span>
        </div>
        <div class="topbar-right">
            <button class="theme-toggle" onclick="toggleTheme()" title="Cambiar tema">
                <i class="bi bi-moon-fill" id="themeIcon"></i>
            </button>
            <span id="userIndicator" class="topbar-user">👤 Cargando...</span>
            <button onclick="cerrarSesion()" class="topbar-logout"><i class="bi bi-box-arrow-right"></i> Cerrar Sesión</button>
        </div>
    </header>`;

    // Crear contenedor <main> si no existe
    const existingMain = document.querySelector('main.main-content, div.main-content');
    let mainEl;

    if (existingMain) {
        // El contenido ya está dentro de un main-content, solo inyectamos sidebar+topbar antes
        mainEl = existingMain;
        mainEl.insertAdjacentHTML('beforebegin', sidebarHTML + topbarHTML);
    } else {
        // Envolver todo el body content en <main class="main-content">
        const bodyContent = document.body.innerHTML;
        document.body.innerHTML = '';
        document.body.insertAdjacentHTML('afterbegin', sidebarHTML + topbarHTML);
        mainEl = document.createElement('main');
        mainEl.className = 'main-content';
        mainEl.innerHTML = bodyContent;
        document.body.appendChild(mainEl);
    }

    // ── Footer (se añade al final del main) ──
    if (!mainEl.querySelector('.footer-premium')) {
        mainEl.insertAdjacentHTML('beforeend', `
        <footer class="footer-premium">
            <p>&copy; 2026 POWER GYM &amp; POWER BOX &nbsp;|&nbsp; El Triunfo, Ecuador &nbsp;|&nbsp; Gestión Profesional de Gimnasio</p>
        </footer>`);
    }

    // Establecer icono de tema correcto
    const saved = localStorage.getItem('gym_theme') || 'dark';
    const icon = document.getElementById('themeIcon');
    if (icon) icon.className = saved === 'dark' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
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
