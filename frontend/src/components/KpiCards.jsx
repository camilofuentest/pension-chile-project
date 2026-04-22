import { formatNumber, formatPct, formatPesos } from '../utils/format'

const MESES = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']

function formatFecha(fecha) {
  if (!fecha) return ''
  const [year, month] = fecha.split('-')
  return `${MESES[parseInt(month, 10) - 1]} ${year}`
}

const SUELDO_REF = 800_000

export default function KpiCards({ comisiones, afiliados }) {
  if (!comisiones || !afiliados) return null

  const sistema = afiliados.find(r => r.afp === 'Sistema')
  const totalAfiliados = sistema?.afiliados ?? null

  const afpRows = afiliados.filter(r => r.afp !== 'Sistema')
  const largest = afpRows.reduce((best, r) =>
    (r.afiliados ?? 0) > (best.afiliados ?? 0) ? r : best
  , afpRows[0])

  const minComision = comisiones.reduce((min, r) =>
    r.comision_pct < min.comision_pct ? r : min
  )
  const maxComision = comisiones.reduce((max, r) =>
    r.comision_pct > max.comision_pct ? r : max
  )
  const diffPct = maxComision.comision_pct - minComision.comision_pct
  const diffPesosMes = Math.round(SUELDO_REF * diffPct / 100)

  const cards = [
    {
      label: 'Afiliados al sistema',
      value: formatNumber(totalAfiliados),
      note:  `Datos a ${formatFecha(sistema?.fecha)}`,
      accent: 'border-blue-500',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
          <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
      ),
    },
    {
      label: `AFP con más afiliados: ${largest?.afp ?? '—'}`,
      value: formatPct(largest?.market_share_pct, 1),
      note:  `${formatNumber(largest?.afiliados)} personas afiliadas`,
      accent: 'border-purple-500',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a855f7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
          <polyline points="17 6 23 6 23 12"/>
        </svg>
      ),
    },
    {
      label: 'Brecha entre AFP más cara y más barata',
      value: formatPct(diffPct, 2),
      note:  `${minComision.afp} vs ${maxComision.afp} — equivale a ${formatPesos(diffPesosMes)}/mes con sueldo de ${formatPesos(SUELDO_REF)}`,
      accent: 'border-amber-500',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="19" y1="5" x2="5" y2="19"/>
          <circle cx="6.5" cy="6.5" r="2.5"/>
          <circle cx="17.5" cy="17.5" r="2.5"/>
        </svg>
      ),
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
      {cards.map(card => (
        <div key={card.label} className={`bg-white dark:bg-slate-800 rounded-2xl shadow-sm p-5 border-t-4 ${card.accent} transition-colors duration-200`}>
          <div className="mb-3">{card.icon}</div>
          <p className="text-sm text-gray-500 dark:text-slate-400 mb-1">{card.label}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-slate-100">{card.value}</p>
          <p className="text-xs text-gray-400 dark:text-slate-500 mt-2">{card.note}</p>
        </div>
      ))}
    </div>
  )
}
