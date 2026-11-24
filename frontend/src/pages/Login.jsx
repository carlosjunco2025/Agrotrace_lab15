import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { PERFIL_KEY, TOKEN_KEY, mensajeDeError } from '../api.js'
import './login.css'

/** S15: login del panel AgroTrace con token + perfil (rol/is_staff). */
function Login() {
  const navegar = useNavigate()
  const [usuario, setUsuario] = useState('')
  const [clave, setClave] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    setError('')
    setCargando(true)
    try {
      const respuesta = await api.post('login/', { username: usuario, password: clave })
      localStorage.setItem(TOKEN_KEY, respuesta.data.token)
      const perfil = await api.get('me/')
      localStorage.setItem(PERFIL_KEY, JSON.stringify(perfil.data))
      window.dispatchEvent(new Event('agrotrace-auth'))
      navegar('/dashboard')
    } catch (fallo) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(PERFIL_KEY)
      setError(mensajeDeError(fallo, 'Credenciales inválidas.'))
    } finally {
      setCargando(false)
    }
  }

  return (
    <section className="login-pantalla">
      <form className="login-tarjeta" onSubmit={enviar}>
        <span className="login-marca">AT</span>
        <h1>Ingreso a AgroTrace</h1>
        <p>Panel administrativo · autenticación con token</p>

        <label htmlFor="login-usuario">Usuario</label>
        <input
          id="login-usuario"
          name="username"
          autoComplete="username"
          value={usuario}
          onChange={(evento) => setUsuario(evento.target.value)}
          required
        />

        <label htmlFor="login-clave">Contraseña</label>
        <input
          id="login-clave"
          name="password"
          type="password"
          autoComplete="current-password"
          value={clave}
          onChange={(evento) => setClave(evento.target.value)}
          required
        />

        {error && <p className="login-error" role="alert">{error}</p>}

        <button type="submit" disabled={cargando}>
          {cargando ? 'Validando…' : 'Iniciar sesión'}
        </button>
        <small>La contraseña se verifica en Django con hash PBKDF2.</small>
      </form>
    </section>
  )
}

export default Login
