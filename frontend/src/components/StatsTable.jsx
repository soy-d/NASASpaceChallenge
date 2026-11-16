const fmt = (v, d = 3) => (Math.abs(v) < 0.001 && v !== 0 ? v.toExponential(2) : v.toFixed(d))

export default function StatsTable({ stats, unit, perDecade = true }) {
  const k = perDecade ? 10 : 1
  const per = perDecade ? 'decade' : 'year'
  const rows = [
    [`Sen's slope (${unit}/${per})`, fmt(stats.sen_slope_per_year * k)],
    [`Linear slope (${unit}/${per})`, fmt(stats.linear_slope_per_year * k)],
    ['Mann-Kendall Z', fmt(stats.mann_kendall_z, 2)],
    ['p-value', fmt(stats.p_value, 4)],
    ['Kendall τ', fmt(stats.kendall_tau, 2)],
    ['R²', fmt(stats.r_squared, 3)],
    ['Latest z-score', fmt(stats.latest_z_score, 2)],
    ['Observations', stats.n],
  ]
  return (
    <div>
      <div className={`verdict ${stats.direction.toLowerCase()}`}>
        {stats.direction} · {stats.significance_level}
      </div>
      <table className="stats">
        <tbody>
          {rows.map(([name, value]) => (
            <tr key={name}><td>{name}</td><td>{value}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
