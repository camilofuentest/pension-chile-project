import { useState } from 'react'
import {
  ComposedChart, Bar, Line, Cell,
  XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer,
} from 'recharts'
import { formatPct } from '../utils/format'

const AFP_LIMITED = { Modelo: 2010, Uno: 2019 }

function TooltipPersonalizado({ active, payload, label }) {
  if (!active || !payload?.length) return null

  const { value, sistema, windowLabel } = payload[0].payload

  if (value == null) return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 shadow text-sm">
      <p className="font-medium text-gray-700">{label}</p>
      <p className="text-gray-400 text-xs mt-1">Sin datos para este período</p>
    </div>
  )

  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 shadow text-sm max-w-[220px]">
      <p className="text-xs text-gray-400 mb-1">{windowLabel}</p>
      <p className={`font-bold text-base ${value >= 0 ? 'text-green-600' : 'text-red-500'}`}>
        {formatPct(value, 2)}
      </p>
      {sistema != null && (
        <p className="text-xs text-gray-500 mt-1">
          Promedio sistema: <span className="font-medium">{formatPct(sistema, 2)}</span>
          {value > sistema
            ? ' ↑ sobre el promedio'
            : value < sistema
              ? ' ↓ bajo el promedio'
              : ' = promedio'}
        </p>
      )}
      <p className="text-xs text-gray-400 mt-1">
        {value >= 0
          ? 'Tu dinero creció más que la inflación'
          : 'Tu dinero creció menos que la inflación'}
      </p>
    </div>
  )
}

export default function RentabilidadChart({ rentabilidades }) {
  const [fondo, setFondo] = useState('C')
  const [afp,   setAfp]   = useState('Capital')

  if (!rentabilidades) return null

  const key          = `${afp}__${fondo}`
  const dataset      = rentabilidades[key]
  const sistemaKey   = `Sistema__${fondo}`
  const sistemaData  = rentabilidades[sistemaKey]

  // Build a lookup: window_end_year → sistema value (for fast alignment)
  const sistemaByYear = {}
  if (sistemaData) {
    sistemaData.window_end_years.forEach((y, i) => {
      sistemaByYear[y] = sistemaData.values[i]
    })
  }

  // AFP list — exclude Sistema from the AFP selector
  const afpList   = [...new Set(
    Object.values(rentabilidades).map(d => d.afp).filter(a => a !== 'Sistema')
  )].sort()
  const fondoList = ['A', 'B', 'C', 'D', 'E']
  const limitedYear = AFP_LIMITED[afp]

  const chartData = dataset?.window_end_years
    ? dataset.window_end_years.map((y, i) => ({
        year:        y,
        value:       dataset.values[i],
        sistema:     sistemaByYear[y] ?? null,
        windowLabel: dataset.window_labels?.[i] ?? String(y),
      }))
    : []

  function barColor(entry) {
    if (entry.value == null) return '#e5e7eb'
    return entry.value >= 0 ? '#22c55e' : '#ef4444'
  }

  return (
    <section className="px-4 py-6 sm:px-6">
      <h2 className="text-xl font-bold text-gray-800 mb-1 border-l-4 border-blue-600 pl-3">
        Rentabilidad por período de 12 meses
      </h2>
      <p className="text-sm text-gray-500 mb-4">
        Cada barra es un período de 12 meses consecutivos,{' '}
        <strong>ya descontando la inflación</strong>.
        La línea punteada muestra el promedio del sistema ese mismo período.
        Pasa el cursor sobre cada barra para ver el detalle.
      </p>

      <div className="flex gap-3 mb-4 flex-wrap">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Tu AFP</label>
          <select
            className="border rounded px-2 py-1 text-sm"
            value={afp}
            onChange={e => setAfp(e.target.value)}
          >
            {afpList.map(a => <option key={a}>{a}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Fondo</label>
          <select
            className="border rounded px-2 py-1 text-sm"
            value={fondo}
            onChange={e => setFondo(e.target.value)}
          >
            {fondoList.map(f => <option key={f} value={f}>Fondo {f}</option>)}
          </select>
        </div>
      </div>

      {limitedYear && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-3 text-xs text-amber-800">
          Esta AFP partió en {limitedYear}, por eso no aparecen datos anteriores a ese año.
        </div>
      )}

      {!dataset ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-6 text-center text-sm text-gray-400">
          No hay datos disponibles para {afp} Fondo {fondo}.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
            <XAxis
              dataKey="year"
              tick={{ fontSize: 11, fill: '#6b7280' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={v => `${v}%`}
              tick={{ fontSize: 11, fill: '#6b7280' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<TooltipPersonalizado />} />
            <ReferenceLine y={0} stroke="#d1d5db" />
            <Bar dataKey="value" radius={[3, 3, 0, 0]} maxBarSize={40}>
              {chartData.map((entry, i) => (
                <Cell key={`cell-${i}`} fill={barColor(entry)} />
              ))}
            </Bar>
            {sistemaData && (
              <Line
                type="monotone"
                dataKey="sistema"
                stroke="#6b7280"
                strokeWidth={1.5}
                strokeDasharray="5 3"
                dot={false}
                activeDot={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      )}

      <div className="flex gap-4 mt-2 text-xs text-gray-500 flex-wrap">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm bg-green-500 inline-block" /> Período positivo
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm bg-red-400 inline-block" /> Período negativo
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm bg-gray-200 inline-block" /> Sin datos
        </span>
        {sistemaData && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-5 border-t-2 border-dashed border-gray-400" />
            Promedio sistema
          </span>
        )}
      </div>

      <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-900">
        <p className="font-semibold mb-1">¿Qué significa esto para mí?</p>
        <p>
          Los períodos en <strong>rojo</strong> no significan que perdiste dinero de
          tu bolsillo — significan que tu fondo creció <em>menos</em> que la inflación
          ese año. Lo normal es ver períodos rojos seguidos de períodos verdes.
          Lo que importa es el resultado acumulado a lo largo de muchos años.
        </p>
        <p className="mt-2">
          → Revisa el <strong>ranking</strong> más arriba para comparar tu AFP con las demás.
        </p>
      </div>
    </section>
  )
}
