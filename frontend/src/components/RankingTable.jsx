import { useState } from 'react'
import { formatPct, formatPesos } from '../utils/format'
import { AfpLogo } from '../utils/afpLogos'

const AFP_LIMITED      = { Modelo: 2010, Uno: 2019 }
const PERIOD_YEARS     = { '2y': 2, '5y': 5, '10y': 10, '15y': 15 }
const AHORRO_DEFAULT   = 10_000_000

export default function RankingTable({ rentabilidades }) {
  const [fondo,  setFondo]  = useState('C')
  const [period, setPeriod] = useState('10y')
  const [ahorro, setAhorro] = useState(AHORRO_DEFAULT)

  if (!rentabilidades) return null

  const fondoList  = ['A', 'B', 'C', 'D', 'E']
  const periodList = [
    { key: '2y',  label: '2 años'  },
    { key: '5y',  label: '5 años'  },
    { key: '10y', label: '10 años' },
    { key: '15y', label: '15 años' },
  ]

  // Extract the reference month label from the data (same for all AFP/fondo combos)
  const firstEntry    = Object.values(rentabilidades)[0]
  const lastMonthLabel = firstEntry?.last_month_label ?? ''

  const rows = Object.values(rentabilidades)
    .filter(d => d.fondo === fondo)
    .map(d => ({
      afp:     d.afp,
      value:   d.periodos?.[period] ?? null,
      limited: AFP_LIMITED[d.afp],
    }))
    .sort((a, b) => {
      if (a.value == null) return 1
      if (b.value == null) return -1
      return b.value - a.value
    })

  // Gap between best and worst AFP (only among those with data)
  const withData = rows.filter(r => r.value != null)
  const best  = withData[0]
  const worst = withData[withData.length - 1]
  const n     = PERIOD_YEARS[period]
  const gap   = best && worst && best !== worst
    ? parseFloat((best.value - worst.value).toFixed(2))
    : null
  const ahorroN = Number(ahorro) || AHORRO_DEFAULT
  const impacto = gap != null
    ? Math.round(ahorroN * (Math.pow(1 + best.value / 100, n) - Math.pow(1 + worst.value / 100, n)))
    : null

  return (
    <section className="px-4 py-6 sm:px-6">
      <h2 className="text-xl font-bold text-gray-800 mb-1 border-l-4 border-blue-600 pl-3">Ranking de rentabilidad</h2>
      <p className="text-sm text-gray-500 mb-1">
        La <strong>rentabilidad real</strong> es cuánto creció tu dinero <em>por encima de la inflación</em>.
        Si tu fondo subió 8% pero la inflación fue 5%, tu rentabilidad real fue 3% —
        eso es lo que realmente ganaste en poder de compra.
      </p>
      <p className="text-sm text-gray-500 mb-4">
        Calculada hasta <strong>{lastMonthLabel}</strong>.{' '}
        <span className="text-blue-600 font-medium">Cambia el fondo y el período</span> para ver cómo se mueve el ranking — en algunos fondos el orden cambia bastante.
      </p>

      <div className="flex gap-3 mb-4 flex-wrap">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Fondo</label>
          <div className="flex gap-1">
            {fondoList.map(f => (
              <button
                key={f}
                onClick={() => setFondo(f)}
                className={`px-3 py-1 rounded text-sm font-medium border ${
                  fondo === f
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-200'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Período</label>
          <div className="flex gap-1">
            {periodList.map(p => (
              <button
                key={p.key}
                onClick={() => setPeriod(p.key)}
                className={`px-3 py-1 rounded text-sm font-medium border ${
                  period === p.key
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-200'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-xl overflow-x-auto border border-gray-200">
        <table className="w-full text-sm min-w-[320px]">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th className="px-3 py-3 text-left">#</th>
              <th className="px-3 py-3 text-left">AFP</th>
              <th className="px-3 py-3 text-right">
                <span className="hidden sm:inline">Rentabilidad real anual promedio</span>
                <span className="sm:hidden">Rentab. anual</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((row, i) => {
              const rank    = row.value != null ? i + 1 : null
              const medal   = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : null
              const isWorst = row === worst
              return (
                <tr key={row.afp} className="bg-white hover:bg-gray-50">
                  <td className="px-3 py-3 text-gray-400 text-base">
                    {medal ?? (rank ?? '—')}
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <AfpLogo afp={row.afp} className="h-5 w-10 shrink-0" />
                      <span className="font-medium text-gray-800">{row.afp}</span>
                      {isWorst && (
                        <span className="hidden sm:inline text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                          menor rentabilidad
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3 text-right">
                    {row.value != null ? (
                      <span className={`font-bold ${row.value >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                        {formatPct(row.value, 2)}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-xs">
                        Sin datos{row.limited ? <span className="hidden sm:inline"> — desde {row.limited}</span> : ''}
                      </span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {gap != null ? (
        <div className="mt-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-900">
          <p className="font-semibold mb-1">¿Qué significa esto para mí?</p>
          <p>
            En los últimos <strong>{n} años</strong>, la brecha entre{' '}
            <strong>{best.afp}</strong> (la mejor) y <strong>{worst.afp}</strong> (la peor)
            fue de <strong>{formatPct(gap, 2)} al año</strong>.
          </p>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span>Si tienes</span>
            <div className="flex items-center border border-blue-300 rounded bg-white text-gray-800 text-sm">
              <span className="pl-2 text-gray-400 select-none">$</span>
              <input
                type="text"
                inputMode="numeric"
                value={new Intl.NumberFormat('es-CL').format(ahorroN)}
                onChange={e => {
                  const raw = parseInt(e.target.value.replace(/\./g, '').replace(/[^\d]/g, ''), 10)
                  setAhorro(isNaN(raw) ? 0 : raw)
                }}
                className="px-2 py-0.5 w-32 bg-transparent outline-none"
              />
            </div>
            <span>ahorrados, la diferencia sería</span>
            <strong>{formatPesos(impacto)}</strong>
            <span>en {n} años.</span>
          </div>
        </div>
      ) : (
        <div className="mt-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-900">
          <strong>¿Qué significa esto para mí?</strong> No hay suficientes AFPs con
          datos para este período. Prueba con un período más corto o un fondo diferente.
        </div>
      )}
    </section>
  )
}
