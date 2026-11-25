// VITE_API_BASE가 설정되면 해당 서버로 직접 호출, 미설정 시 vite dev proxy(/api) 사용
const BASE = import.meta.env.VITE_API_BASE || ''

export function getToken() {
  return localStorage.getItem('dayribbon_token')
}
export function setToken(t) {
  if (t) localStorage.setItem('dayribbon_token', t)
  else localStorage.removeItem('dayribbon_token')
}

export async function api(path, { method = 'GET', body, formData } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  let payload
  if (formData) {
    payload = formData
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  const res = await fetch(`${BASE}${path}`, { method, headers, body: payload })
  if (res.status === 401) {
    setToken(null)
    window.location.href = '/login'
    throw new Error('인증이 필요합니다.')
  }
  const ct = res.headers.get('content-type') || ''
  if (!res.ok) {
    let msg = `오류 ${res.status}`
    try {
      const j = await res.json()
      msg = j.detail || msg
    } catch { /* ignore */ }
    throw new Error(msg)
  }
  if (ct.includes('application/pdf')) return res.blob()
  return res.json()
}

export function fmtWon(v) {
  if (v === null || v === undefined || v === '') return '-'
  const n = Number(v)
  if (Math.abs(n) >= 1e8) return `${(n / 1e8).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}억원`
  if (Math.abs(n) >= 1e4) return `${(n / 1e4).toLocaleString('ko-KR', { maximumFractionDigits: 0 })}만원`
  return `${n.toLocaleString('ko-KR')}원`
}

export function fmtNum(v, digits = 1) {
  if (v === null || v === undefined) return '-'
  return Number(v).toLocaleString('ko-KR', { maximumFractionDigits: digits })
}

export function pct(v, digits = 1) {
  if (v === null || v === undefined) return '-'
  const n = Number(v)
  return `${n > 0 ? '+' : ''}${n.toLocaleString('ko-KR', { maximumFractionDigits: digits })}%`
}

export function fmtDate(iso) {
  if (!iso) return '-'
  return iso.slice(0, 16).replace('T', ' ')
}
