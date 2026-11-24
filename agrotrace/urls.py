from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalogo.api_views import CategoriaViewSet, ProductoViewSet
from comercializacion.api_views import (
    ClienteAgroViewSet,
    OrdenComercialViewSet,
    OrdenDespachoViewSet,
    PagoDespachoViewSet,
    ProductoAgroViewSet,
    ProductorAgroViewSet,
)
from pedidos.api_views import ClienteViewSet, PagoViewSet, PedidoViewSet

from .api_views import (
    EvaluacionCalidadViewSet,
    EvaluacionCalidadDetalladaViewSet,
    FundoProductorViewSet,
    LoteDetalladoViewSet,
    LoteViewSet,
)
from . import views

app_name = 'agrotrace'

router = DefaultRouter()
router.register(r'fundos', FundoProductorViewSet, basename='fundo')
router.register(
    r'evaluaciones',
    EvaluacionCalidadViewSet,
    basename='evaluacion',
)
router.register(
    r'evaluaciones-detalladas',
    EvaluacionCalidadDetalladaViewSet,
    basename='evaluacion-detallada',
)
router.register(r'lotes', LoteViewSet, basename='lote')
router.register(
    r'lotes-detallados',
    LoteDetalladoViewSet,
    basename='lote-detallado-api',
)

# Semana 14 - Parte 1: cafetería (Ejercicios 2 a 8).
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'pedidos', PedidoViewSet, basename='pedido')
router.register(r'pagos', PagoViewSet, basename='pago')

# Semana 14 - Parte 2: AgroTrace (Ejercicios 9 a 12).
router.register(r'productores-agro', ProductorAgroViewSet, basename='productor-agro')
router.register(r'clientes-agro', ClienteAgroViewSet, basename='cliente-agro')
router.register(r'productos-agro', ProductoAgroViewSet, basename='producto-agro')
router.register(
    r'ordenes-despacho',
    OrdenDespachoViewSet,
    basename='orden-despacho',
)
# S15: alias semántico "OrdenComercial" sobre la misma entidad privada.
router.register(
    r'ordenes-comerciales',
    OrdenComercialViewSet,
    basename='orden-comercial',
)
router.register(r'pagos-despacho', PagoDespachoViewSet, basename='pago-despacho')

urlpatterns = [
    # Fundos
    path('fundos/', views.fundo_list, name='fundo_list'),
    path('fundos/nuevo/', views.fundo_create, name='fundo_create'),
    path('fundos/editar/<int:pk>/', views.fundo_update, name='fundo_update'),
    path('fundos/eliminar/<int:pk>/', views.fundo_delete, name='fundo_delete'),

    # Lotes
    path('lotes/', views.lote_list, name='lote_list'),
    path('lotes/nuevo/', views.lote_create, name='lote_create'),
    path('lotes/editar/<int:pk>/', views.lote_update, name='lote_update'),
    path('lotes/eliminar/<int:pk>/', views.lote_delete, name='lote_delete'),

    # Operación Transaccional (Ejercicio 3 - Lab 07)
    path(
        'recepcion-transaccional/',
        views.recepcion_transaccional,
        name='recepcion_transaccional',
    ),

    # Reporte General (Ejercicio 6 - Lab 07)
    path('reporte/', views.reporte_general, name='reporte_general'),

    # API REST
    path('api/', include(router.urls)),
]