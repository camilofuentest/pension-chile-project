import { useState, useMemo } from 'react'
import {
  BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer,
} from 'recharts'
import { AfpLogo } from '../utils/afpLogos'

// -----------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------
function fmt1(v) {
  if (v == null) return '—'
  return `${v.toFixed(1)}%`
}

function fmtMM(miles) {
  if (miles == null) return '—'
  const val = miles / 1_000_000
  const formatted = val % 1 === 0 ? val.toFixed(0) : val.toFixed(1)
  return `$${formatted} mil mill.`
}

const MEDALS = { 0: '🥇', 1: '🥈', 2: '🥉' }

// -----------------------------------------------------------------------
// Ganancia ranking for one year — sorted by absolute profit, best → worst
// -----------------------------------------------------------------------
function GananciaRanking({ financiero, year }) {
  const rows = useMemo(() => {
    return Object.entries(financiero)
      .map(([afp, d]) => {
        const idx = d.year.indexOf(year)
        return {
          afp,
          ganancia: idx >= 0 ? d.ganancia_miles[idx] : null,
          roe:      idx >= 0 ? d.roe_pct[idx]        : null,
        }
      })
      .filter(r => r.ganancia != null)
      .sort((a, b) => b.ganancia - a.ganancia)
  }, [financiero, year])

  if (!rows.length) return <p className="text-sm text-gray-400">Sin datos para {year}.</p>

  const best  = rows[0]
  const worst = rows[rows.length - 1]

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mb-4">
        {rows.map((r, i) => {
          const isBest  = i === 0
          const isWorst = i === rows.length - 1 && rows.length > 1
          return (
            <div
              key={r.afp}
              className={`rounded-xl border px-4 py-3 flex flex-col gap-1 ${
                isBest ? 'border-green-200 bg-green-50' : 'border-gray-100 bg-white'
              }`}
            >
              {/* rank + worst tag */}
              <div className="flex items-center justify-between mb-1">
                <span className="text-base">{MEDALS[i] ?? <span className="text-xs text-gray-400">#{i + 1}</span>}</span>
                {isWorst && (
                  <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                    menor ganancia
                  </span>
                )}
              </div>

              {/* logo */}
              <AfpLogo afp={r.afp} className="h-7 w-full mb-2" />
              <p className="font-semibold text-gray-700 text-xs leading-tight">{r.afp}</p>

              {/* primary: ganancia absoluta */}
              <p className={`text-lg font-bold mt-1 leading-tight ${r.ganancia >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                {fmtMM(r.ganancia)}
              </p>

              {/* secondary: ROE with size caveat */}
              {r.roe != null && (
                <p className="text-xs text-gray-500 font-semibold">
                  ROE {fmt1(r.roe)}
                </p>
              )}
            </div>
          )
        })}
      </div>

      {/* Callout */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-900">
        <p className="font-semibold mb-1">¿Qué significa esto para mí?</p>
        <p>
          En <strong>{year}</strong>, <strong>{best.afp}</strong> fue la AFP que más ganó
          en términos absolutos: <strong>{fmtMM(best.ganancia)}</strong> para sus accionistas.
          {worst.ganancia < 0
            ? <> <strong>{worst.afp}</strong> tuvo pérdidas ese año ({fmtMM(worst.ganancia)}).</>
            : <> <strong>{worst.afp}</strong> fue la de menor ganancia con {fmtMM(worst.ganancia)}.</>
          }
        </p>
        <p className="mt-2 text-blue-800">
          Esta ganancia proviene principalmente de las comisiones que pagan sus afiliados cada mes.
        </p>
      </div>

      {/* ROE caveat */}
      <p className="text-xs text-gray-400 mt-3">
        El ROE (mostrado como dato secundario) mide eficiencia sobre el capital propio, pero
        no es directamente comparable entre AFPs de distinto tamaño o antigüedad:
        una AFP nueva tiene menos patrimonio acumulado, lo que infla o distorsiona su ROE.
        Úsalo para ver la <em>evolución de cada AFP en el tiempo</em>, no para compararlas entre sí.
      </p>
    </>
  )
}

// -----------------------------------------------------------------------
// Historical ROE bar chart for one AFP
// -----------------------------------------------------------------------
function RoeTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const { roe, ganancia } = payload[0].payload
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 shadow text-sm">
      <p className="font-medium text-gray-700 mb-1">{label}</p>
      <p className={`font-bold ${roe >= 0 ? 'text-green-600' : 'text-red-500'}`}>
        Ganancia: {fmtMM(ganancia)}
      </p>
      {roe != null && (
        <p className="text-xs text-gray-400 mt-0.5">ROE: {fmt1(roe)}</p>
      )}
    </div>
  )
}

function RoeHistory({ financiero, afp }) {
  const data = financiero[afp]
  if (!data) return null

  const chartData = data.year.map((y, i) => ({
    year:     y,
    roe:      data.roe_pct[i],
    ganancia: data.ganancia_miles[i],
  }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 5, right: 10, left: 5, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
        <XAxis
          dataKey="year"
          tick={{ fontSize: 11, fill: '#6b7280' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={v => `$${(v / 1_000_000).toFixed(0)}`}
          tick={{ fontSize: 11, fill: '#6b7280' }}
          axisLine={false}
          tickLine={false}
          width={55}
        />
        <Tooltip content={<RoeTooltip />} />
        <ReferenceLine y={0} stroke="#d1d5db" />
        <Bar dataKey="ganancia" radius={[3, 3, 0, 0]} maxBarSize={36}>
          {chartData.map((entry, i) => (
            <Cell
              key={`cell-${i}`}
              fill={entry.ganancia == null ? '#e5e7eb' : entry.ganancia >= 0 ? '#60a5fa' : '#ef4444'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// -----------------------------------------------------------------------
// Main component
// -----------------------------------------------------------------------
export default function SaludFinanciera({ financiero }) {
  const afpList  = financiero ? Object.keys(financiero).sort() : []
  const yearList = useMemo(() => {
    if (!financiero) return []
    const all = new Set()
    Object.values(financiero).forEach(d => d.year.forEach(y => all.add(y)))
    return [...all].sort((a, b) => b - a)
  }, [financiero])

  const [selectedAfp,  setAfp]  = useState('Habitat')
  const [selectedYear, setYear] = useState(() => yearList[0] ?? 2025)

  if (!financiero) return null

  return (
    <section className="px-6 py-6">
      <h2 className="text-xl font-bold text-gray-800 mb-1 border-l-4 border-blue-600 pl-3">
        AFP como negocio: ¿cuánto gana cada AFP para sus dueños?
      </h2>
      <p className="text-sm text-gray-500 mb-5">
        Esto no es la rentabilidad de tu fondo — es la <strong>ganancia del negocio</strong> de
        administrar pensiones. El ranking muestra cuánto dinero ganó cada AFP para sus accionistas
        en el año seleccionado, según sus estados financieros oficiales.
        Fuente: Superintendencia de Pensiones.
      </p>

      {/* ---- RANKING ---- */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-3 flex-wrap">
          <h3 className="font-semibold text-gray-700">Ranking por año</h3>
          <select
            className="border rounded px-2 py-1 text-sm"
            value={selectedYear}
            onChange={e => setYear(Number(e.target.value))}
          >
            {yearList.map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <GananciaRanking financiero={financiero} year={selectedYear} />
      </div>

      {/* ---- HISTORICAL CHART ---- */}
      <div>
        <div className="flex items-center gap-3 mb-3 flex-wrap">
          <h3 className="font-semibold text-gray-700">Evolución histórica de ganancias</h3>
          <select
            className="border rounded px-2 py-1 text-sm"
            value={selectedAfp}
            onChange={e => setAfp(e.target.value)}
          >
            {afpList.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
        <RoeHistory financiero={financiero} afp={selectedAfp} />
        <p className="text-xs text-gray-400 mt-1 text-right">
          Ganancia anual (miles de millones $) — azul = ganancia, rojo = pérdida
        </p>
      </div>
    </section>
  )
}
