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
        { name: 'Home', icon: 'home', path: '/dashboard', regex: /^\/(dashboard|scout-dashboard|$)/ },
        { name: 'Teams', icon: 'groups', path: '/teams-dir', regex: /^\/teams-dir/ },
        { name: 'Schedule', icon: 'calendar_month', path: '/dashboard', regex: /^\/$/ }
    ];

    // Add role-specific items
    if (userRole === 'Admin' || userRole === 'Head Scout') {
        navItems.push({ name: 'Management', icon: 'manage_accounts', path: '/admin-hub', regex: /^\/admin-hub/ });
        navItems.push({ name: 'Pick List', icon: 'drag_indicator', path: '/picklist', regex: /^\/picklist/ });
        navItems.push({ name: 'Analytics', icon: 'analytics', path: '/head-scout-stats', regex: /^\/(head-scout-stats|head-scout-analytics)/ });
    } else {
        navItems.push({ name: 'Profile', icon: 'person', path: '/profile/edit', regex: /^\/profile/ });
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
    }
});
