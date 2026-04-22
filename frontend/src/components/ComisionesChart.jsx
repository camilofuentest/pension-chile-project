import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { formatPct, formatPesos, costoPorMes, diferenciaAnual } from '../utils/format'
import { AfpLogo } from '../utils/afpLogos'

const SUELDO_DEFAULT = 800000

export default function ComisionesChart({ comisiones }) {
  const [sueldo, setSueldo] = useState(SUELDO_DEFAULT)

  if (!comisiones || comisiones.length === 0) return null

  const sorted  = [...comisiones].sort((a, b) => a.comision_pct - b.comision_pct)
  const minPct  = sorted[0].comision_pct
  const sueldoN = Number(sueldo) || SUELDO_DEFAULT

  const chartData = sorted.map(r => ({
    afp:         r.afp,
    comision:    r.comision_pct,
    costo_mes:   costoPorMes(sueldoN, r.comision_pct),
    diff_anual:  diferenciaAnual(sueldoN, r.comision_pct, minPct),
  }))

  return (
    <section className="px-4 py-6 sm:px-6">
      <h2 className="text-xl font-bold text-gray-800 dark:text-slate-100 mb-1 border-l-4 border-blue-600 pl-3">Comisiones AFP</h2>
      <p className="text-sm text-gray-500 dark:text-slate-400 mb-2">
        La comisión es el porcentaje de tu sueldo imponible que se lleva la AFP cada mes por administrar tu cuenta.
        Una comisión más baja significa más dinero que queda en tu bolsillo cada mes — aunque la decisión de AFP también depende de la rentabilidad que entrega.
      </p>

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <label className="text-sm text-gray-600 dark:text-slate-300 whitespace-nowrap">Con un sueldo de</label>
        <div className="border border-gray-200 dark:border-slate-600 rounded px-2 py-1 text-sm w-36 flex items-center bg-white dark:bg-slate-700">
          <span className="text-gray-400 dark:text-slate-500 mr-1">$</span>
          <input
            type="text"
            inputMode="numeric"
            value={new Intl.NumberFormat('es-CL').format(sueldoN)}
            onChange={e => {
              const raw = parseInt(e.target.value.replace(/\./g, '').replace(/[^\d]/g, ''), 10)
              setSueldo(isNaN(raw) ? 0 : raw)
            }}
            className="w-full bg-transparent outline-none text-gray-800 dark:text-slate-200"
          />
        </div>
        <span className="text-sm text-gray-400 dark:text-slate-500">CLP bruto mensual</span>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 60, right: 40, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--chart-grid)" />
          <XAxis type="number" tickFormatter={v => `${v}%`} tick={{ fontSize: 11, fill: 'var(--chart-axis)' }} />
          <YAxis type="category" dataKey="afp" tick={{ fontSize: 12, fill: 'var(--chart-axis)' }} width={80} />
          <Tooltip
            formatter={(v, name, props) => {
              const row = props.payload
              return [
                `${formatPct(v, 2)} → ${formatPesos(row.costo_mes)}/mes`,
                'Comisión AFP',
              ]
            }}
            contentStyle={{
              backgroundColor: 'var(--tooltip-bg, #fff)',
              border: '1px solid var(--tooltip-border, #e5e7eb)',
              borderRadius: '8px',
              fontSize: '13px',
            }}
          />
          <Bar dataKey="comision" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={entry.afp} fill={i === 0 ? '#22c55e' : '#60a5fa'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 rounded-xl border border-gray-200 dark:border-slate-700 overflow-x-auto">
        <table className="w-full text-sm min-w-[340px]">
          <thead className="bg-gray-50 dark:bg-slate-700 text-gray-500 dark:text-slate-400 text-xs uppercase">
            <tr>
              <th className="px-3 py-2 text-left">AFP</th>
              <th className="px-3 py-2 text-right">Comisión</th>
              <th className="px-3 py-2 text-right">Al mes</th>
              <th className="px-3 py-2 text-right hidden sm:table-cell">Diferencia al año</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
            {chartData.map((row, i) => (
              <tr key={row.afp} className={
                i === 0
                  ? 'bg-green-50 dark:bg-green-950/30'
                  : i === chartData.length - 1
                    ? 'bg-red-50 dark:bg-red-950/30'
                    : 'bg-white dark:bg-slate-800'
              }>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <AfpLogo afp={row.afp} className="h-5 w-10 shrink-0" />
                    <span className="font-medium text-gray-800 dark:text-slate-200">{row.afp}</span>
                    {i === 0 && <span className="hidden sm:inline text-xs text-green-600 dark:text-green-400">más barata</span>}
                    {i === chartData.length - 1 && <span className="hidden sm:inline text-xs text-red-500">más cara</span>}
                  </div>
                </td>
                <td className="px-3 py-2 text-right text-gray-700 dark:text-slate-300">{formatPct(row.comision, 2)}</td>
                <td className="px-3 py-2 text-right font-medium text-gray-800 dark:text-slate-200">{formatPesos(row.costo_mes)}</td>
                <td className="px-3 py-2 text-right text-red-500 hidden sm:table-cell">
                  {row.diff_anual > 0 ? `+${formatPesos(row.diff_anual)}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-3 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded-lg px-4 py-3 text-sm text-blue-900 dark:text-blue-200">
        <strong>¿Qué significa esto para mí?</strong> La comisión sale directo de tu cotización antes de que llegue a tu cuenta.
        Con tu sueldo, la diferencia entre la AFP más cara y la más barata es {formatPesos(diferenciaAnual(sueldoN, sorted[sorted.length - 1]?.comision_pct ?? 0, minPct))} al año. Considera también la rentabilidad de cada AFP antes de decidir.
      </div>
    </section>
  )
}
