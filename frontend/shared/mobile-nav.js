/**
 * Mobile Navigation Injection Script
 * Automatically adds a bottom navigation bar to all pages on mobile devices.
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('Mobile nav script starting...');

    // Inject always, use CSS to hide on desktop
    const navContainer = document.createElement('div');
    navContainer.id = 'mobile-bottom-nav';
    navContainer.className = 'mobile-nav';

    // Try to detect user role from existing page elements (more robust)
    let userRole = 'Scout';
    const possibleRoleSelectors = [
        'p.text-\\[10px\\].text-slate-500',
        'p.text-\\[10px\\]',
        '.uppercase.font-bold.tracking-tighter',
        'h1',
        'h2'
    ];

    for (const selector of possibleRoleSelectors) {
        // Try attribute first (most reliable)
        const roleFromAttr = document.body.getAttribute('data-user-role');
        if (roleFromAttr) {
            userRole = roleFromAttr;
            break;
        }

        const elements = document.querySelectorAll(selector);
        for (const el of elements) {
            if (el && el.textContent) {
                const text = el.textContent.trim();
                // Direct match
                if (['Admin', 'Head Scout', 'Scout', 'Pit Scout', 'Drive Team'].includes(text)) {
                    userRole = text;
                    break;
                }
                // Partial match for Admin/Head Scout in headers
                if (text.includes('Admin') || text.includes('Head Scout')) {
                    userRole = text.includes('Admin') ? 'Admin' : 'Head Scout';
                    break;
                }
            }
        }
        if (userRole !== 'Scout') break;
    }

    console.log('Detected user role:', userRole);

    const currentPath = window.location.pathname;

    const navItems = [
        { name: 'Home', icon: 'home', path: '/', regex: /^\/(dashboard|scout-dashboard|$)/ },
        { name: 'Teams', icon: 'groups', path: '/teams', regex: /^\/teams/ },
        { name: 'Schedule', icon: 'calendar_month', path: '/events', regex: /^\/events/ }
    ];

    // Add role-specific items
    if (userRole === 'Admin' || userRole === 'Head Scout') {
        // Only keep functional pages for admins
        navItems.push({ name: 'Admin', icon: 'manage_accounts', path: '/admin', regex: /^\/admin/ });
        navItems.push({ name: 'Pick List', icon: 'drag_indicator', path: '/picklist', regex: /^\/picklist/ });
        navItems.push({ name: 'Analytics', icon: 'analytics', path: '/analytics', regex: /^\/analytics/ });
    } else {
        navItems.push({ name: 'Profile', icon: 'person', path: '/profile', regex: /^\/profile/ });
    }

    navItems.forEach(item => {
        const link = document.createElement('a');
        link.href = item.path;
        link.className = 'mobile-nav-item';
        if (item.regex.test(currentPath)) {
            link.classList.add('active');
        }

        const icon = document.createElement('span');
        icon.className = 'material-symbols-outlined';
        icon.textContent = item.icon;

        const label = document.createElement('span');
        label.textContent = item.name;

        link.appendChild(icon);
        link.appendChild(label);
        navContainer.appendChild(link);
    });

    // Check if it already exists to avoid double injection
    if (!document.getElementById('mobile-bottom-nav')) {
        document.body.appendChild(navContainer);
        console.log('Mobile bottom nav injected.');

        // JS Fallback: Shift utility buttons up if they exist
        const shiftButtons = () => {
            if (window.innerWidth <= 768) {
                ['custom-language-selector', 'pwa-install-btn', 'pwa-offline-banner', 'pwa-sync-banner'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        el.style.setProperty('bottom', '95px', 'important');
                    }
                });
            }
        };

        shiftButtons();
        // Periodically check as some buttons (like install) are injected late
        setInterval(shiftButtons, 2000);

        // --- NEW: Header Hub Injection ---
        const injectHeaderHub = () => {
            const headerActions = document.querySelector('header .flex.items-center.gap-4.flex-1.justify-end');
            if (!headerActions || document.getElementById('mobile-header-hub')) return;

            const hubBtn = document.createElement('a');
            hubBtn.id = 'mobile-header-hub';
            // Route based on role
            const hubPath = (userRole === 'Admin' || userRole === 'Head Scout') ? '/admin' : '/';
            hubBtn.href = hubPath;
            hubBtn.className = 'md:hidden flex items-center justify-center size-10 rounded-lg bg-slate-100 dark:bg-card-dark text-slate-600 dark:text-slate-400 hover:text-primary transition-colors glass mr-2';

            const icon = document.createElement('span');
            icon.className = 'material-symbols-outlined text-[24px]';
            icon.textContent = (userRole === 'Admin' || userRole === 'Head Scout') ? 'manage_accounts' : 'dashboard_customize';

            hubBtn.appendChild(icon);
            // Insert before the "New Report" button (+) or profile
            headerActions.insertBefore(hubBtn, headerActions.firstChild);
        };

        injectHeaderHub();
        setInterval(injectHeaderHub, 2000);
    }
});
