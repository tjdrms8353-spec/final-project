const TOKEN_KEY = 'dayribbon-token';

export const biToken = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export async function bi(path, { method = 'GET', body, file } = {}) {
  const headers = {};
  const token = biToken.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (file) {
    payload = new FormData();
    payload.append('file', file);
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }
  const response = await fetch(`/api/bi${path}`, { method, headers, body: payload });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail
      : detail?.message ? `${detail.message} ${(detail.errors || []).join(' / ')}`
      : Array.isArray(detail) ? detail.map(d => d.msg).join(', ')
      : `요청 실패 (${response.status})`;
    throw Object.assign(new Error(message), { status: response.status });
  }
  return data;
}

export const won = (v) => v == null ? '-' : `${Math.round(v).toLocaleString('ko-KR')}원`;
export const eok = (v) => v == null ? '-' : `${(v / 1e8).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}억`;
export const formatKpi = (value, unit) => value == null ? '-'
  : unit === 'KRW' ? won(value) : unit === '%' ? `${value.toFixed(2)}%` : `${value.toLocaleString('ko-KR')}${unit}`;
