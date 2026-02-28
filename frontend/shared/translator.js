/**
 * Shared Multi-Language Translation Widget
 * Injects Google Translate and a custom floating language selector into any page.
 */

(function () {
    // 1. Inject Google Translate Script
    const gtScript = document.createElement('script');
    gtScript.type = 'text/javascript';
    gtScript.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
    document.head.appendChild(gtScript);

    // 2. Hide Google's native ugly banner and widgets via CSS
    const style = document.createElement('style');
    style.innerHTML = `
        .goog-te-banner-frame.skiptranslate, .goog-te-gadget-icon { display: none !important; }
        body { top: 0px !important; }
        #google_translate_element { display: none !important; }
        .goog-tooltip { display: none !important; }
        .goog-tooltip:hover { display: none !important; }
        .goog-text-highlight { background-color: transparent !important; border: none !important; box-shadow: none !important; }
        
        /* Prevent Material Icons from turning into text when translated */
        .material-symbols-outlined {
            font-family: 'Material Symbols Outlined' !important;
            direction: ltr;
        }
    `;
    document.head.appendChild(style);

    // 3. Define Google Translate callback
    window.googleTranslateElementInit = function () {
        new google.translate.TranslateElement({
            pageLanguage: 'en', // Assuming default language is English
            includedLanguages: 'en,fr,es,hi,zh-CN,ru,ar',
            autoDisplay: false
        }, 'google_translate_element');
    };

    // 4. Create Custom Floating Widget & Tag Icons
    window.addEventListener('DOMContentLoaded', () => {
        // Tag all Material Symbols with 'notranslate' to prevent Google Translate from ruining UI icons
        function protectIcons() {
            document.querySelectorAll('.material-symbols-outlined, .material-symbols-rounded, .material-symbols-sharp').forEach(icon => {
                icon.classList.add('notranslate');
                icon.setAttribute('translate', 'no');
            });
        }

        protectIcons();

        // Observe for dynamically added icons (e.g., from JS rendering)
        const observer = new MutationObserver((mutations) => {
            let shouldProtect = false;
            mutations.forEach(mutation => {
                if (mutation.addedNodes.length > 0) shouldProtect = true;
            });
            if (shouldProtect) protectIcons();
        });
        observer.observe(document.body, { childList: true, subtree: true });

        // Create hidden div for the native translator API to hook into
        const gtDiv = document.createElement('div');
        gtDiv.id = 'google_translate_element';
        document.body.appendChild(gtDiv);

        // Build Custom Floating UI
        const widgetHtml = `
            <div id="custom-language-selector" class="fixed bottom-6 left-6 z-[9999] font-sans notranslate">
                <div class="relative group">
                    <!-- Dropdown Button -->
                    <button class="flex items-center gap-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-lg hover:shadow-xl hover:border-blue-500 transition-all rounded-full px-4 py-3 text-slate-700 dark:text-slate-200 font-medium text-sm focus:outline-none">
                        <span class="material-symbols-outlined text-xl text-blue-500">translate</span>
                        <span id="current-lang-text">English</span>
                        <span class="material-symbols-outlined text-sm text-slate-400 group-hover:block transition-transform duration-200">expand_less</span>
                    </button>
                    
                    <!-- Dropdown Menu -->
                    <div class="absolute bottom-full left-0 mb-3 w-48 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 overflow-hidden origin-bottom-left scale-95 group-hover:scale-100">
                        <ul class="flex flex-col py-2">
                            <li><button onclick="changeLanguage('en', 'English')" class="w-full text-left px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-200 font-medium transition-colors flex items-center justify-between">English <span class="text-lg">&#127468;&#127463;</span></button></li>
                            <li><button onclick="changeLanguage('fr', 'Français')" class="w-full text-left px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-200 font-medium transition-colors flex items-center justify-between">Français <span class="text-lg">&#127467;&#127479;</span></button></li>
                            <li><button onclick="changeLanguage('es', 'Español')" class="w-full text-left px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-200 font-medium transition-colors flex items-center justify-between">Español <span class="text-lg">🇪🇸</span></button></li>
                            <li><button onclick="changeLanguage('hi', 'हिन्दी')" class="w-full text-left px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-200 font-medium transition-colors flex items-center justify-between">हिन्दी <span class="text-lg">🇮🇳</span></button></li>
                            <li><button onclick="changeLanguage('zh-CN', '中文')" class="w-full text-left px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-200 font-medium transition-colors flex items-center justify-between">中文 <span class="text-lg">🇨🇳</span></button></li>
                            <li><button onclick="changeLanguage('ru', 'Русский')" class="w-full text-left px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-200 font-medium transition-colors flex items-center justify-between">Русский <span class="text-lg">🇷🇺</span></button></li>
                            <li><button onclick="changeLanguage('ar', 'العربية')" class="w-full text-left px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-200 font-medium transition-colors flex items-center justify-between">العربية <span class="text-lg">🇸🇦</span></button></li>
                        </ul>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', widgetHtml);

        // Initialize label based on existing cookie
        const currentLangCookie = getCookie('googtrans');
        if (currentLangCookie) {
            const langCode = currentLangCookie.split('/').pop(); // Extract lang code from e.g. "/en/fr"
            const langMap = {
                'en': 'English', 'fr': 'Français', 'es': 'Español', 'hi': 'हिन्दी',
                'zh-CN': '中文', 'ru': 'Русский', 'ar': 'العربية'
            };
            if (langMap[langCode]) {
                document.getElementById('current-lang-text').innerText = langMap[langCode];
            }
        }
    });

    // Language Change Logic
    window.changeLanguage = function (langCode, langName) {
        document.getElementById('current-lang-text').innerText = langName;

        // Google Translate uses a specific cookie format: /auto/en (source/target)
        // Set cookies for both domain and subdomains to ensure coverage
        setCookie('googtrans', `/en/${langCode}`, 30);
        setCookie('googtrans', `/en/${langCode}`, 30, document.domain);

        // Trigger a reload to apply the translation natively without glitched UI
        window.location.reload();
    };

    // Cookie Utilities
    function setCookie(name, value, days, domain) {
        let expires = "";
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = "; expires=" + date.toUTCString();
        }
        let domainStr = domain ? `; domain=${domain}` : "";
        document.cookie = name + "=" + (value || "") + expires + domainStr + "; path=/";
    }

    function getCookie(name) {
        const nameEQ = name + "=";
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    }
})();
