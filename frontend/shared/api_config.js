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
    // Default to include credentials for session/cookies
    if (!options.credentials) {
        options.credentials = 'include';
    }

    return fetch(url, options);
};

console.log("🚀 API Config Loaded: Backend at " + window.API_BASE_URL);
