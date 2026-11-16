import { ENSO_COLORS, LAYERS } from '../layers.js'

const STATUS_TEXT = { connecting: 'Connecting…', live: 'Live', reconnecting: 'Reconnecting…' }

export default function Sidebar({ status, snapshot, visible, onToggle, selected }) {
  const counts = snapshot?.counts || {}
  const avg = snapshot?.meta?.weather?.global_average_c
  const enso = snapshot?.meta?.enso
  const sources = snapshot?.sources || {}

  return (
    <aside className="sidebar">
      <h1>Earth System Trend Detective</h1>
      <div className={`pill ${status}`}>{STATUS_TEXT[status]}</div>
      {snapshot && <div className="muted">Updated {new Date(snapshot.generated_at).toLocaleTimeString()}</div>}

      <section>
        <h2>Climate</h2>
        <div className="stat">
          <span>Global avg temperature</span>
          <b>{avg != null ? `${avg.toFixed(1)} °C` : '—'}</b>
        </div>
        <div className="muted small">Area-weighted mean of {snapshot?.meta?.weather?.samples ?? 0} sampled points</div>
        <div className="stat">
          <span>ENSO phase</span>
          <b style={{ color: ENSO_COLORS[enso?.phase] }}>{enso ? `${enso.phase} (${enso.oni > 0 ? '+' : ''}${enso.oni})` : '—'}</b>
        </div>
      </section>

      <section>
        <h2>Layers</h2>
        {Object.entries(LAYERS).map(([key, layer]) => (
          <label key={key} className="layer">
            <input type="checkbox" checked={visible[key]} onChange={() => onToggle(key)} />
            <span className="dot" style={{ background: layer.color }} />
            <span className="grow">{layer.label}</span>
            <span className="count">{counts[key] ?? 0}</span>
          </label>
        ))}
      </section>

      {selected && (
        <section>
          <h2>Selected</h2>
          <b>{selected.title}</b>
          <div className="muted small">
            {LAYERS[selected.type]?.label} · {selected.source}
            <br />
            {selected.lat.toFixed(2)}, {selected.lng.toFixed(2)}
            {selected.value != null && ` · ${selected.value} ${selected.unit || ''}`}
            {selected.date && <><br />{selected.date}</>}
          </div>
        </section>
      )}

      <section>
        <h2>Data sources</h2>
        {Object.entries(sources).map(([name, s]) => (
          <div key={name} className="source" title={s.error || ''}>
            <span className={`dot ${s.status}`} />
            <span className="grow">{name}</span>
            <span className="muted small">{s.status === 'error' ? 'error' : s.count}</span>
          </div>
        ))}
      </section>
    </aside>
  )
}
