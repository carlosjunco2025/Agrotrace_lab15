"""Semana 15 · Semilla de seguridad de AgroTrace.

Uso:
    python manage.py seed_seguridad_s15

Las contraseñas nunca se escriben en la base de datos: se entregan a
User.objects.create_user(), que las convierte en hash PBKDF2. La clave de
demostración puede sobreescribirse con AGROTRACE_DEMO_PASSWORD.
"""

import os
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from comercializacion.models import ClienteAgro, DetalleOrdenDespacho, OrdenDespacho, PagoDespacho, ProductoAgro, ProductorAgro
from agrotrace.models import FundoProductor, LoteRecepcionado, PerfilUsuario

User = get_user_model()

CLAVE_DEMO = os.environ.get('AGROTRACE_DEMO_PASSWORD', 'AgroTrace.S15.2026!')


class Command(BaseCommand):
    help = 'Crea usuarios, perfiles, lotes y ordenes de AgroTrace con contraseñas hasheadas'

    @transaction.atomic
    def handle(self, *args, **options):
        usuarios = {}
        for username, email, rol, staff, superuser in (
            ('admin_agro', 'admin.agro@agrotrace.pe', PerfilUsuario.ROL_ADMINISTRADOR, True, True),
            ('operador_agro', 'operador.agro@agrotrace.pe', PerfilUsuario.ROL_OPERADOR, False, False),
            ('operador_agro2', 'operador2.agro@agrotrace.pe', PerfilUsuario.ROL_OPERADOR, False, False),
        ):
            usuario, creado = User.objects.get_or_create(
                username=username,
                defaults={'email': email},
            )
            if creado:
                usuario.set_password(CLAVE_DEMO)
            usuario.is_staff = staff
            usuario.is_superuser = superuser
            usuario.save(update_fields=['email', 'is_staff', 'is_superuser', 'password'])
            usuarios[username] = usuario
            self.stdout.write(
                f'  {username}: create_user() -> password={usuario.password[:28]}... (hash PBKDF2)'
            )

        productor, _ = ProductorAgro.objects.get_or_create(
            ruc='20999000001',
            defaults={'nombre': 'Cooperativa AgroTrace', 'region': 'Cajamarca'},
        )
        fundos = {}
        for clave, nombre, stock, precio in (
            ('admin', 'Fundo Administración', Decimal('900.00'), Decimal('920.00')),
            ('op1', 'Fundo La Esperanza', Decimal('600.00'), Decimal('850.00')),
            ('op2', 'Fundo San Miguel', Decimal('450.00'), Decimal('810.00')),
        ):
            fundo, _ = FundoProductor.objects.get_or_create(
                nombre_fundo=nombre,
                defaults={
                    'propietario_dni_ruc': f'20{abs(hash(nombre)) % 10**10:010d}',
                    'hectareas': Decimal('120.00'),
                    'stock_disponible_tn': stock,
                    'precio_referencia_tn': precio,
                },
            )
            fundos[clave] = fundo

        for username, fundo in (
            ('admin_agro', fundos['admin']),
            ('operador_agro', fundos['op1']),
            ('operador_agro2', fundos['op2']),
        ):
            perfil, _ = PerfilUsuario.objects.update_or_create(
                usuario=usuarios[username],
                defaults={'rol': usuarios[username].perfil_agrotrace.rol if hasattr(usuarios[username], 'perfil_agrotrace') else PerfilUsuario.ROL_OPERADOR,
                          'fundo': fundo},
            )
            perfil.rol = PerfilUsuario.ROL_ADMINISTRADOR if username == 'admin_agro' else PerfilUsuario.ROL_OPERADOR
            perfil.save(update_fields=['rol', 'fundo'])

        lotes = (
            ('admin_agro', 'admin', 'LOT-ADM-001', Decimal('12.00')),
            ('operador_agro', 'op1', 'LOT-OP1-001', Decimal('18.50')),
            ('operador_agro', 'op1', 'LOT-OP1-002', Decimal('9.75')),
            ('operador_agro2', 'op2', 'LOT-OP2-001', Decimal('22.00')),
        )
        for username, clave_fundo, codigo, toneladas in lotes:
            fundo = fundos[clave_fundo]
            lote, _ = LoteRecepcionado.objects.get_or_create(
                codigo_lote=codigo,
                defaults={
                    'fundo': fundo,
                    'toneladas_brutas': toneladas,
                    'registrado_por': usuarios[username],
                    'cantidad_sacos': int(toneladas * 20),
                    'precio_unitario_aplicado': fundo.precio_referencia_tn,
                    'total_valorizado': toneladas * fundo.precio_referencia_tn,
                    'estado_evaluacion': 'PENDIENTE',
                },
            )
            self.stdout.write(f'  lote {lote.codigo_lote} -> {username}')

        for indice, (username, clave_fundo, codigo, doc) in enumerate((
            ('admin_agro', 'admin', 'AG-ADM', '20999000011'),
            ('operador_agro', 'op1', 'AG-OP1', '20999000012'),
            ('operador_agro2', 'op2', 'AG-OP2', '20999000013'),
        )):
            cliente, _ = ClienteAgro.objects.get_or_create(
                documento=doc,
                defaults={'nombre': f'Cliente {username}', 'email': f'cliente{indice}@agrotrace.pe'},
            )
            producto, _ = ProductoAgro.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': f'Café {codigo}',
                    'stock_kg': Decimal('1000.00'),
                    'precio_kg': fundos[clave_fundo].precio_referencia_tn / Decimal('20'),
                    'productor': productor,
                },
            )
            orden, creada = OrdenDespacho.objects.get_or_create(
                cliente=cliente,
                registrado_por=usuarios[username],
                estado=OrdenDespacho.ESTADO_PAGADO,
                defaults={
                    'cantidad_sacos': 40 + indice,
                    'precio_unitario_aplicado': producto.precio_kg * Decimal('20'),
                },
            )
            if creada:
                orden.total_valorizado = orden.cantidad_sacos * orden.precio_unitario_aplicado
                orden.total = orden.total_valorizado
                orden.save(update_fields=['total_valorizado', 'total'])
                DetalleOrdenDespacho.objects.create(
                    orden=orden,
                    producto=producto,
                    cantidad_kg=Decimal(orden.cantidad_sacos * 20),
                    precio_unitario_kg=producto.precio_kg,
                )
                PagoDespacho.objects.create(
                    orden=orden,
                    monto=orden.total_valorizado,
                    estado=PagoDespacho.ESTADO_PAGADO,
                    referencia=f'AGRO-SEED-{uuid.uuid4().hex[:10].upper()}',
                )
                ProductoAgro.objects.filter(pk=producto.pk).update(
                    stock_kg=producto.stock_kg - Decimal(orden.cantidad_sacos * 20),
                )
            self.stdout.write(
                f'  orden #{orden.pk} -> {username} | total_valorizado={orden.total_valorizado}'
            )

        self.stdout.write(self.style.SUCCESS(
            'S15 seed OK. Clave de demo enmascarada: ****  (hash guardado en la BD)'
        ))
