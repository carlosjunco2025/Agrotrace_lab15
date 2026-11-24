"""Semana 14 · Ejercicio 11: serializers del dominio AgroTrace."""

import uuid
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from .models import (
    ClienteAgro,
    DetalleOrdenDespacho,
    OrdenDespacho,
    PagoDespacho,
    ProductoAgro,
    ProductorAgro,
)


class ProductorAgroSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductorAgro
        fields = ('id', 'nombre', 'ruc', 'region', 'activo')


class ClienteAgroSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteAgro
        fields = ('id', 'nombre', 'documento', 'email')


class ProductoAgroSerializer(serializers.ModelSerializer):
    """Regla de negocio equivalente a validate_precio de la cafetería."""

    productor_nombre = serializers.CharField(source='productor.nombre', read_only=True)

    class Meta:
        model = ProductoAgro
        fields = (
            'id', 'codigo', 'nombre', 'stock_kg', 'precio_kg', 'activo',
            'productor', 'productor_nombre',
        )

    def validate_precio_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError('El precio por kg debe ser mayor que cero.')
        return value

    def validate_stock_kg(self, value):
        if value < 0:
            raise serializers.ValidationError('El stock no puede ser negativo.')
        return value


class DetalleOrdenDespachoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = DetalleOrdenDespacho
        fields = (
            'id', 'producto', 'producto_nombre', 'cantidad_kg',
            'precio_unitario_kg', 'subtotal',
        )


class PagoDespachoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagoDespacho
        fields = ('id', 'monto', 'estado', 'referencia', 'fecha_pago')
        read_only_fields = fields


class OrdenDespachoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    detalles = DetalleOrdenDespachoSerializer(many=True, read_only=True)
    pago = PagoDespachoSerializer(read_only=True)
    registrado_por = serializers.PrimaryKeyRelatedField(read_only=True)
    precio_unitario_aplicado = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
    )
    total_valorizado = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True,
    )
    fecha_registro = serializers.DateTimeField(read_only=True)

    class Meta:
        model = OrdenDespacho
        fields = (
            'id', 'cliente', 'cliente_nombre', 'estado', 'total',
            'cantidad_sacos', 'precio_unitario_aplicado', 'total_valorizado',
            'registrado_por', 'fecha_registro', 'fecha_creacion',
            'detalles', 'pago',
        )
        read_only_fields = (
            'estado', 'total', 'precio_unitario_aplicado', 'total_valorizado',
            'registrado_por', 'fecha_registro', 'fecha_creacion',
        )


class OrdenComercialSerializer(OrdenDespachoSerializer):
    """S15: alta de OrdenComercial con precio y total calculados en BD."""

    producto = serializers.PrimaryKeyRelatedField(
        queryset=ProductoAgro.objects.all(), write_only=True,
    )
    estado = serializers.ChoiceField(choices=OrdenDespacho.ESTADOS, required=False)

    class Meta(OrdenDespachoSerializer.Meta):
        fields = OrdenDespachoSerializer.Meta.fields + ('producto',)
        read_only_fields = tuple(
            campo for campo in OrdenDespachoSerializer.Meta.read_only_fields
            if campo != 'estado'
        )

    def validate_cantidad_sacos(self, value):
        if not 1 <= value <= 500:
            raise serializers.ValidationError('La cantidad de sacos debe estar entre 1 y 500.')
        return value

    def validate_estado(self, value):
        permitidos = [estado for estado, _ in OrdenDespacho.ESTADOS]
        if value not in permitidos:
            raise serializers.ValidationError(f'Estado no permitido: {value}.')
        return value

    def validate_producto(self, producto):
        if not producto.activo:
            raise serializers.ValidationError('El producto no está activo.')
        sacos = self.initial_data.get('cantidad_sacos', 0)
        try:
            sacos = int(sacos)
        except (TypeError, ValueError):
            return producto
        if producto.stock_kg < Decimal(sacos * 20):
            raise serializers.ValidationError(
                f'Stock insuficiente: se requieren {sacos * 20} kg y hay {producto.stock_kg} kg.'
            )
        return producto

    def _calcular(self, datos):
        producto = datos.pop('producto')
        precio_saco = producto.precio_kg * Decimal('20')
        datos['precio_unitario_aplicado'] = precio_saco
        datos['total_valorizado'] = Decimal(datos['cantidad_sacos']) * precio_saco
        datos['total'] = datos['total_valorizado']
        return datos, producto

    @transaction.atomic
    def create(self, validated_data):
        datos, producto = self._calcular(validated_data)
        orden = OrdenDespacho.objects.create(**datos)
        DetalleOrdenDespacho.objects.create(
            orden=orden,
            producto=producto,
            cantidad_kg=Decimal(datos['cantidad_sacos'] * 20),
            precio_unitario_kg=producto.precio_kg,
        )
        ProductoAgro.objects.filter(pk=producto.pk).update(
            stock_kg=F('stock_kg') - Decimal(datos['cantidad_sacos'] * 20),
        )
        PagoDespacho.objects.create(
            orden=orden,
            monto=datos['total_valorizado'],
            estado=PagoDespacho.ESTADO_PAGADO,
            referencia=f'AGRO-{uuid.uuid4().hex[:12].upper()}',
        )
        return orden

    @transaction.atomic
    def update(self, instance, validated_data):
        datos, producto = self._calcular(validated_data)
        for campo, valor in datos.items():
            setattr(instance, campo, valor)
        instance.save()
        return instance


class ItemDespachoSerializer(serializers.Serializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=ProductoAgro.objects.all())
    cantidad_kg = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
    )

    def validate_cantidad_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad en kg debe ser mayor que cero.')
        return value


class CrearOrdenDespachoSerializer(serializers.Serializer):
    cliente = serializers.PrimaryKeyRelatedField(queryset=ClienteAgro.objects.all())
    items = serializers.ListField(child=ItemDespachoSerializer(), allow_empty=False)

    def validate_items(self, items):
        productos = [item['producto'].pk for item in items]
        if len(productos) != len(set(productos)):
            raise serializers.ValidationError(
                'No se puede repetir un producto en la misma orden.'
            )
        return items
