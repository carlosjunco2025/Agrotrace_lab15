"""Semana 15 · Pruebas de seguridad de AgroTrace (hash, token, permisos, IDOR).

Ejecutar: python manage.py test agrotrace.tests_seguridad_s15 -v 2
"""

from decimal import Decimal

from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from agrotrace.models import FundoProductor, LoteRecepcionado, PerfilUsuario
from comercializacion.models import ClienteAgro, OrdenDespacho

CLAVE = 'AgroTrace.S15.2026!'


class SeguridadAgroTraceTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='admin_agro', password=CLAVE, is_staff=True, is_superuser=True,
        )
        self.op1 = User.objects.create_user(username='operador_agro', password=CLAVE)
        self.op2 = User.objects.create_user(username='operador_agro2', password=CLAVE)
        PerfilUsuario.objects.create(usuario=self.admin, rol=PerfilUsuario.ROL_ADMINISTRADOR)
        PerfilUsuario.objects.create(usuario=self.op1, rol=PerfilUsuario.ROL_OPERADOR)
        PerfilUsuario.objects.create(usuario=self.op2, rol=PerfilUsuario.ROL_OPERADOR)

        self.fundo = FundoProductor.objects.create(
            nombre_fundo='Fundo Prueba S15',
            propietario_dni_ruc='20999000999',
            hectareas=Decimal('100.00'),
            stock_disponible_tn=Decimal('500.00'),
            precio_referencia_tn=Decimal('850.00'),
        )
        self.lote = LoteRecepcionado.objects.create(
            fundo=self.fundo,
            codigo_lote='LOT-QA-001',
            toneladas_brutas=Decimal('10.00'),
            registrado_por=self.op1,
        )
        cliente = ClienteAgro.objects.create(
            nombre='Cliente QA', documento='20999000998',
        )
        self.orden_op1 = OrdenDespacho.objects.create(
            cliente=cliente, registrado_por=self.op1, total=Decimal('100.00'),
        )
        self.orden_op2 = OrdenDespacho.objects.create(
            cliente=cliente, registrado_por=self.op2, total=Decimal('200.00'),
        )

    def autenticar(self, usuario):
        client = APIClient()
        respuesta = client.post(
            '/api/login/',
            {'username': usuario.username, 'password': CLAVE},
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        client.credentials(HTTP_AUTHORIZATION=f'Token {respuesta.data["token"]}')
        return client

    def test_password_es_hash_y_authenticate(self):
        self.op1.refresh_from_db()
        self.assertTrue(self.op1.password.startswith('pbkdf2_sha256$'))
        self.assertTrue(self.op1.check_password(CLAVE))
        self.assertFalse(self.op1.check_password('clave-erronea'))
        self.assertEqual(authenticate(username='operador_agro', password=CLAVE), self.op1)
        self.assertIsNone(authenticate(username='operador_agro', password='clave-erronea'))

    def test_login_correcto_incorrecto_y_sin_token(self):
        client = APIClient()
        self.assertEqual(client.get('/api/lotes/').status_code, status.HTTP_401_UNAUTHORIZED)
        mala = client.post(
            '/api/login/',
            {'username': 'operador_agro', 'password': 'clave-erronea'},
            format='json',
        )
        self.assertEqual(mala.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.autenticar(self.op1).get('/api/lotes/').status_code,
            status.HTTP_200_OK,
        )

    def test_me_no_expone_password(self):
        respuesta = self.autenticar(self.op1).get('/api/me/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['rol'], 'OPERADOR')
        self.assertFalse(respuesta.data['is_staff'])
        self.assertNotIn('password', respuesta.data)

    def test_operador_no_puede_eliminar_lote_admin_si(self):
        self.assertEqual(
            self.autenticar(self.op1).delete(f'/api/lotes/{self.lote.pk}/').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.autenticar(self.admin).delete(f'/api/lotes/{self.lote.pk}/').status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def test_idor_orden_ajena_devuelve_404(self):
        operador = self.autenticar(self.op1)
        self.assertEqual(
            operador.get(f'/api/ordenes-comerciales/{self.orden_op2.pk}/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            operador.get(f'/api/ordenes-comerciales/{self.orden_op1.pk}/').status_code,
            status.HTTP_200_OK,
        )
        admin = self.autenticar(self.admin)
        self.assertEqual(
            admin.get(f'/api/ordenes-comerciales/{self.orden_op2.pk}/').status_code,
            status.HTTP_200_OK,
        )

    def test_listado_ordenes_filtrado_por_usuario(self):
        respuesta = self.autenticar(self.op1).get('/api/ordenes-comerciales/')
        self.assertEqual([item['id'] for item in respuesta.data], [self.orden_op1.pk])
