"""Semana 14 · Ejercicio 11: ViewSets de AgroTrace y orden transaccional."""

from decimal import Decimal
import uuid

from django.db import transaction
from django.db.models import F
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import (
    ClienteAgro,
    DetalleOrdenDespacho,
    OrdenDespacho,
    PagoDespacho,
    ProductoAgro,
    ProductorAgro,
)
from .serializers import (
    ClienteAgroSerializer,
    CrearOrdenDespachoSerializer,
    OrdenComercialSerializer,
    OrdenDespachoSerializer,
    PagoDespachoSerializer,
    ProductoAgroSerializer,
    ProductorAgroSerializer,
)


class ProductorAgroViewSet(viewsets.ModelViewSet):
    queryset = ProductorAgro.objects.all()
    serializer_class = ProductorAgroSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'ruc']


class ClienteAgroViewSet(viewsets.ModelViewSet):
    queryset = ClienteAgro.objects.all()
    serializer_class = ClienteAgroSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'documento']


class ProductoAgroViewSet(viewsets.ModelViewSet):
    """Entidad principal: CRUD y búsqueda en /api/productos-agro/."""

    queryset = ProductoAgro.objects.select_related('productor')
    serializer_class = ProductoAgroSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo']


class PagoDespachoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PagoDespachoSerializer

    def get_queryset(self):
        usuario = self.request.user
        base = PagoDespacho.objects.select_related('orden')
        if usuario.is_staff:
            return base
        return base.filter(orden__registrado_por=usuario)


class OrdenComercialViewSet(viewsets.ModelViewSet):
    """OrdenComercial (OrdenDespacho): registros privados por usuario creador."""

    serializer_class = OrdenComercialSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['cliente__nombre', 'estado']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        base = OrdenDespacho.objects.select_related('cliente', 'pago').prefetch_related(
            'detalles__producto',
        )
        if self.request.user.is_staff:
            return base
        # Un operador solo ve sus propias órdenes; un ID ajeno responde 404.
        return base.filter(registrado_por=self.request.user)

    def perform_create(self, serializer):
        serializer.save(registrado_por=self.request.user)

    @action(detail=False, methods=['post'], url_path='crear')
    def crear_orden(self, request):
        """Versión AgroTrace de crear_pedido: mismo patrón, mismo atomic."""
        serializer = CrearOrdenDespachoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cliente = serializer.validated_data['cliente']
        items = serializer.validated_data['items']
        ids = [item['producto'].pk for item in items]

        with transaction.atomic():
            productos = {
                producto.pk: producto
                for producto in ProductoAgro.objects.select_for_update()
                .filter(pk__in=ids)
                .order_by('pk')
            }

            for item in items:
                producto = productos.get(item['producto'].pk)
                if producto is None:
                    raise ValidationError(
                        {'items': f'El producto {item["producto"].pk} no existe.'}
                    )
                if not producto.activo:
                    raise ValidationError(
                        {'items': f'{producto.nombre} no está activo.'}
                    )
                if producto.stock_kg < item['cantidad_kg']:
                    raise ValidationError(
                        {
                            'items': (
                                f'Stock insuficiente para {producto.nombre}: '
                                f'se solicitan {item["cantidad_kg"]} kg y hay '
                                f'{producto.stock_kg} kg.'
                            )
                        }
                    )

            total = sum(
                (
                    productos[item['producto'].pk].precio_kg * item['cantidad_kg']
                    for item in items
                ),
                Decimal('0.00'),
            )

            kg_totales = sum((item['cantidad_kg'] for item in items), Decimal('0'))
            precio_unitario = max(p.precio_kg for p in productos.values()) * Decimal('20')
            orden = OrdenDespacho.objects.create(
                cliente=cliente,
                estado=OrdenDespacho.ESTADO_PENDIENTE,
                total=total,
                registrado_por=request.user,
                cantidad_sacos=int(kg_totales / Decimal('20')),
                precio_unitario_aplicado=precio_unitario,
                total_valorizado=total,
            )
            for item in items:
                producto = productos[item['producto'].pk]
                DetalleOrdenDespacho.objects.create(
                    orden=orden,
                    producto=producto,
                    cantidad_kg=item['cantidad_kg'],
                    precio_unitario_kg=producto.precio_kg,
                )
                ProductoAgro.objects.filter(pk=producto.pk).update(
                    stock_kg=F('stock_kg') - item['cantidad_kg'],
                )

            PagoDespacho.objects.create(
                orden=orden,
                monto=total,
                estado=PagoDespacho.ESTADO_PAGADO,
                referencia=f'AGRO-{uuid.uuid4().hex[:12].upper()}',
            )
            orden.estado = OrdenDespacho.ESTADO_PAGADO
            orden.save(update_fields=['estado'])

        return Response(
            OrdenDespachoSerializer(orden).data,
            status=status.HTTP_201_CREATED,
        )


# Compatibilidad con el nombre usado en la Semana 14.
OrdenDespachoViewSet = OrdenComercialViewSet
