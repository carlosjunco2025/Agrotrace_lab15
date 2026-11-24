import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import './App.css'
import './pages/pages.css'
import ListaPractica from './practica/ListaPractica.jsx'
import PanelLotes from './components/PanelLotes.jsx'
import ProductosPage from './pages/ProductosPage.jsx'
import ProductosAgroPage from './pages/ProductosAgroPage.jsx'
import ProductoAgroDetallePage from './pages/ProductoAgroDetallePage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import ProductoresPage from './pages/ProductoresPage.jsx'
import LotesPage from './pages/LotesPage.jsx'
import PedidosPage from './pages/PedidosPage.jsx'
import TrazabilidadPage from './pages/TrazabilidadPage.jsx'
import Login from './pages/Login.jsx'
import { AuthProvider, RutaProtegida, useAuth } from './auth.jsx'

const ENLACES = [
  { grupo: 'General', rutas: [{ to: '/', texto: 'Inicio' }] },
  {
    grupo: 'Parte 1 · práctica',
    rutas: [
      { to: '/practica', texto: 'Lista' },
      { to: '/productos', texto: 'Productos' },
    ],
  },
  {
    grupo: 'Parte 2 · AgroTrace',
    rutas: [
      { to: '/dashboard', texto: 'Dashboard' },
      { to: '/productores', texto: 'Productores' },
      { to: '/lotes', texto: 'Lotes' },
      { to: '/productos-agro', texto: 'Catálogo Agro' },
      { to: '/pedidos', texto: 'Pedidos' },
      { to: '/trazabilidad', texto: 'Trazabilidad' },
    ],
  },
  {
    grupo: 'S12',
    rutas: [{ to: '/panel', texto: 'Panel CRUD' }],
  },
]

function enlace({ isActive }) {
  return `app-tab${isActive ? ' app-tab--active' : ''}`
}

function SinRuta() {
  return (
    <section className="module sin-ruta">
      <h1>Ruta no encontrada</h1>
      <p>Usa el menú superior para elegir un módulo del laboratorio.</p>
    </section>
  )
}

function Shell() {
  const { perfil, autenticado, cerrarSesion } = useAuth()
  const proteger = (elemento) => <RutaProtegida>{elemento}</RutaProtegida>

  return (
      <div className="app-shell">
        <nav className="app-nav" aria-label="Navegación del laboratorio">
          <div className="app-nav__inner">
            <div className="brand">
              <span className="brand-mark" aria-hidden="true">
                AT
              </span>
              <div>
                <strong>AgroTrace</strong>
                <span>Semana 15 · Panel seguro con token y perfiles</span>
              </div>
            </div>

            <div className="app-tabs" role="group" aria-label="Rutas de la aplicación">
              {ENLACES.map((grupo) => (
                <div className="nav-grupo" key={grupo.grupo}>
                  <span className="nav-grupo__etiqueta">{grupo.grupo}</span>
                  {grupo.rutas.map((ruta) => (
                    <NavLink
                      key={ruta.to}
                      to={ruta.to}
                      end={ruta.to === '/'}
                      className={enlace}
                    >
                      {ruta.texto}
                    </NavLink>
                  ))}
                </div>
              ))}
            </div>

            <div className="app-sesion">
              {autenticado ? (
                <>
                  <span className="app-usuario">
                    {perfil?.username} · {perfil?.rol}
                  </span>
                  <button type="button" onClick={cerrarSesion} className="app-logout">
                    Cerrar sesión
                  </button>
                </>
              ) : (
                <NavLink to="/login" className="app-tab">Ingresar</NavLink>
              )}
            </div>
          </div>
        </nav>

        <main className="app-main">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<DashboardPage />} />
            <Route path="/dashboard" element={proteger(<DashboardPage />)} />
            <Route path="/practica" element={<ListaPractica />} />
            <Route path="/productos" element={<ProductosPage />} />
            <Route path="/productos-agro" element={proteger(<ProductosAgroPage />)} />
            <Route
              path="/productos-agro/:id"
              element={proteger(<ProductoAgroDetallePage />)}
            />
            <Route path="/panel" element={proteger(<PanelLotes />)} />
            <Route path="/productores" element={proteger(<ProductoresPage />)} />
            <Route path="/lotes" element={proteger(<LotesPage />)} />
            <Route path="/pedidos" element={proteger(<PedidosPage />)} />
            <Route path="/trazabilidad" element={proteger(<TrazabilidadPage />)} />
            <Route path="*" element={<SinRuta />} />
          </Routes>
        </main>

        <footer className="app-footer">
          <span>AgroTrace · Desarrollo de Aplicaciones Empresariales</span>
          <span>Laboratorio 15 · Seguridad por capas y control de perfiles</span>
        </footer>
      </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
