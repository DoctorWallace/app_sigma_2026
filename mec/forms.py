from django import forms
from django.contrib.auth.models import User
from .models import MecSample, MecSolicitud, MecMuestraNombre
from sigmalab.models import UsuarioAsociado


class MecSampleForm(forms.ModelForm):
    class Meta:
        model = MecSample
        fields = ["nombre", "tipo", "tratamientos"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input", "placeholder": "Nombre de la muestra"}),
            "tipo": forms.TextInput(attrs={"class": "form-input", "placeholder": "Tipo"}),
            "tratamientos": forms.Textarea(attrs={"class": "form-input", "rows": 4, "placeholder": "Tratamientos previos"}),
        }


class MecSolicitudForm(forms.ModelForm):
    class Meta:
        model = MecSolicitud
        fields = [
            # generales
            "material", "procedencia", "numero_muestras", "tratamientos",
            # dureza
            "ensayo_dureza", "dureza_carga", "dureza_huellas_filas", "dureza_huellas_columnas",
            # traccion
            "ensayo_traccion", "traccion_temperatura", "traccion_velocidad_deformacion", "traccion_diametro", "traccion_longitud_marca",
            # fatiga
            "ensayo_fatiga", "fatiga_temperatura", "fatiga_porcentaje_deformacion", "fatiga_frecuencia", "fatiga_eps_max", "fatiga_eps_min",
            # creep-fatiga
            "ensayo_creep_fatiga", "creep_temperatura", "creep_porcentaje_deformacion", "creep_frecuencia", "creep_eps_max", "creep_eps_min",
            "creep_mantenimiento_tipo", "creep_mantenimiento_en", "creep_tiempo_mantenimiento_s",
            # notas
            "observaciones",
        ]
        widgets = {
            "material": forms.TextInput(attrs={"class": "form-input", "placeholder": "Material"}),
            "procedencia": forms.TextInput(attrs={"class": "form-input", "placeholder": "Procedencia"}),
            "numero_muestras": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
            "tratamientos": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Tratamientos"}),

            "ensayo_dureza": forms.CheckboxInput(),
            "dureza_carga": forms.TextInput(attrs={"class": "form-input", "placeholder": "Carga"}),
            "dureza_huellas_filas": forms.Select(choices=[(i, i) for i in range(1, 21)], attrs={"class": "form-input"}),
            "dureza_huellas_columnas": forms.Select(choices=[(i, i) for i in range(1, 21)], attrs={"class": "form-input"}),

            "ensayo_traccion": forms.CheckboxInput(),
            "traccion_temperatura": forms.Textarea(attrs={"class": "form-input", "rows": 2, "placeholder": "Lista de temperaturas"}),
            "traccion_velocidad_deformacion": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "traccion_diametro": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "traccion_longitud_marca": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),

            "ensayo_fatiga": forms.CheckboxInput(),
            "fatiga_temperatura": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "fatiga_porcentaje_deformacion": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "fatiga_frecuencia": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "fatiga_eps_max": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "fatiga_eps_min": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),

            "ensayo_creep_fatiga": forms.CheckboxInput(),
            "creep_temperatura": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "creep_porcentaje_deformacion": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "creep_frecuencia": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "creep_eps_max": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "creep_eps_min": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "creep_mantenimiento_tipo": forms.TextInput(attrs={"class": "form-input", "placeholder": "carga/deformacion"}),
            "creep_mantenimiento_en": forms.TextInput(attrs={"class": "form-input", "placeholder": "maxima/minima"}),
            "creep_tiempo_mantenimiento_s": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),

            "observaciones": forms.Textarea(attrs={"class": "form-input", "rows": 4, "placeholder": "Anotaciones"}),
        }


class MecMuestraNombreForm(forms.ModelForm):
    class Meta:
        model = MecMuestraNombre
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input", "placeholder": "Nombre de la muestra"}),
        }


# Formset para múltiples nombres de muestras
MecMuestraNombreFormSet = forms.inlineformset_factory(
    MecSolicitud,
    MecMuestraNombre,
    form=MecMuestraNombreForm,
    extra=1,
    can_delete=True,
    can_delete_extra=True,
)


class MecSolicitudDurezaForm(forms.Form):
    """Formulario para solicitudes de ensayos de dureza"""
    
    # Selección de tipo de ensayo
    ensayo_dureza = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Ensayo de Dureza",
        help_text="Medición de dureza Vickers"
    )
    
    ensayo_maquina = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'disabled': True}),
        label="Máquina de Ensayos",
        help_text="Disponible próximamente"
    )
    
    # Datos de la/s muestra/s
    material = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Material de la muestra'
        }),
        label="Material"
    )
    
    numero_muestras = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 20
        }),
        label="Número de Muestras",
        help_text="Máximo 20 muestras por solicitud"
    )
    
    referencia_muestras = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Referencia de las muestras'
        }),
        label="Referencia de Muestras"
    )
    
    tamano_muestra = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Dimensiones de la muestra'
        }),
        label="Tamaño de la Muestra",
        help_text="Dimensiones en mm"
    )
    
    # Parámetros del ensayo de dureza
    carga_ensayo = forms.FloatField(
        min_value=0.01,
        max_value=20,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 'any',
            'placeholder': '0.01 - 20 HV'
        }),
        label="Carga del Ensayo [HV]",
        help_text="Rango: 0.01-20 HV"
    )
    
    numero_indentaciones = forms.IntegerField(
        min_value=1,
        max_value=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 50
        }),
        label="Número de Indentaciones",
        help_text="Número impar de medidas, matriz, puntos en línea, etc."
    )
    
    otros_datos = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Otros datos de interés o información relevante de la/s muestra/s'
        }),
        label="Otros Datos de Interés"
    )
    
    dureza_esperada = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Dureza esperada aproximada'
        }),
        label="Dureza Esperada"
    )
    
    incluir_fotos = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Incluir en el informe de resultados fotos de las indentaciones",
        help_text="Se incluirán fotografías de las indentaciones en el informe final"
    )
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Observaciones adicionales'
        }),
        label="Observaciones"
    )
    
    # Campos para muestras individuales (se generarán dinámicamente)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Los campos de muestras se añadirán dinámicamente en el template
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que al menos un tipo de ensayo esté seleccionado
        if not cleaned_data.get('ensayo_dureza') and not cleaned_data.get('ensayo_maquina'):
            raise forms.ValidationError("Debe seleccionar al menos un tipo de ensayo")
        
        # Validar que si se selecciona dureza, se completen los campos obligatorios
        if cleaned_data.get('ensayo_dureza'):
            if not cleaned_data.get('carga_ensayo'):
                raise forms.ValidationError("La carga del ensayo es obligatoria para ensayos de dureza")
            if not cleaned_data.get('numero_indentaciones'):
                raise forms.ValidationError("El número de indentaciones es obligatorio para ensayos de dureza")
        
        return cleaned_data


class MecUsuarioAsociadoForm(forms.ModelForm):
    """Formulario para crear/editar usuarios externos en S-MEC"""
    
    class Meta:
        model = UsuarioAsociado
        fields = [
            'investigador_principal', 'nombre', 'apellidos', 'email', 'telefono',
            'tipo_becario', 'institucion_origen',
            'fecha_inicio', 'fecha_fin',
            'puede_solicitar_autonomo', 'observaciones'
        ]
        widgets = {
            'investigador_principal': forms.Select(attrs={
                'class': 'form-input'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nombre del usuario externo'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Apellidos del usuario externo'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'email@ejemplo.com'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Teléfono (opcional)'
            }),
            'tipo_becario': forms.Select(attrs={
                'class': 'form-input'
            }),
            'institucion_origen': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Universidad, centro de investigación, etc.'
            }),
            'fecha_inicio': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'fecha_fin': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'puede_solicitar_autonomo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Observaciones adicionales sobre el usuario externo...'
            }),
        }
        labels = {
            'investigador_principal': 'Usuario DTF responsable',
            'nombre': 'Nombre',
            'apellidos': 'Apellidos',
            'email': 'Email',
            'telefono': 'Teléfono',
            'tipo_becario': 'Tipo de usuario',
            'institucion_origen': 'Institución de origen',
            'fecha_inicio': 'Fecha de inicio',
            'fecha_fin': 'Fecha de finalización',
            'puede_solicitar_autonomo': 'Puede realizar solicitudes autónomas',
            'observaciones': 'Observaciones',
        }
    
    def __init__(self, *args, **kwargs):
        self.creado_por = kwargs.pop('creado_por', None)
        self.es_tecnico = kwargs.pop('es_tecnico', False)
        super().__init__(*args, **kwargs)

        # Hacer que el teléfono no sea obligatorio
        self.fields['telefono'].required = False
        self.fields['fecha_fin'].required = False
        self.fields['observaciones'].required = False

        # Configurar el campo de investigador principal
        if self.es_tecnico:
            # Si es técnico, puede seleccionar cualquier usuario DTF
            self.fields['investigador_principal'].queryset = User.objects.filter(
                groups__name='usuarios_dtf'
            ).order_by('first_name', 'last_name')
            self.fields['investigador_principal'].empty_label = "Seleccionar usuario DTF..."
            self.fields['investigador_principal'].required = True
        else:
            # Si no es técnico, solo puede ver sus propios usuarios (no debería llegar aquí)
            self.fields['investigador_principal'].queryset = User.objects.none()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Verificar que no exista otro usuario con el mismo email
            existing = UsuarioAsociado.objects.filter(email=email)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("Ya existe un usuario externo con este email.")
        return email

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.creado_por:
            instance.creado_por = self.creado_por
        
        if commit:
            instance.save()
        
        return instance

