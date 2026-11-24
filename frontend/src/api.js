import axios from 'axios'

export const TOKEN_KEY = 'agrotrace_token'
export const PERFIL_KEY = 'agrotrace_perfil'

/** Borra token y perfil: se usa al cerrar sesión y ante un 401. */
export function limpiarSesion() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(PERFIL_KEY)
  window.dispatchEvent(new Event('agrotrace-auth'))
}

// Instancia única de Axios para toda la aplicación.
// El backend de Django se levanta en el puerto 8000 con el prefijo /api/.
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/',
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Convierte el cuerpo de error de DRF en un objeto plano
 * { campo: "mensaje" } para pintarlo junto a cada input.
 */
export function normalizarErrores(respuesta) {
  const datos = respuesta?.data

  if (!datos || typeof datos !== 'object') {
    return { general: 'No se pudo completar la operación.' }
  }

  return Object.entries(datos).reduce((errores, [campo, valor]) => {
    errores[campo] = Array.isArray(valor) ? valor.join(' ') : String(valor)
    return errores
  }, {})
}

/**
 * Mensaje legible para errores de red, timeout o respuestas inesperadas.
 */
export function mensajeDeError(error, respaldo = 'Ocurrió un error inesperado.') {
  if (error?.code === 'ECONNABORTED') {
    return 'El servidor tardó demasiado en responder (timeout de 5 s).'
  }

  if (!error?.response) {
    return 'No se pudo conectar con Django en http://127.0.0.1:8000. Verifica que el servidor esté encendido y que CORS esté configurado.'
  }

  if (typeof error.response.data === 'string') {
    return error.response.data
  }

  const errores = normalizarErrores(error.response)
  return errores.general ?? errores.detail ?? respaldo
}

// S15: adjunta el token a TODAS las peticiones y reacciona al 401.
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      config.headers.Authorization = `Token ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

api.interceptors.response.use(
  (respuesta) => respuesta,
  (error) => {
    if (
      error?.response?.status === 401 &&
      !window.location.pathname.startsWith('/login')
    ) {
      limpiarSesion()
      window.location.assign('/login')
    }
    return Promise.reject(error)
  },
)

export default api
