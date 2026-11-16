// SVG time-series chart: observations, OLS trend, Sen's slope and a 95% confidence band.
const W = 640
const H = 260
const M = { l: 52, r: 14, t: 12, b: 28 }

export default function TrendChart({ series, trend, color, unit, bands }) {
  const xs = series.map((p) => p.x)
  const ys = series.map((p) => p.value)
  const lo = trend ? Math.min(...ys, ...trend.map((t) => t.ci_low)) : Math.min(...ys)
  const hi = trend ? Math.max(...ys, ...trend.map((t) => t.ci_high)) : Math.max(...ys)
  const pad = (hi - lo || 1) * 0.08
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)]
  const [y0, y1] = [Math.min(lo - pad, bands ? -0.5 - pad : Infinity), Math.max(hi + pad, bands ? 0.5 + pad : -Infinity)]
  const X = (x) => M.l + ((x - x0) / (x1 - x0 || 1)) * (W - M.l - M.r)
  const Y = (y) => H - M.b - ((y - y0) / (y1 - y0 || 1)) * (H - M.t - M.b)
  const line = (pts) => pts.map(([x, y], i) => `${i ? 'L' : 'M'}${X(x).toFixed(1)} ${Y(y).toFixed(1)}`).join('')
  const yTicks = Array.from({ length: 5 }, (_, i) => y0 + ((y1 - y0) * i) / 4)
  const xTicks = Array.from({ length: Math.min(6, series.length) }, (_, i) => x0 + ((x1 - x0) * i) / (Math.min(6, series.length) - 1 || 1))

  const band = trend && `${trend.map((t) => `${X(t.x).toFixed(1)},${Y(t.ci_high).toFixed(1)}`).join(' ')} ${[...trend].reverse().map((t) => `${X(t.x).toFixed(1)},${Y(t.ci_low).toFixed(1)}`).join(' ')}`

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart">
      {yTicks.map((t, i) => (
        <g key={i}>
          <line x1={M.l} x2={W - M.r} y1={Y(t)} y2={Y(t)} stroke="#1e293b" />
          <text x={M.l - 6} y={Y(t) + 4} textAnchor="end" className="axis">{Math.abs(t) >= 100 ? t.toFixed(0) : t.toFixed(1)}</text>
        </g>
      ))}
      {xTicks.map((t, i) => <text key={i} x={X(t)} y={H - 8} textAnchor="middle" className="axis">{Math.round(t)}</text>)}
      {bands && [0.5, -0.5].map((v) => <line key={v} x1={M.l} x2={W - M.r} y1={Y(v)} y2={Y(v)} stroke="#f43f5e" strokeDasharray="4 3" opacity="0.6" />)}
      {band && <polygon points={band} fill={color} opacity="0.15" />}
      <path d={line(series.map((p) => [p.x, p.value]))} fill="none" stroke={color} strokeWidth="1.6" />
      {series.length <= 60 && series.map((p, i) => <circle key={i} cx={X(p.x)} cy={Y(p.value)} r="2.4" fill={color}><title>{`${p.label}: ${p.value} ${unit}`}</title></circle>)}
      {trend && <path d={line(trend.map((t) => [t.x, t.ols]))} fill="none" stroke="#e2e8f0" strokeWidth="1.4" strokeDasharray="6 3" />}
      {trend && <path d={line(trend.map((t) => [t.x, t.sen]))} fill="none" stroke="#facc15" strokeWidth="1.4" />}
    </svg>
  )
}
