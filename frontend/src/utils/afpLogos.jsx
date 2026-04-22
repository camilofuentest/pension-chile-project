// Shared AFP logo map and component — used by RankingTable, ComisionesChart, SaludFinanciera

const AFP_LOGOS = {
  Capital:   '/logos/capital.svg',
  Cuprum:    '/logos/cuprum.png',
  Habitat:   '/logos/habitat.svg',
  Modelo:    '/logos/modelo.png',
  PlanVital: '/logos/planvital.png',
  Provida:   '/logos/provida.png',
  Uno:       '/logos/uno.svg',
}

export function AfpLogo({ afp, className = '' }) {
  const src = AFP_LOGOS[afp]
  if (!src) return <span className={`font-bold text-gray-500 text-xs ${className}`}>{afp}</span>
  return (
    <img
      src={src}
      alt={afp}
      className={`object-contain ${className}`}
      onError={e => { e.target.style.display = 'none' }}
    />
  )
}
