// Historical analysis view that fetches archive and ENSO data from the backend and renders charts.
import { useCallback, useEffect, useState } from 'react'
import { getJson } from '../api.js'
import WorldPinpointMap from './WorldPinpointMap.jsx'
import TrendChart from './TrendChart.jsx'
import StatsTable from './StatsTable.jsx'
import { ENSO_COLORS } from '../layers.js'

export default function AnalysisView() {
  const [catalog, setCatalog] = useState(null)
  const [mode, setMode] = useState('region') // region | enso
  const [lat, setLat] = useState(6.93)
  const [lon, setLon] = useState(79.85)
  const [chosen, setChosen] = useState(['temp_mean', 'precip_sum'])
  const [cadence, setCadence] = useState('annual')
  const [startYear, setStartYear] = useState(2000)
  const [endYear, setEndYear] = useState(null)
  const [result, setResult] = useState(null)
  const [enso, setEnso] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getJson('/api/analysis/variables')
      .then((c) => { setCatalog(c); setEndYear(c.max_year) })
      .catch((e) => setError(`Could not reach the backend: ${e.message}`))
  }, [])

  const run = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      if (mode === 'enso') {
        setEnso(await getJson('/api/analysis/enso', { start_year: startYear }))
      } else {
        setResult(await getJson('/api/analysis/timeseries', {
          lat, lon, variables: chosen.join(','), cadence, start_year: startYear, end_year: endYear,
        }))
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [mode, lat, lon, chosen, cadence, startYear, endYear])

  const toggleVar = (id) => setChosen((c) => (c.includes(id) ? c.filter((v) => v !== id) : [...c, id]))
  const years = catalog ? Array.from({ length: catalog.max_year - catalog.min_year + 1 }, (_, i) => catalog.min_year + i) : []

  return (
    <div className="analysis">
      <div className="analysis-controls">
        <div className="tabs">
          <button className={mode === 'region' ? 'on' : ''} onClick={() => setMode('region')}>Region trends</button>
          <button className={mode === 'enso' ? 'on' : ''} onClick={() => setMode('enso')}>El Niño history</button>
        </div>

        {mode === 'region' && (
          <>
            <h2>Location</h2>
            <WorldPinpointMap lat={lat} lon={lon} onPick={(la, lo) => { setLat(la); setLon(lo) }} />
            <div className="muted small">Click the map to choose a point · {lat.toFixed(2)}°, {lon.toFixed(2)}°</div>
            <div className="chips">
              {catalog?.regions.map((r) => (
                <button key={r.id} title={r.note} onClick={() => { setLat(r.lat); setLon(r.lon) }}>{r.label}</button>
              ))}
            </div>
            <h2>Variables</h2>
            {catalog?.variables.map((v) => (
              <label key={v.id} className="layer" title={v.description}>
                <input type="checkbox" checked={chosen.includes(v.id)} onChange={() => toggleVar(v.id)} />
                <span className="dot" style={{ background: v.color }} />
                <span className="grow">{v.label}</span>
                <span className="count">{v.unit}</span>
              </label>
            ))}
          </>
        )}

        <h2>Time window</h2>
        <div className="row">
          <label>From <select value={startYear} onChange={(e) => setStartYear(+e.target.value)}>{years.map((y) => <option key={y}>{y}</option>)}</select></label>
          {mode === 'region' && (
            <>
              <label>To <select value={endYear ?? ''} onChange={(e) => setEndYear(+e.target.value)}>{years.map((y) => <option key={y}>{y}</option>)}</select></label>
              <label>Bins <select value={cadence} onChange={(e) => setCadence(e.target.value)}><option value="annual">Annual</option><option value="quarterly">Quarterly</option></select></label>
            </>
          )}
        </div>
        <button className="primary" disabled={loading || !catalog || (mode === 'region' && chosen.length === 0)} onClick={run}>
          {loading ? 'Fetching past data…' : 'Analyze'}
        </button>
        {error && <div className="error">{error}</div>}
      </div>

      <div className="analysis-results">
        {!result && !enso && !loading && <div className="muted">Choose a location, variables and a time window, then press Analyze. Data comes from the Open-Meteo ERA5 archive and NOAA, with trend statistics computed in the Python backend.</div>}

        {mode === 'region' && result && (
          <>
            <div className="muted small">{result.source} · {result.lat.toFixed(2)}°, {result.lon.toFixed(2)}° · {result.start_year}–{result.end_year} · {result.bins} {result.cadence} bins</div>
            {result.variables.map((v) => (
              <section key={v.id} className="card">
                <h3><span className="dot" style={{ background: v.color }} /> {v.label} <span className="muted small">({v.unit})</span></h3>
                <div className="card-body">
                  <TrendChart series={v.series} trend={v.stats.trend_line} color={v.color} unit={v.unit} />
                  <StatsTable stats={v.stats} unit={v.unit} />
                </div>
                <div className="muted small">White dashed: linear trend with 95% band · yellow: Sen's slope</div>
              </section>
            ))}
          </>
        )}

        {mode === 'enso' && enso && (
          <section className="card">
            <h3>Oceanic Niño Index (Niño 3.4 SST anomaly)</h3>
            <div className="card-body">
              <TrendChart series={enso.series} trend={enso.stats.trend_line} color="#f43f5e" unit="°C" bands />
              <StatsTable stats={enso.stats} unit="°C" />
            </div>
            <div className="muted small">
              Dashed red lines mark the ±0.5 °C El Niño / La Niña thresholds ·{' '}
              {Object.entries(enso.counts).map(([k, n]) => <span key={k} style={{ color: ENSO_COLORS[k], marginRight: 10 }}>{k}: {n} seasons</span>)}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
