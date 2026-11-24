from django.conf import settings
from django.db import models
from django.utils import timezone


class CentroAcopio(models.Model):
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=150)

    def __str__(self):
        return self.nombre


class VariedadCultivo(models.Model):
    nombre_cultivo = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre_cultivo


class CertificacionAgricola(models.Model):
    nombre_certificacion = models.CharField(max_length=100)
    entidad_emisora = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre_certificacion


class FundoProductor(models.Model):
    nombre_fundo = models.CharField(max_length=100)
    propietario_dni_ruc = models.CharField(max_length=20)
    hectareas = models.DecimalField(max_digits=8, decimal_places=2)
    valido_exportacion = models.BooleanField(default=False)
    cupo_diario_lotes = models.IntegerField(default=10)
    # S15: stock y precio de referencia se leen desde la BD, nunca del cliente.
    stock_disponible_tn = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    precio_referencia_tn = models.DecimalField(max_digits=10, decimal_places=2, default=850.00)

    def __str__(self):
        return self.nombre_fundo


class PerfilUsuario(models.Model):
    """S15: rol y fundo asignado de cada usuario del panel AgroTrace."""

    ROL_ADMINISTRADOR = 'ADMINISTRADOR'
    ROL_OPERADOR = 'OPERADOR'
    ROL_PRODUCTOR = 'PRODUCTOR'
    ROLES = [
        (ROL_ADMINISTRADOR, 'Administrador'),
        (ROL_OPERADOR, 'Operador'),
        (ROL_PRODUCTOR, 'Productor'),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_agrotrace',
    )
    rol = models.CharField(max_length=20, choices=ROLES, default=ROL_OPERADOR)
    fundo = models.ForeignKey(
        FundoProductor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='perfiles',
    )

    def __str__(self):
        return f'{self.usuario.username} · {self.rol}'


# --- QUERYSET PERSONALIZADO (Ejercicio 7) ---
class LoteQuerySet(models.QuerySet):
    def pendientes(self):
        """Regla de negocio: Retorna solo lotes pendientes de evaluación"""
        return self.filter(estado_evaluacion='PENDIENTE')

    def aprobados(self):
        """Retorna lotes procesados, considerados conformes."""
        return self.filter(estado_evaluacion='PROCESADO')

    def con_alto_descarte(self, umbral=2.0):
        """Regla de negocio: Retorna lotes cuyo descarte supera el umbral"""
        return self.filter(porcentaje_descarte__gt=umbral)


# --- ENTIDAD PRINCIPAL UNIFICADA ---
class LoteRecepcionado(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('PROCESADO', 'Procesado'),
    ]

    # Manager con QuerySet personalizado
    objects = LoteQuerySet.as_manager()

    # Relación 1:N (ForeignKey)
    fundo = models.ForeignKey(
        FundoProductor, 
        on_delete=models.CASCADE, 
        related_name='lotes'
    )
    codigo_lote = models.CharField(max_length=50, unique=True)
    toneladas_brutas = models.DecimalField(max_digits=8, decimal_places=2)
    porcentaje_descarte = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    estado_evaluacion = models.CharField(max_length=50, default='PENDIENTE')
    fecha_ingreso = models.DateTimeField(auto_now_add=True)

    # S15: trazabilidad y datos derivados calculados siempre en el servidor.
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lotes_registrados',
    )
    cantidad_sacos = models.PositiveIntegerField(default=0)
    precio_unitario_aplicado = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
    )
    total_valorizado = models.DecimalField(
        max_digits=14, decimal_places=2, default=0.00,
    )
    fecha_registro = models.DateTimeField(default=timezone.now, editable=False)

    # Relación N:M mediante tabla intermedia 'through'
    certificaciones = models.ManyToManyField(
        CertificacionAgricola,
        through='CertificacionLote',
        related_name='lotes'
    )

    def __str__(self):
        return f"{self.codigo_lote} - {self.fundo.nombre_fundo}"


# Relación 1:1 (OneToOneField)
class EvaluacionCalidadLote(models.Model):
    lote = models.OneToOneField(
        LoteRecepcionado,
        on_delete=models.CASCADE,
        related_name='evaluacion_calidad'
    )
    nivel_brix = models.DecimalField(max_digits=4, decimal_places=2)
    firmeza_fruto = models.DecimalField(max_digits=4, decimal_places=2)
    observaciones = models.TextField(blank=True, null=True)
    fecha_evaluacion = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Evaluación {self.lote.codigo_lote}"


# Tabla intermedia para la relación N:M
class CertificacionLote(models.Model):
    lote = models.ForeignKey(LoteRecepcionado, on_delete=models.CASCADE)
    certificacion = models.ForeignKey(CertificacionAgricola, on_delete=models.CASCADE)
    fecha_auditoria = models.DateField()
    codigo_inspeccion = models.CharField(max_length=50)
    costo_auditoria = models.DecimalField(max_digits=8, decimal_places=2, default=150.00)

    class Meta:
        unique_together = ('lote', 'certificacion')

    def __str__(self):
        return f"{self.lote.codigo_lote} - {self.certificacion.nombre_certificacion}"