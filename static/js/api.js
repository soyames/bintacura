const API_BASE_URL = window.location.origin;

function getApiUrl(endpoint) {
    return `${API_BASE_URL}/api/v1/${endpoint.replace(/^\//, '')}`;
}

async function fetchApi(endpoint, options = {}) {
    const url = getApiUrl(endpoint);
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
    };
    const fetchOptions = {
        credentials: 'include',
        ...options,
        headers,
    };
    const response = await fetch(url, fetchOptions);
    if (!response.ok && response.status === 403) {
        window.location.href = '/auth/login/';
        throw new Error('Authentication required');
    }
    return response;
}
