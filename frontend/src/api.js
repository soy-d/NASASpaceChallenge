export const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export async function getJson(path, params) {
  const url = new URL(path, API)
  Object.entries(params || {}).forEach(([k, v]) => v != null && url.searchParams.set(k, v))
  const res = await fetch(url)
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch { /* not json */ }
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json()
}
