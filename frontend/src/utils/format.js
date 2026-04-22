/**
 * format.js — Chilean number formatting utilities.
 * All user-facing numbers go through these functions.
 */

/** $1.200.000 */
export function formatPesos(value) {
  if (value == null || isNaN(value)) return '—'
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.round(value))
}

/** 4,2% */
export function formatPct(value, decimals = 1) {
  if (value == null || isNaN(value)) return '—'
  return `${value.toFixed(decimals).replace('.', ',')}%`
}

/** 3.800.000 */
export function formatNumber(value) {
  if (value == null || isNaN(value)) return '—'
  return new Intl.NumberFormat('es-CL').format(Math.round(value))
}

/**
 * How much does this AFP commission cost per month, in pesos.
 * @param {number} salarioCLP  gross salary in CLP
 * @param {number} comisionPct AFP commission % (e.g. 0.44)
 */
export function costoPorMes(salarioCLP, comisionPct) {
  return Math.round(salarioCLP * (comisionPct / 100))
}

/**
 * How much more per year vs the cheapest AFP.
 */
export function diferenciaAnual(salarioCLP, comisionPct, minComisionPct) {
  const diff = (comisionPct - minComisionPct) / 100
  return Math.round(salarioCLP * diff * 12)
}
