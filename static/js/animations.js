

function animateCountUp(element, target, duration = 1000, decimals = 0) {
    if (!element) return;

    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = start + (target - start) * eased;
        element.textContent = current.toFixed(decimals);
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

function fadeInUp(element, delay = 0, duration = 600) {
    if (!element) return;

    element.style.opacity = '0';
    element.style.transform = 'translateY(30px)';
    element.style.transition = `opacity ${duration}ms cubic-bezier(0.4, 0, 0.2, 1), transform ${duration}ms cubic-bezier(0.4, 0, 0.2, 1)`;
    element.style.transitionDelay = `${delay}ms`;

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        });
    });
}

function staggerFadeIn(elements, staggerDelay = 100) {
    if (!elements || elements.length === 0) return;

    elements.forEach((el, index) => {
        fadeInUp(el, index * staggerDelay);
    });
}

function setAQITheme(aqiValue) {
    const root = document.documentElement;
    let color, glow;

    if (aqiValue === null || aqiValue === undefined) {
        color = '#94a3b8';
        glow = 'rgba(148, 163, 184, 0.3)';
    } else if (aqiValue <= 50) {
        color = '#10b981';
        glow = 'rgba(16, 185, 129, 0.3)';
    } else if (aqiValue <= 100) {
        color = '#eab308';
        glow = 'rgba(234, 179, 8, 0.3)';
    } else if (aqiValue <= 200) {
        color = '#f97316';
        glow = 'rgba(249, 115, 22, 0.3)';
    } else if (aqiValue <= 300) {
        color = '#ef4444';
        glow = 'rgba(239, 68, 68, 0.3)';
    } else if (aqiValue <= 400) {
        color = '#a855f7';
        glow = 'rgba(168, 85, 247, 0.3)';
    } else {
        color = '#7e0023';
        glow = 'rgba(126, 0, 35, 0.3)';
    }

    root.style.setProperty('--aqi-color', color);
    root.style.setProperty('--aqi-glow', glow);
}

function smoothValueUpdate(element, newValue, decimals = 1) {
    if (!element) return;

    const currentValue = parseFloat(element.textContent) || 0;
    const targetValue = parseFloat(newValue) || 0;
    const startTime = performance.now();
    const duration = 800;

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = currentValue + (targetValue - currentValue) * eased;
        element.textContent = current.toFixed(decimals);
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

function initScrollReveal() {
    const elements = document.querySelectorAll('[data-reveal]');
    if (elements.length === 0) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const delay = el.dataset.revealDelay || 0;
                fadeInUp(el, parseInt(delay));
                observer.unobserve(el);
            }
        });
    }, { threshold: 0.1 });

    elements.forEach(el => {
        el.style.opacity = '0';
        observer.observe(el);
    });
}

function showLiquidLoading(show) {
    const indicator = document.getElementById('loadingIndicator');
    if (!indicator) return;

    if (show) {
        indicator.style.display = 'block';
        indicator.innerHTML = `
            <div class="liquid-spinner"></div>
            <p>Fetching air quality data...</p>
        `;
    } else {
        indicator.style.display = 'none';
    }
}

function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#06b6d4'
    };

    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: rgba(15, 23, 42, 0.95);
        backdrop-filter: blur(20px);
        border: 1px solid ${colors[type] || colors.info};
        border-radius: 12px;
        color: #f1f5f9;
        font-size: 0.9rem;
        font-weight: 500;
        z-index: 9999;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        animation: toastIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        max-width: 350px;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

const style = document.createElement('style');
style.textContent = `
    @keyframes toastIn {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    @keyframes toastOut {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(style);

document.addEventListener('DOMContentLoaded', function() {
    initScrollReveal();
});
