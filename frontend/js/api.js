// ═══════════════════════════════════════════════════════════════
// POWER GYM & POWER BOX — API & Session Module
// Centraliza la URL base, autenticación y guard de sesión.
// ═══════════════════════════════════════════════════════════════

const API_BASE_URL = 'https://api-facturacion-gym.onrender.com';

// ── Session Guard ───────────────────────────────────────────
const GYM_TOKEN = localStorage.getItem('gym_token');

function authHeaders(extra = {}) {
    return { 'Authorization': `Bearer ${GYM_TOKEN}`, ...extra };
}

/**
 * Verifica token + sede activa. Redirige a login si faltan.
 * Carga nombre de usuario en topbar y muestra enlace "Usuarios" si es admin.
 * @param {Object} opts
 * @param {boolean} opts.requireAdmin  — si true, redirige a index.html si no es admin
 * @param {Function} opts.onAdmin      — callback que se ejecuta si el usuario es admin
 */
function initSessionGuard(opts = {}) {
    if (!GYM_TOKEN) { window.location.href = 'login.html'; return; }
    if (!localStorage.getItem('sede_activa')) { window.location.href = 'login.html'; return; }

    // Sede indicator
    const sede = localStorage.getItem('sede_activa') || 'gym';
    const sedeEl = document.getElementById('sedeIndicator');
    if (sedeEl) sedeEl.textContent = '📍 ' + (sede === 'box' ? 'POWER BOX' : 'POWER GYM');

    // Verificar token con el backend
    fetch(`${API_BASE_URL}/api/v1/auth/me`, { headers: authHeaders() })
        .then(r => {
            if (!r.ok) {
                localStorage.removeItem('gym_token');
                localStorage.removeItem('gym_user');
                window.location.href = 'login.html';
                throw new Error('Token inválido');
            }
            return r.json();
        })
        .then(user => {
            if (!user) return;

            // Mostrar nombre de usuario
            const rol = user.rol ? user.rol.charAt(0).toUpperCase() + user.rol.slice(1) : '';
            const userEl = document.getElementById('userIndicator');
            if (userEl) userEl.textContent = `👤 ${user.nombre_completo} (${rol})`;

            // Enlace "Usuarios" solo para admin
            if (user.rol === 'admin') {
                const nu = document.getElementById('navUsuarios');
                if (nu) nu.style.display = 'flex';
                if (typeof opts.onAdmin === 'function') opts.onAdmin(user);
            }

            // Protección admin-only
            if (opts.requireAdmin && user.rol !== 'admin') {
                alert('Acceso denegado: solo administradores pueden acceder a esta sección.');
                window.location.href = 'index.html';
            }
        })
        .catch(() => {});
}

// ── Cerrar Sesión ───────────────────────────────────────────
function cerrarSesion() {
    localStorage.removeItem('gym_token');
    localStorage.removeItem('gym_user');
    window.location.href = 'login.html';
}

// ── Toast Notifications ─────────────────────────────────────
function mostrarToast(mensaje, tipo = 'success') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = 'position:fixed;top:68px;right:16px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
        document.body.appendChild(container);
    }

    const isSuccess = tipo === 'success';
    const toast = document.createElement('div');
    toast.className = `toast-unified ${isSuccess ? 'toast-success' : 'toast-error'}`;
    toast.innerHTML = `
        <i class="bi ${isSuccess ? 'bi-check-circle-fill' : 'bi-exclamation-circle-fill'}"></i>
        <span style="flex:1;font-size:0.82rem;">${mensaje}</span>
        <button onclick="this.parentElement.remove()" style="background:none;border:none;opacity:0.5;cursor:pointer;color:inherit;font-size:0.9rem;">
            <i class="bi bi-x-lg"></i>
        </button>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}
