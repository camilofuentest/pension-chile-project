import { useAfpData } from './hooks/useAfpData'
import KpiCards          from './components/KpiCards'
import FondosExplainer   from './components/FondosExplainer'
import RentabilidadChart from './components/RentabilidadChart'
import RankingTable      from './components/RankingTable'
import ComisionesChart   from './components/ComisionesChart'
import SaludFinanciera   from './components/SaludFinanciera'

function LoadingState() {
  return (
    <div className="flex items-center justify-center min-h-screen text-gray-400 text-sm">
      Cargando datos...
    </div>
  )
}

function ErrorState({ error }) {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center max-w-md px-4">
        <p className="text-red-500 font-medium mb-2">No se pudieron cargar los datos</p>
        <p className="text-gray-400 text-sm">{error?.message}</p>
      </div>
    </div>
  )
}

// Format today's date in Spanish: "21 de abril de 2026"
const MESES = [
  'enero','febrero','marzo','abril','mayo','junio',
  'julio','agosto','septiembre','octubre','noviembre','diciembre'
]
function fechaHoy() {
  const d = new Date()
  return `${d.getDate()} de ${MESES[d.getMonth()]} de ${d.getFullYear()}`
}

export default function App() {
  const { data, loading, error } = useAfpData()

  if (loading) return <LoadingState />
  if (error)   return <ErrorState error={error} />

  const { rentabilidades, comisiones, financiero, afiliados } = data

  // Extract the last data month from rentabilidades for the data-freshness label
  const lastMonthLabel = rentabilidades
    ? Object.values(rentabilidades)[0]?.last_month_label
    : null

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Top accent bar */}
      <div className="h-1 bg-gradient-to-r from-blue-700 via-blue-400 to-blue-600" />

      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between gap-4">

          {/* Brand */}
          <div className="flex items-center gap-2 min-w-0">
            {/* Mini bar-chart icon — all bars use brand blue-600 with opacity for depth */}
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="shrink-0">
              <rect x="1"  y="10" width="4" height="9"  rx="1" fill="#2563eb" opacity="0.5" />
              <rect x="8"  y="5"  width="4" height="14" rx="1" fill="#2563eb" opacity="0.75" />
              <rect x="15" y="1"  width="4" height="18" rx="1" fill="#2563eb" />
            </svg>
            <div className="min-w-0">
              <span className="font-bold text-gray-900 text-sm sm:text-base">Tu Pensión en Datos</span>
              <span className="text-xs text-gray-400 ml-2 hidden sm:inline">
                Superintendencia de Pensiones
              </span>
            </div>
          </div>

          {/* Nav */}
          <nav className="flex items-center gap-1 sm:gap-3 text-xs text-gray-500 shrink-0">
            <a href="#rentabilidad" className="px-2 py-1 rounded hover:bg-gray-100 hover:text-gray-800 transition-colors whitespace-nowrap">
              <span className="hidden sm:inline">Rentabilidad</span>
              <span className="sm:hidden">Rent.</span>
            </a>
            <a href="#comisiones" className="px-2 py-1 rounded hover:bg-gray-100 hover:text-gray-800 transition-colors whitespace-nowrap">Comisiones</a>
            <a href="#financiero" className="px-2 py-1 rounded hover:bg-gray-100 hover:text-gray-800 transition-colors whitespace-nowrap">
              <span className="hidden sm:inline">AFP como negocio</span>
              <span className="sm:hidden">Negocio</span>
            </a>
          </nav>

        </div>
      </header>

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-4 py-8">

        {/* Hero */}
        <div className="mb-8 bg-blue-50 border border-blue-100 rounded-2xl px-4 py-6 sm:px-6 sm:py-8">
          <h1 className="text-2xl sm:text-3xl font-black text-gray-900 mb-2">
            ¿Cómo está tu pensión?
          </h1>
          <p className="text-gray-500 max-w-xl">
            Datos reales del sistema AFP chileno, explicados en lenguaje simple.
            Sin jerga financiera. Fuente:{' '}
            <a
              href="https://www.spensiones.cl"
              target="_blank"
              rel="noreferrer"
              className="underline hover:text-blue-700"
            >
              Superintendencia de Pensiones
            </a>.
          </p>
          <div className="flex gap-4 mt-3 text-xs text-gray-400 flex-wrap">
            <span>📅 Consultado el {fechaHoy()}</span>
            {lastMonthLabel && (
              <span>📊 Datos hasta {lastMonthLabel}</span>
            )}
          </div>
        </div>

        <KpiCards comisiones={comisiones} afiliados={afiliados} />

        <div className="bg-white rounded-2xl shadow-sm mb-6">
          <FondosExplainer />
        </div>

        <div id="rentabilidad">
          <div className="bg-white rounded-2xl shadow-sm mb-6">
            <RankingTable rentabilidades={rentabilidades} />
          </div>
          <div className="bg-white rounded-2xl shadow-sm mb-6">
            <RentabilidadChart rentabilidades={rentabilidades} />
          </div>
        </div>

        <div id="comisiones">
          <div className="bg-white rounded-2xl shadow-sm mb-6">
            <ComisionesChart comisiones={comisiones} />
          </div>
        </div>

        <div id="financiero">
          <div className="bg-white rounded-2xl shadow-sm mb-6">
            <SaludFinanciera financiero={financiero} />
          </div>
        </div>

      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-16 py-10 text-xs text-gray-400">
        <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row justify-between gap-6">

          {/* Left: data source */}
          <div className="space-y-1">
            <p className="font-medium text-gray-500">Fuente de datos</p>
            <p>Superintendencia de Pensiones de Chile —{' '}
              <a href="https://www.spensiones.cl" target="_blank" rel="noreferrer"
                className="underline hover:text-gray-600">spensiones.cl</a>
            </p>
            <p>Este sitio no está afiliado ni patrocinado por ninguna AFP.</p>
          </div>

          {/* Right: author */}
          <div className="space-y-1 sm:text-right">
            <p className="font-medium text-gray-500">Desarrollado por</p>
            <a
              href="https://www.linkedin.com/in/camilo-fuentes-toro/"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 group"
            >
              {/* LinkedIn "in" mark */}
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"
                className="text-[#0A66C2] shrink-0">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
              </svg>
              <span className="group-hover:text-gray-700 transition-colors">
                <span className="font-medium text-gray-600">Camilo Fuentes Toro</span>
              </span>
            </a>
            <p>Ingeniero Civil Industrial</p>
            <p>Operaciones Financieras · Análisis de Datos · Control de Procesos</p>
          </div>

        </div>
      </footer>

    </div>
  )
}
