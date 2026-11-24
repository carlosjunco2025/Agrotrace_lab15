/* eslint-disable react-refresh/only-export-components -- contexto compartido por el panel */
import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { PERFIL_KEY, TOKEN_KEY, limpiarSesion } from './api.js'

const AuthContext = createContext(null)

function leerPerfil() {
  try {
    return JSON.parse(localStorage.getItem(PERFIL_KEY) || 'null')
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [perfil, setPerfil] = useState(leerPerfil)

  useEffect(() => {
    const sincronizar = () => {
      setToken(localStorage.getItem(TOKEN_KEY))
      setPerfil(leerPerfil())
    }
    window.addEventListener('agrotrace-auth', sincronizar)
    window.addEventListener('storage', sincronizar)
    return () => {
      window.removeEventListener('agrotrace-auth', sincronizar)
      window.removeEventListener('storage', sincronizar)
    }
  }, [])

  const cerrarSesion = () => {
    limpiarSesion()
    setToken(null)
    setPerfil(null)
    window.location.assign('/login')
  }

  const valor = useMemo(() => ({
    token,
    perfil,
    autenticado: Boolean(token),
    esAdmin: Boolean(perfil?.is_staff),
    cerrarSesion,
  }), [token, perfil])

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const contexto = useContext(AuthContext)
  if (!contexto) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return contexto
}

export function RutaProtegida({ children }) {
  const { autenticado } = useAuth()
  return autenticado ? children : <Navigate to="/login" replace />
}
