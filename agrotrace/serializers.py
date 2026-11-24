import re

from rest_framework import serializers

from .models import (
    CertificacionAgricola,
    CertificacionLote,
    EvaluacionCalidadLote,
    FundoProductor,
    LoteRecepcionado,
)


class LoteSimpleSerializer(serializers.ModelSerializer):
    """S15: reglas de validación y valorización calculada en el servidor."""

    REGLA_CODIGO = re.compile(r'^LOT-[A-Z0-9]{2,12}(-[A-Z0-9]{1,8})?$')

    fundo = serializers.PrimaryKeyRelatedField(
        queryset=FundoProductor.objects.all(),
    )
    estado_evaluacion = serializers.ChoiceField(
        choices=LoteRecepcionado.ESTADOS,
        default='PENDIENTE',
    )
    registrado_por = serializers.PrimaryKeyRelatedField(read_only=True)
    precio_unitario_aplicado = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
    )
    total_valorizado = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True,
    )
    fecha_registro = serializers.DateTimeField(read_only=True)

    class Meta:
        model = LoteRecepcionado
        fields = (
            'id',
            'codigo_lote',
            'toneladas_brutas',
            'porcentaje_descarte',
            'cantidad_sacos',
            'estado_evaluacion',
            'fundo',
            'registrado_por',
            'precio_unitario_aplicado',
            'total_valorizado',
            'fecha_registro',
        )
        read_only_fields = (
            'id',
            'registrado_por',
            'precio_unitario_aplicado',
            'total_valorizado',
            'fecha_registro',
        )

    def _fundo(self):
        if self.instance and 'fundo' not in self.initial_data:
            return self.instance.fundo
        return self.initial_data.get('fundo')

    def validate_codigo_lote(self, value):
        if not self.REGLA_CODIGO.match(value):
            raise serializers.ValidationError(
                'Formato inválido. Use LOT-ABC-001 (mayúsculas, guiones y dígitos).'
            )
        existe = LoteRecepcionado.objects.filter(codigo_lote__iexact=value)
        if self.instance:
            existe = existe.exclude(pk=self.instance.pk)
        if existe.exists():
            raise serializers.ValidationError('Ese código de lote ya está registrado.')
        return value.upper()

    def validate_toneladas_brutas(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Las toneladas brutas deben ser mayores a 0.'
            )
        fundo = self._fundo()
        if fundo is not None:
            fundo_obj = fundo if hasattr(fundo, 'stock_disponible_tn') else (
                FundoProductor.objects.filter(pk=fundo).first() if str(fundo).isdigit() else None
            )
            if fundo_obj and value > fundo_obj.stock_disponible_tn:
                raise serializers.ValidationError(
                    f'Supera el stock disponible del fundo ({fundo_obj.stock_disponible_tn} TN).'
                )
        return value

    def validate_cantidad_sacos(self, value):
        if not 1 <= value <= 500:
            raise serializers.ValidationError('La cantidad de sacos debe estar entre 1 y 500.')
        return value

    def validate_estado_evaluacion(self, value):
        permitidos = [estado for estado, _ in LoteRecepcionado.ESTADOS]
        if value not in permitidos:
            raise serializers.ValidationError(f'Estado no permitido: {value}.')
        return value

    def validate_porcentaje_descarte(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('El descarte debe estar entre 0 y 100 %.')
        return value

    def _calcular_valorizacion(self, datos):
        fundo = datos.get('fundo') or getattr(self.instance, 'fundo', None)
        toneladas = datos.get(
            'toneladas_brutas',
            getattr(self.instance, 'toneladas_brutas', 0),
        )
        precio = fundo.precio_referencia_tn if hasattr(fundo, 'precio_referencia_tn') else 0
        datos['precio_unitario_aplicado'] = precio
        datos['total_valorizado'] = toneladas * precio
        return datos

    def create(self, validated_data):
        # Cualquier total enviado por el cliente fue descartado por read_only.
        return super().create(self._calcular_valorizacion(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._calcular_valorizacion(validated_data))


class FundoProductorSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundoProductor
        fields = (
            'id',
            'nombre_fundo',
            'propietario_dni_ruc',
            'hectareas',
            'valido_exportacion',
            'cupo_diario_lotes',
            'stock_disponible_tn',
            'precio_referencia_tn',
        )

    def validate_hectareas(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Las hectáreas deben ser mayores a 0.'
            )
        return value

    def validate_stock_disponible_tn(self, value):
        if value < 0:
            raise serializers.ValidationError('El stock disponible no puede ser negativo.')
        return value

    def validate_precio_referencia_tn(self, value):
        if value <= 0:
            raise serializers.ValidationError('El precio de referencia debe ser mayor que cero.')
        return value


class EvaluacionCalidadSerializer(serializers.ModelSerializer):
    lote = serializers.PrimaryKeyRelatedField(
        queryset=LoteRecepcionado.objects.all(),
    )

    class Meta:
        model = EvaluacionCalidadLote
        fields = (
            'id',
            'lote',
            'nivel_brix',
            'firmeza_fruto',
            'observaciones',
            'fecha_evaluacion',
        )


class LoteDeEvaluacionSerializer(serializers.ModelSerializer):
    fundo = FundoProductorSerializer(read_only=True)

    class Meta:
        model = LoteRecepcionado
        fields = ('id', 'codigo_lote', 'fundo')


class EvaluacionCalidadDetalladaSerializer(serializers.ModelSerializer):
    lote = LoteDeEvaluacionSerializer(read_only=True)

    class Meta:
        model = EvaluacionCalidadLote
        fields = (
            'id',
            'lote',
            'nivel_brix',
            'firmeza_fruto',
            'observaciones',
            'fecha_evaluacion',
        )


class CertificacionAgricolaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificacionAgricola
        fields = ('id', 'nombre_certificacion', 'entidad_emisora')


FundoSerializer = FundoProductorSerializer
EvaluacionSerializer = EvaluacionCalidadSerializer
CertificacionSerializer = CertificacionAgricolaSerializer


class CertificacionLoteSerializer(serializers.ModelSerializer):
    certificacion = CertificacionSerializer(read_only=True)

    class Meta:
        model = CertificacionLote
        fields = (
            'certificacion',
            'fecha_auditoria',
            'codigo_inspeccion',
            'costo_auditoria',
        )


class LoteDetalladoSerializer(serializers.ModelSerializer):
    fundo = FundoProductorSerializer(read_only=True)
    evaluacioncalidadlote = EvaluacionCalidadSerializer(
        source='evaluacion_calidad',
        read_only=True,
    )
    certificaciones_lote = CertificacionLoteSerializer(
        source='certificacionlote_set',
        many=True,
        read_only=True,
    )

    class Meta:
        model = LoteRecepcionado
        fields = (
            'id',
            'codigo_lote',
            'toneladas_brutas',
            'porcentaje_descarte',
            'estado_evaluacion',
            'fecha_ingreso',
            'fundo',
            'evaluacioncalidadlote',
            'certificaciones_lote',
        )
