"""Semana 14 · Pruebas automáticas de reglas de negocio y transacciones.

Ejecutar: python manage.py test agrotrace.tests_semana14 -v 2
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.test import APITestCase

from catalogo.models import Categoria, Producto
from catalogo.serializers import ProductoSerializer
from comercializacion.models import ClienteAgro, ProductoAgro, ProductorAgro
from comercializacion.serializers import ProductoAgroSerializer
from pedidos.models import Cliente, DetallePedido, Pago, Pedido


class Semana14Tests(APITestCase):
    def setUp(self):
        # S15: la API exige autenticación por token/sesión.
        self.usuario = get_user_model().objects.create_user(
            username='qa_s14', password='Prueba.S15.2026!',
        )
        self.client.force_authenticate(user=self.usuario)
        self.categoria = Categoria.objects.create(nombre='Bebidas')
        self.producto = Producto.objects.create(
            nombre='Café de origen',
            precio=Decimal('18.50'),
            stock=10,
            categoria=self.categoria,
        )
        self.cliente = Cliente.objects.create(
            nombre='Cliente Prueba',
            documento='999888777',
        )
        self.productor = ProductorAgro.objects.create(
            nombre='Productor Prueba',
            ruc='20999000001',
            region='Cajamarca',
        )
        self.cliente_agro = ClienteAgro.objects.create(
            nombre='Exportadora Prueba',
            documento='20999000002',
        )
        self.producto_agro = ProductoAgro.objects.create(
            codigo='AG-TEST',
            nombre='Café lavado',
            stock_kg=Decimal('100.00'),
            precio_kg=Decimal('20.00'),
            productor=self.productor,
        )

    def test_serializer_rechaza_precio_cero(self):
        serializer = ProductoSerializer(
            data={
                'nombre': 'Producto inválido',
                'precio': '0.00',
                'stock': 5,
                'categoria': self.categoria.pk,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('precio', serializer.errors)

    def test_busqueda_por_nombre(self):
        Producto.objects.create(
            nombre='Capuchino',
            precio=Decimal('14.00'),
            stock=5,
            categoria=self.categoria,
        )
        respuesta = self.client.get('/api/productos/?search=Capuchino')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)

    def test_borrar_categoria_con_productos_levanta_protected_error(self):
        with self.assertRaises(ProtectedError):
            self.categoria.delete()

    def test_crear_pedido_exitoso_descuenta_stock_y_registra_pago(self):
        respuesta = self.client.post(
            '/api/pedidos/crear/',
            {
                'cliente': self.cliente.pk,
                'items': [{'producto': self.producto.pk, 'cantidad': 3}],
            },
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.producto.refresh_from_db()
        pedido = Pedido.objects.get(pk=respuesta.data['id'])

        self.assertEqual(self.producto.stock, 7)
        self.assertEqual(pedido.total, Decimal('55.50'))
        self.assertEqual(pedido.estado, Pedido.ESTADO_PAGADO)
        self.assertEqual(pedido.pago.monto, Decimal('55.50'))
        self.assertEqual(pedido.pago.estado, Pago.ESTADO_PAGADO)
        self.assertEqual(DetallePedido.objects.filter(pedido=pedido).count(), 1)

    def test_crear_pedido_sin_stock_no_cambia_la_base(self):
        respuesta = self.client.post(
            '/api/pedidos/crear/',
            {
                'cliente': self.cliente.pk,
                'items': [{'producto': self.producto.pk, 'cantidad': 999}],
            },
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
        self.assertFalse(Pedido.objects.exists())
        self.assertFalse(DetallePedido.objects.exists())
        self.assertFalse(Pago.objects.exists())

    def test_serializer_agro_rechaza_precio_cero(self):
        serializer = ProductoAgroSerializer(
            data={
                'codigo': 'AG-BAD',
                'nombre': 'Inválido',
                'stock_kg': '10.00',
                'precio_kg': '0.00',
                'productor': self.productor.pk,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('precio_kg', serializer.errors)

    def test_crear_orden_despacho_atomica(self):
        respuesta = self.client.post(
            '/api/ordenes-despacho/crear/',
            {
                'cliente': self.cliente_agro.pk,
                'items': [
                    {'producto': self.producto_agro.pk, 'cantidad_kg': '12.50'}
                ],
            },
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.producto_agro.refresh_from_db()
        self.assertEqual(self.producto_agro.stock_kg, Decimal('87.50'))
        self.assertEqual(respuesta.data['total'], '250.00')

    def test_crear_orden_sin_stock_hace_rollback(self):
        respuesta = self.client.post(
            '/api/ordenes-despacho/crear/',
            {
                'cliente': self.cliente_agro.pk,
                'items': [
                    {'producto': self.producto_agro.pk, 'cantidad_kg': '500.00'}
                ],
            },
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.producto_agro.refresh_from_db()
        self.assertEqual(self.producto_agro.stock_kg, Decimal('100.00'))
