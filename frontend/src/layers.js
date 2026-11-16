// One entry per hazard type: label, colour, and how it is drawn on the globe.
export const LAYERS = {
  typhoon:     { label: 'Typhoons / storms', color: '#38bdf8', radius: 0.9, altitude: 0.04, rings: true },
  wildfire:    { label: 'Wildfires',         color: '#f97316', radius: 0.35, altitude: 0.02 },
  volcano:     { label: 'Volcanoes',         color: '#ef4444', radius: 0.6, altitude: 0.03 },
  earthquake:  { label: 'Earthquakes',       color: '#facc15', radius: 0.45, altitude: 0.02, rings: true },
  tsunami:     { label: 'Tsunami potential', color: '#a855f7', radius: 0.8, altitude: 0.03, rings: true },
  rain:        { label: 'Rain',              color: '#3b82f6', radius: 1.4, altitude: 0.006 },
  snow:        { label: 'Snow',              color: '#e2e8f0', radius: 1.4, altitude: 0.006 },
  sea_ice:     { label: 'Sea / lake ice',    color: '#67e8f9', radius: 0.7, altitude: 0.01 },
  el_nino:     { label: 'El Niño / La Niña', color: '#f43f5e', radius: 2.5, altitude: 0.01, rings: true },
  temperature: { label: 'Temperature grid',  color: '#fb923c', radius: 1.2, altitude: 0.003 },
}

export const ENSO_COLORS = { 'El Niño': '#f43f5e', 'La Niña': '#3b82f6', Neutral: '#94a3b8' }

// blue (cold) -> yellow -> red (hot), clamped to -30..40 °C
export function tempColor(c) {
  const t = Math.max(0, Math.min(1, (c + 30) / 70))
  const stops = [[59, 130, 246], [250, 204, 21], [239, 68, 68]]
  const [a, b, u] = t < 0.5 ? [stops[0], stops[1], t * 2] : [stops[1], stops[2], (t - 0.5) * 2]
  return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * u)).join(',')})`
}

export function colorFor(ev, ensoPhase) {
  if (ev.type === 'temperature') return tempColor(ev.value)
  if (ev.type === 'el_nino') return ENSO_COLORS[ensoPhase] || LAYERS.el_nino.color
  return LAYERS[ev.type]?.color || '#ffffff'
}

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
}
