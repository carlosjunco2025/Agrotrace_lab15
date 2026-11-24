"""Semana 15 · Permisos por perfil del panel AgroTrace."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import PerfilUsuario


class PuedeGestionarAgrotrace(BasePermission):
    """Lectura para cualquier usuario autenticado; escritura para gestores."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        perfil = getattr(request.user, 'perfil_agrotrace', None)
        return bool(
            request.user.is_staff
            or (perfil and perfil.rol in (
                PerfilUsuario.ROL_ADMINISTRADOR,
                PerfilUsuario.ROL_OPERADOR,
            ))
        )
