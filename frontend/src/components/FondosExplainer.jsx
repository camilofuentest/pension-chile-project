const FONDOS = [
  {
    letra:  'A',
    nombre: 'Más arriesgado',
    color:  'bg-red-100 border-red-400',
    para:   'Más de 20 años para jubilar. Mayor potencial de ganancia, pero puede caer fuerte en crisis.',
  },
  {
    letra:  'B',
    nombre: 'Arriesgado',
    color:  'bg-orange-100 border-orange-400',
    para:   'Entre 10 y 20 años para jubilar. Mezcla de acciones y bonos.',
  },
  {
    letra:  'C',
    nombre: 'Equilibrado',
    color:  'bg-yellow-100 border-yellow-400',
    para:   'El fondo más común. Punto de partida para la mayoría de afiliados.',
  },
  {
    letra:  'D',
    nombre: 'Conservador',
    color:  'bg-blue-100 border-blue-400',
    para:   'Menos de 10 años para jubilar. Prioriza proteger lo acumulado sobre ganar más.',
  },
  {
    letra:  'E',
    nombre: 'Más conservador',
    color:  'bg-green-100 border-green-400',
    para:   'Cerca de jubilar o ya jubilado. Solo bonos y depósitos — menor volatilidad, aunque puede caer en ciertos ciclos de tasas.',
  },
]

export default function FondosExplainer() {
  return (
    <section className="px-4 py-6 sm:px-6">
      <h2 className="text-xl font-bold text-gray-800 mb-1 border-l-4 border-blue-600 pl-3">Los 5 fondos de pensión</h2>
      <p className="text-sm text-gray-500 mb-4">
        Tu AFP invierte tu dinero en uno de estos fondos según tu edad y perfil de riesgo.
        De izquierda a derecha: más riesgo y potencial → más seguridad y estabilidad.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
        {FONDOS.map(f => (
          <div key={f.letra} className={`rounded-xl border-l-4 p-4 ${f.color}`}>
            <div className="text-3xl font-black text-gray-700 mb-0.5">Fondo {f.letra}</div>
            <div className="text-xs font-semibold text-gray-600 mb-2">{f.nombre}</div>
            <p className="text-xs text-gray-700">{f.para}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
