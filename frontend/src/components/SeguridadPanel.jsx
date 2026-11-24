import { useEffect, useState } from 'react'
import api from '../api.js'
import { useAuth } from '../auth.jsx'
import './seguridad.css'

const TEXTO_XSS = "<script>alert('XSS')</script>"

/** S15: control de UI por perfil + demostración de escape automático de React. */
function SeguridadPanel() {
  const { perfil, esAdmin } = useAuth()
  const [lotes, setLotes] = useState([])
  const [mensaje, setMensaje] = useState('')

  useEffect(() => {
    api.get('lotes/')
      .then((respuesta) => setLotes(respuesta.data.slice(0, 3)))
      .catch(() => setLotes([]))
  }, [])

  return (
    <section className="seguridad-panel">
      <div className="seguridad-panel__cabecera">
        <div>
          <h2>Control de acceso AgroTrace</h2>
          <p>
            Sesión: <strong>{perfil?.username || '—'}</strong> · rol{' '}
            <strong>{perfil?.rol || '—'}</strong> · is_staff:{' '}
            <strong>{String(Boolean(perfil?.is_staff))}</strong>
          </p>
        </div>
        <span className={`perfil-chispa ${esAdmin ? 'perfil-chispa--admin' : ''}`}>
          {esAdmin ? 'ADMINISTRADOR' : 'OPERADOR'}
        </span>
      </div>

      <p className="xss-demo" data-prueba="xss">
        Texto con etiquetas (React lo renderiza como texto plano): {TEXTO_XSS}
      </p>

      <h3>Lotes recientes</h3>
      <ul className="seguridad-lotes">
        {lotes.map((lote) => (
          <li key={lote.id}>
            <span>{lote.codigo_lote} · {lote.toneladas_brutas} TN</span>
            {esAdmin && (
              <button
                type="button"
                className="boton-eliminar"
                onClick={() => setMensaje(`DELETE autorizado para el lote ${lote.id}`)}
              >
                Eliminar
              </button>
            )}
          </li>
        ))}
      </ul>
      {!esAdmin && (
        <p className="seguridad-aviso">
          Botón Eliminar oculto: el perfil Operador no tiene permiso de borrado.
        </p>
      )}
      {mensaje && <p className="seguridad-ok">{mensaje}</p>}
      <small>El servidor es la autoridad: React solo adapta la interfaz.</small>
    </section>
  )
}

export default SeguridadPanel
