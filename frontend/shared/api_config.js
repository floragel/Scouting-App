/**
 * FRC Scouting App - Global API Configuration
 * Team 6622 "StanRobotix" 2026 Season
 */

// Deployment URL for the Vercel Backend
window.API_BASE_URL = 'https://frc-scouting-app.nayl.ca';

/**
 * Global helper for API fetches.
 * - Automatically prepends API_BASE_URL for relative paths.
 * - Ensures 'credentials: include' for session management if not specified.
 */
window.apiFetch = async function(url, options = {}) {
    let finalUrl = url;
    if (url.startsWith('/api/')) {
        finalUrl = window.API_BASE_URL + url;
    }

    // Default to include credentials for cross-origin session/cookies
    if (!options.credentials) {
        options.credentials = 'include';
    }

    return fetch(finalUrl, options);
};

console.log("🚀 API Config Loaded: Backend at " + window.API_BASE_URL);
