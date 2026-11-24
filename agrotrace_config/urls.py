from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

from agrotrace.api_views import api_me
from agrotrace.urls import router

# Semana 13: rutas de las apps de estructura inicial. Cada app expone un
# endpoint de metadata hasta que los modelos de negocio se escriban en S14.
urlpatterns = [
    path('admin/', admin.site.urls),
    # Semana 15: login con token y perfil del usuario autenticado.
    path('api/login/', obtain_auth_token, name='api_login'),
    path('api/me/', api_me, name='api_me'),
    path('api/', include(router.urls)),
    path('api/catalogo/', include('catalogo.urls')),
    # El CRUD real de pedidos lo publica el DefaultRouter en /api/pedidos/.
    # Esta ruta de metadata de la Semana 13 se conserva en un subprefijo.
    path('api/pedidos/modulo/', include('pedidos.urls')),
    path('api/productores/', include('productores.urls')),
    path('api/inventario/', include('inventario.urls')),
    path('api/comercializacion/', include('comercializacion.urls')),
    path('api/trazabilidad/', include('trazabilidad.urls')),
    path('agrotrace/', include('agrotrace.urls')),
]
