import { useEffect, useMemo, useRef, useState } from 'react'
import Globe from 'react-globe.gl'
import { LAYERS, colorFor, escapeHtml } from '../layers.js'

const TEXTURE = 'https://unpkg.com/three-globe/example/img'

function withAlpha(color, a) {
  // accepts #rrggbb or rgb(r,g,b)
  if (color.startsWith('#')) {
    const n = parseInt(color.slice(1), 16)
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`
  }
  return color.replace('rgb(', 'rgba(').replace(')', `,${a})`)
}

export default function GlobeView({ events, ensoPhase, onSelect }) {
  const globeRef = useRef()
  const boxRef = useRef()
  const [size, setSize] = useState({ w: 800, h: 600 })

  useEffect(() => {
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setSize({ w: Math.floor(width), h: Math.floor(height) })
    })
    ro.observe(boxRef.current)
    return () => ro.disconnect()
  }, [])

  // pulsing rings only for the notable ones, so hundreds of small quakes don't clutter the globe
  const rings = useMemo(
    () => events.filter((e) => LAYERS[e.type]?.rings && (e.type !== 'earthquake' || (e.value || 0) >= 4.5)),
    [events],
  )

  return (
    <div ref={boxRef} className="globe-box">
      <Globe
        ref={globeRef}
        width={size.w}
        height={size.h}
        globeImageUrl={`${TEXTURE}/earth-blue-marble.jpg`}
        bumpImageUrl={`${TEXTURE}/earth-topology.png`}
        backgroundImageUrl={`${TEXTURE}/night-sky.png`}
        pointsData={events}
        pointLat="lat"
        pointLng="lng"
        pointColor={(e) => colorFor(e, ensoPhase)}
        pointRadius={(e) => (e.type === 'earthquake' ? 0.25 + (e.value || 0) * 0.12 : LAYERS[e.type]?.radius || 0.5)}
        pointAltitude={(e) => LAYERS[e.type]?.altitude || 0.01}
        pointLabel={(e) =>
          `<div class="tip"><b>${escapeHtml(e.title)}</b><br/>${escapeHtml(LAYERS[e.type]?.label || e.type)} · ${escapeHtml(e.source)}${e.date ? '<br/>' + escapeHtml(e.date) : ''}</div>`
        }
        onPointClick={(e) => {
          onSelect(e)
          globeRef.current?.pointOfView({ lat: e.lat, lng: e.lng, altitude: 1.6 }, 900)
        }}
        ringsData={rings}
        ringLat="lat"
        ringLng="lng"
        ringColor={(e) => (t) => withAlpha(colorFor(e, ensoPhase), 1 - t)}
        ringMaxRadius={(e) => (e.type === 'el_nino' ? 14 : e.type === 'typhoon' ? 6 : 3 + (e.value || 0) * 0.4)}
        ringPropagationSpeed={2}
        ringRepeatPeriod={1400}
      />
    </div>
  )
}
