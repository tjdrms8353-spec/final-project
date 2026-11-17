const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
export async function request(path, options = {}) {
 const response = await fetch(`${API_BASE}${path}`, options);
 if (!response.ok) throw new Error(`API request failed: ${response.status}`);
 return response.status === 204 ? null : response.json();
}
