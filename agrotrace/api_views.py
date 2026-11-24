from django.contrib.auth import get_user_model

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import EvaluacionCalidadLote, FundoProductor, LoteRecepcionado
from .permissions import PuedeGestionarAgrotrace
from .serializers import (
    EvaluacionCalidadSerializer,
    EvaluacionCalidadDetalladaSerializer,
    FundoProductorSerializer,
    LoteDetalladoSerializer,
    LoteSimpleSerializer,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_me(request):
    """Perfil del usuario autenticado; nunca expone password ni hash."""
    usuario = get_user_model().objects.get(pk=request.user.pk)
    perfil = getattr(usuario, 'perfil_agrotrace', None)
    return Response({
        'id': usuario.id,
        'username': usuario.username,
        'email': usuario.email,
        'is_staff': usuario.is_staff,
        'rol': perfil.rol if perfil else (
            'ADMINISTRADOR' if usuario.is_superuser else 'OPERADOR'
        ),
    }, status=status.HTTP_200_OK)


class PermisosPorAccionMixin:
    """GET autenticado; crear/editar gestores; borrar solo administrador."""

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), IsAdminUser()]
        if self.action in {'create', 'update', 'partial_update'}:
            return [IsAuthenticated(), PuedeGestionarAgrotrace()]
        return [IsAuthenticated()]


class EstadoFilterMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado_evaluacion=estado)
        return queryset


class FundoProductorViewSet(PermisosPorAccionMixin, viewsets.ModelViewSet):
    queryset = FundoProductor.objects.all()
    serializer_class = FundoProductorSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre_fundo', 'propietario_dni_ruc']
    ordering_fields = ['hectareas', 'id']


class EvaluacionCalidadViewSet(PermisosPorAccionMixin, viewsets.ModelViewSet):
    queryset = EvaluacionCalidadLote.objects.select_related('lote')
    serializer_class = EvaluacionCalidadSerializer


class EvaluacionCalidadDetalladaViewSet(PermisosPorAccionMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = EvaluacionCalidadDetalladaSerializer

    def get_queryset(self):
        queryset = EvaluacionCalidadLote.objects.select_related(
            'lote',
            'lote__fundo',
        )
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(lote__estado_evaluacion=estado)
        return queryset

    @action(detail=False, methods=['get'])
    def aprobados(self, request):
        evaluaciones_aprobadas = self.get_queryset().filter(
            lote__in=LoteRecepcionado.objects.aprobados(),
        )
        serializer = self.get_serializer(evaluaciones_aprobadas, many=True)
        return Response(serializer.data)


class LoteViewSet(PermisosPorAccionMixin, EstadoFilterMixin, viewsets.ModelViewSet):
    queryset = LoteRecepcionado.objects.all()
    serializer_class = LoteSimpleSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['codigo_lote', 'fundo__nombre_fundo']
    ordering_fields = ['toneladas_brutas', 'id']

    def perform_create(self, serializer):
        serializer.save(registrado_por=self.request.user)

    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        lotes_pendientes = self.get_queryset().pendientes()
        serializer = self.get_serializer(lotes_pendientes, many=True)
        return Response(serializer.data)


class LoteDetalladoViewSet(PermisosPorAccionMixin, EstadoFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = LoteDetalladoSerializer
    queryset = LoteRecepcionado.objects.select_related(
        'fundo',
        'evaluacion_calidad',
    ).prefetch_related(
        'certificacionlote_set__certificacion',
    )
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['codigo_lote', 'fundo__nombre_fundo']
    ordering_fields = ['toneladas_brutas', 'fecha_ingreso', 'id']

    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        lotes_pendientes = self.get_queryset().pendientes()
        serializer = self.get_serializer(lotes_pendientes, many=True)
        return Response(serializer.data)
