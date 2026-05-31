'use strict';

// ─── CSRF Token ───────────────────────────────────────
function getCsrf() {
  const c = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
  return c ? c.trim().split('=')[1] : '';
}

// ─── Bouton retour en haut ────────────────────────────
const btnTop = document.getElementById('btnTop');
if (btnTop) {
  window.addEventListener('scroll', () => {
    btnTop.style.display = window.scrollY > 400 ? 'flex' : 'none';
  });
  btnTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

// ─── Fermeture auto des alertes ───────────────────────
document.querySelectorAll('.alert').forEach(alert => {
  setTimeout(() => {
    const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
    if (bsAlert) bsAlert.close();
  }, 5000);
});

// ─── Toast notifications ──────────────────────────────
function showToast(message, type = 'success') {
  const colors = {
    success: 'bg-success',
    error:   'bg-danger',
    warning: 'bg-warning text-dark',
    info:    'bg-primary'
  };
  const icons = {
    success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️'
  };

  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    container.style.cssText = 'position:fixed;top:80px;right:1rem;z-index:9999';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-white
                     ${colors[type]} border-0 show mb-2`;
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        ${icons[type]} ${message}
      </div>
      <button type="button"
              class="btn-close btn-close-white me-2 m-auto"
              onclick="this.closest('.toast').remove()">
      </button>
    </div>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ─── Toggle Favori (AJAX) ────────────────────────────
document.addEventListener('click', async function(e) {
  const btn = e.target.closest('.btn-favori');
  if (!btn) return;
  e.preventDefault();

  const logementId = btn.dataset.logementId;
  if (!logementId) return;

  try {
    const res = await fetch(`/logements/${logementId}/favori/`, {
      method:  'POST',
      headers: { 'X-CSRFToken': getCsrf() },
    });
    const data = await res.json();

    const icon = btn.querySelector('i');
    if (data.status === 'added') {
      if (icon) {
        icon.className = 'bi bi-heart-fill text-danger';
      }
      showToast('Ajouté aux favoris ❤️');
    } else {
      if (icon) {
        icon.className = 'bi bi-heart';
      }
      showToast('Retiré des favoris', 'info');
    }
  } catch(e) {
    showToast('Erreur réseau', 'error');
  }
});

// ─── Galerie photos (page détail) ────────────────────
const mainImg = document.getElementById('galleryMain');
if (mainImg) {
  document.querySelectorAll('.thumb-img').forEach(thumb => {
    thumb.addEventListener('click', () => {
      mainImg.src = thumb.src;
    });
  });
}

// ─── Notifications count live ─────────────────────────
async function updateNotifCount() {
  try {
    const res  = await fetch('/notifications/count/');
    const data = await res.json();
    const badge = document.querySelector('.notif-badge');
    if (badge) {
      badge.textContent  = data.count;
      badge.style.display = data.count > 0 ? '' : 'none';
    }
  } catch(e) {}
}

// ─── Init ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

  // Mettre à jour notifs toutes les 60s
  if (document.body.dataset.authenticated === 'true') {
    updateNotifCount();
    setInterval(updateNotifCount, 60000);
  }

  // Tooltips Bootstrap
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });

  // Animation cartes au scroll
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.opacity    = '1';
        e.target.style.transform  = 'translateY(0)';
        observer.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.card').forEach(card => {
    card.style.opacity    = '0';
    card.style.transform  = 'translateY(20px)';
    card.style.transition = 'opacity .4s ease, transform .4s ease';
    observer.observe(card);
  });

});

// ─── Export global ────────────────────────────────────
window.LCM = { showToast, getCsrf };