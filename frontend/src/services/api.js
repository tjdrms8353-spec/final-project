export async function request(path, options = {}) {
 const response = await fetch(path, options);
 if (!response.ok) throw new Error(`API request failed: ${response.status}`);
 return response.status === 204 ? null : response.json();
}
