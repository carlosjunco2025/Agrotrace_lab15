import PaginaBase from './PaginaBase.jsx'
import SeguridadPanel from '../components/SeguridadPanel.jsx'

function DashboardPage() {
  return (
    <>
    <PaginaBase
      etiqueta="Parte 2 · proyecto integrador AgroTrace"
      titulo="Panel de control"
      descripcion="Vista de entrada del panel B2B de trazabilidad y comercialización agroindustrial. Resume qué módulos ya existen y cuáles se construyen en S14-S16."
      rutaReact="/dashboard"
      rutaApi="/api/catalogo/ · /api/inventario/ · /api/productores/"
      modulo="agrotrace (base) + catalogo, pedidos, productores, inventario, comercializacion, trazabilidad"
      estado="Construido (estructura S13)"
      entidadPrincipal="LoteRecepcionado"
      entidades={['FundoProductor', 'EvaluacionCalidadLote', 'PedidoComercial']}
      tareas={[
        'Módulos S8-S12: fundos, lotes y evaluaciones ya funcionan con DRF.',
        'Apps S13 creadas y registradas; check sin errores.',
        'S14: modelos de negocio; S15: pedidos y pagos; S16: trazabilidad.',
      ]}
    />
    <SeguridadPanel />
    </>
  )
}

export default DashboardPage
