import { useMemo, useRef } from 'react'
import { feature } from 'topojson-client'
import world from 'world-atlas/countries-110m.json'

const W = 720
const H = 360
const px = (lon) => ((lon + 180) / 360) * W
const py = (lat) => ((90 - lat) / 180) * H

function ringPath(ring) {
  return ring.map(([lon, lat], i) => `${i ? 'L' : 'M'}${px(lon).toFixed(1)} ${py(lat).toFixed(1)}`).join('') + 'Z'
}

// Click anywhere on the map to choose a location (equirectangular projection).
export default function WorldPinpointMap({ lat, lon, onPick }) {
  const svgRef = useRef()
  const d = useMemo(() => {
    const countries = feature(world, world.objects.countries).features
    return countries
      .map((f) => {
        const g = f.geometry
        if (!g) return ''
        const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates
        return polys.map((poly) => poly.map(ringPath).join('')).join('')
      })
      .join('')
  }, [])

  const handleClick = (e) => {
    const rect = svgRef.current.getBoundingClientRect()
    const lng = ((e.clientX - rect.left) / rect.width) * 360 - 180
    const la = 90 - ((e.clientY - rect.top) / rect.height) * 180
    onPick(Math.max(-85, Math.min(85, +la.toFixed(2))), +lng.toFixed(2))
  }

  return (
    <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="map" onClick={handleClick} role="img" aria-label="World map: click to choose a location">
      <rect width={W} height={H} fill="#0b1e3a" />
      {[-60, -30, 0, 30, 60].map((l) => <line key={l} x1="0" x2={W} y1={py(l)} y2={py(l)} stroke="#1e3a5f" strokeWidth="0.5" />)}
      {[-120, -60, 0, 60, 120].map((l) => <line key={l} y1="0" y2={H} x1={px(l)} x2={px(l)} stroke="#1e3a5f" strokeWidth="0.5" />)}
      <path d={d} fill="#2d4a3e" stroke="#7fa08f" strokeWidth="0.4" />
      <circle cx={px(lon)} cy={py(lat)} r="9" fill="none" stroke="#f43f5e" strokeWidth="1.5" />
      <circle cx={px(lon)} cy={py(lat)} r="3" fill="#f43f5e" />
    </svg>
  )
}
