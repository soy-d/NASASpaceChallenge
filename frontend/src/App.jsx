import { useMemo, useState } from 'react'
import GlobeView from './components/GlobeView.jsx'
import Sidebar from './components/Sidebar.jsx'
import AnalysisView from './components/AnalysisView.jsx'
import { useTelemetry } from './hooks/useTelemetry.js'
import { LAYERS } from './layers.js'
import './App.css'

const initialVisible = Object.fromEntries(Object.keys(LAYERS).map((k) => [k, k !== 'temperature']))

export default function App() {
  const { snapshot, status } = useTelemetry()
  const [view, setView] = useState('live') // live | analysis
  const [visible, setVisible] = useState(initialVisible)
  const [selected, setSelected] = useState(null)

  const events = useMemo(
    () => (snapshot?.events || []).filter((e) => visible[e.type]),
    [snapshot, visible],
  )

  return (
    <div className="shell">
      <nav className="topbar">
        <b>Earth System Trend Detective</b>
        <button className={view === 'live' ? 'on' : ''} onClick={() => setView('live')}>Live globe</button>
        <button className={view === 'analysis' ? 'on' : ''} onClick={() => setView('analysis')}>Past data analysis</button>
      </nav>
      {view === 'live' ? (
        <div className="app">
          <GlobeView events={events} ensoPhase={snapshot?.meta?.enso?.phase} onSelect={setSelected} />
          <Sidebar
            status={status}
            snapshot={snapshot}
            visible={visible}
            onToggle={(k) => setVisible((v) => ({ ...v, [k]: !v[k] }))}
            selected={selected}
          />
        </div>
      ) : (
        <AnalysisView />
      )}
    </div>
  )
}
