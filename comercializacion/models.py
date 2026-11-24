"""Semana 14 · Ejercicios 9 y 10: componentes de AgroTrace.

Entidad principal: ProductoAgro (equivalente a Producto en la cafetería).
Su operación principal es OrdenDespacho + DetalleOrdenDespacho + PagoDespacho.

Criterios de on_delete aplicados:
  * PROTECT en catálogos maestros (productor, cliente, producto) para no
    destruir el histórico de una orden de despacho;
  * CASCADE en las tablas dependientes de la cabecera (detalle, pago), que
    no tienen sentido si la orden desaparece.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class ProductorAgro(models.Model):
    nombre = models.CharField(max_length=120)
    ruc = models.CharField(max_length=20, unique=True)
    region = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ClienteAgro(models.Model):
    nombre = models.CharField(max_length=120)
    documento = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ProductoAgro(models.Model):
    """Entidad principal de AgroTrace: lote/producto listo para despachar."""

    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=120)
    # Equivalente a Producto.precio / Producto.stock, en unidades de la operación agro.
    stock_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_kg = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)
    productor = models.ForeignKey(
        ProductorAgro,
        on_delete=models.PROTECT,
        related_name='productos',
    )

    class Meta:
        ordering = ['codigo']

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class OrdenDespacho(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_PAGADO = 'PAGADO'
    ESTADO_ENTREGADO = 'ENTREGADO'
    ESTADO_CANCELADO = 'CANCELADO'
    ESTADOS = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_PAGADO, 'Pagado'),
        (ESTADO_ENTREGADO, 'Entregado'),
        (ESTADO_CANCELADO, 'Cancelado'),
    ]

    cliente = models.ForeignKey(
        ClienteAgro,
        on_delete=models.PROTECT,
        related_name='ordenes',
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PENDIENTE)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # S15: OrdenComercial privada por usuario y valorización calculada en servidor.
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_registradas',
    )
    cantidad_sacos = models.PositiveIntegerField(default=0)
    precio_unitario_aplicado = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
    )
    total_valorizado = models.DecimalField(
        max_digits=14, decimal_places=2, default=0.00,
    )
    fecha_registro = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['-fecha_creacion', '-id']

    def __str__(self):
        return f'Despacho #{self.pk} - {self.cliente.nombre} ({self.estado})'


class DetalleOrdenDespacho(models.Model):
    orden = models.ForeignKey(
        OrdenDespacho,
        on_delete=models.CASCADE,
        related_name='detalles',
    )
    producto = models.ForeignKey(
        ProductoAgro,
        on_delete=models.PROTECT,
        related_name='detalles_despacho',
    )
    cantidad_kg = models.DecimalField(max_digits=12, decimal_places=2)
    precio_unitario_kg = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.cantidad_kg} kg de {self.producto.nombre}'

    @property
    def subtotal(self):
        return self.cantidad_kg * self.precio_unitario_kg


class PagoDespacho(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_PAGADO = 'PAGADO'
    ESTADO_FALLIDO = 'FALLIDO'
    ESTADOS = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_PAGADO, 'Pagado'),
        (ESTADO_FALLIDO, 'Fallido'),
    ]

    orden = models.OneToOneField(
        OrdenDespacho,
        on_delete=models.CASCADE,
        related_name='pago',
    )
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PENDIENTE)
    referencia = models.CharField(max_length=40, unique=True)
    fecha_pago = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.referencia} - {self.estado}'
