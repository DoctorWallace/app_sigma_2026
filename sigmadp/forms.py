from django import forms
from django.contrib.auth import get_user_model
from .models import DpSample, DpSolicitud, DpMuestraNombre, DpSolicitudTermica, DpResultadoTermico, DpAnalisisDatos


class DpSolicitudUnificadaForm(forms.Form):
    """Formulario unificado para solicitudes S-DP basado en la experiencia de TDS."""

    TIPO_SOLICITUD_CHOICES = (
        ("termica", "Desorción térmica (TDS)"),
        ("permeacion", "Permeación de gases (próximamente)"),
    )

    tipo_solicitud = forms.ChoiceField(
        choices=TIPO_SOLICITUD_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label="Tipo de solicitud",
        initial="termica",
    )

    numero_muestras = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-input", "min": 1, "max": 10}),
        label="Número de muestras",
        help_text="Máximo 10 muestras por solicitud",
    )

    condiciones_globales = forms.BooleanField(
        required=False,
        initial=True,
        label="Aplicar las mismas condiciones de ensayo a todas las muestras",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    material = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Se utilizará si alguna muestra no indica material",
            }
        ),
        label="Material (valor por defecto)",
    )

    procedencia = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Opcional, se asociará a las muestras sin valor propio",
            }
        ),
        label="Procedencia (valor por defecto)",
    )

    temperatura_maxima = forms.FloatField(
        required=False,
        max_value=900,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "step": "any", "placeholder": "Máximo 900°C"}
        ),
        label="Temperatura máxima [°C]",
        help_text="Máximo 900°C",
    )

    tasa_calentamiento = forms.FloatField(
        required=False,
        max_value=15,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "step": "any", "placeholder": "Máximo 15°C/min"}
        ),
        label="Tasa de calentamiento [°C/min]",
        help_text="Máximo 15°C/min",
    )

    tasa_enfriamiento = forms.FloatField(
        required=False,
        max_value=15,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "step": "any", "placeholder": "Máximo 15°C/min"}
        ),
        label="Tasa de enfriamiento [°C/min]",
        help_text="Máximo 15°C/min",
    )

    tiempo_permanencia = forms.FloatField(
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "step": "any", "placeholder": "Minutos"}
        ),
        label="Tiempo de permanencia [min]",
    )

    masa_registrar = forms.ChoiceField(
        choices=(
            ("", "Seleccionar masa..."),
            ("2", "Masa 2 uma"),
            ("3", "Masa 3 uma"),
            ("4", "Masa 4 uma"),
        ),
        required=False,
        widget=forms.Select(attrs={"class": "form-input"}),
        label="Masa a registrar [uma]",
    )

    espesor_muestra = forms.FloatField(
        required=False,
        min_value=0.1,
        max_value=10,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "step": "any", "placeholder": "0.1 - 10 mm"}
        ),
        label="Espesor de la muestra [mm]",
        help_text="Entre 0.1 y 10 mm",
    )

    tamaño_muestra = forms.FloatField(
        required=False,
        min_value=0.5,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "step": "any", "placeholder": "Mínimo 0.5 cm²"}
        ),
        label="Tamaño de la muestra [cm²]",
        help_text="Mínimo 0.5 cm²",
    )

    geometria_muestra = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": "Circular, cuadrada, etc."}
        ),
        label="Geometría de la muestra",
    )

    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-input",
                "rows": 4,
                "placeholder": "Observaciones que se aplicarán a todas las solicitudes",
            }
        ),
        label="Observaciones generales",
    )

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo_solicitud")
        if tipo and tipo != "termica":
            self.add_error(
                "tipo_solicitud",
                "Por ahora solo está disponible la solicitud de desorción térmica (TDS).",
            )

        numero = cleaned_data.get("numero_muestras")
        if not numero:
            self.add_error("numero_muestras", "Indica cuántas muestras quieres incluir.")

        if cleaned_data.get("condiciones_globales"):
            required_fields = [
                ("temperatura_maxima", "la temperatura máxima"),
                ("tasa_calentamiento", "la tasa de calentamiento"),
                ("tasa_enfriamiento", "la tasa de enfriamiento"),
                ("tiempo_permanencia", "el tiempo de permanencia"),
                ("masa_registrar", "la masa a registrar"),
                ("espesor_muestra", "el espesor de la muestra"),
                ("tamaño_muestra", "el tamaño de la muestra"),
                ("geometria_muestra", "la geometría de la muestra"),
            ]
            for field, label in required_fields:
                value = cleaned_data.get(field)
                if field == "masa_registrar":
                    if not value:
                        self.add_error(field, f"Selecciona {label}.")
                else:
                    if value in (None, ""):
                        self.add_error(field, f"Indica {label}.")
        return cleaned_data

class DpMuestraForm(forms.Form):
    """Formulario para cada muestra individual"""
    
    nombre_muestra = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de la muestra'
        }),
        label="Nombre de la Muestra"
    )

    material = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Material de la muestra'
        }),
        label="Material"
    )

    procedencia = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Procedencia de la muestra'
        }),
        label="Procedencia"
    )

    # Campos específicos para TDS
    temperatura_maxima = forms.FloatField(
        required=False,
        max_value=900,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 'any',
            'placeholder': 'Máximo 900°C'
        }),
        label="Temperatura Máxima [°C]",
        help_text="Máximo 900°C"
    )

    tasa_calentamiento = forms.FloatField(
        required=False,
        max_value=15,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 'any',
            'placeholder': 'Máximo 15°C/min'
        }),
        label="Tasa de Calentamiento [°C/min]",
        help_text="Máximo 15°C/min"
    )

    tasa_enfriamiento = forms.FloatField(
        required=False,
        max_value=15,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 'any',
            'placeholder': 'Máximo 15°C/min'
        }),
        label="Tasa de Enfriamiento [°C/min]",
        help_text="Máximo 15°C/min"
    )

    tiempo_permanencia = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 'any',
            'placeholder': 'Minutos'
        }),
        label="Tiempo de Permanencia [min]"
    )

    masa_registrar = forms.ChoiceField(
        choices=[
            ('', 'Seleccionar masa...'),
            ('2', 'Masa 2 uma'),
            ('3', 'Masa 3 uma'),
            ('4', 'Masa 4 uma'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Masa a Registrar [uma]"
    )

    # Especificaciones de la muestra
    espesor_muestra = forms.FloatField(
        required=False,
        min_value=0.1,
        max_value=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 'any',
            'placeholder': '0.1 - 10 mm'
        }),
        label="Espesor de la Muestra [mm]",
        help_text="Entre 0.1 y 10 mm"
    )

    tamaño_muestra = forms.FloatField(
        required=False,
        min_value=0.5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 'any',
            'placeholder': 'Mínimo 0.5 cm²'
        }),
        label="Tamaño de la Muestra [cm²]",
        help_text="Mínimo 0.5 cm²"
    )

    geometria_muestra = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Circular, cuadrada, etc.'
        }),
        label="Geometría de la Muestra"
    )

    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones específicas para esta muestra'
        }),
        label="Observaciones"
    )

    # Checkbox para condiciones iguales
    condiciones_iguales_anterior = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input condiciones-iguales',
            'onchange': 'copiarCondicionesAnteriores(this)'
        }),
        label="Condiciones iguales a la muestra anterior"
    )

    def clean(self):
        cleaned_data = super().clean()
        
        # Validaciones específicas para TDS
        if cleaned_data.get('temperatura_maxima') and not cleaned_data.get('masa_registrar'):
            raise forms.ValidationError("La masa a registrar es obligatoria cuando se especifica temperatura máxima")
        
        if cleaned_data.get('masa_registrar') and not cleaned_data.get('temperatura_maxima'):
            raise forms.ValidationError("La temperatura máxima es obligatoria cuando se especifica masa a registrar")

        return cleaned_data


class DpSampleForm(forms.ModelForm):
    class Meta:
        model = DpSample
        fields = ["nombre", "tipo", "tratamientos"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input", "placeholder": "Nombre de la muestra"}),
            "tipo": forms.TextInput(attrs={"class": "form-input", "placeholder": "Tipo"}),
            "tratamientos": forms.Textarea(attrs={"class": "form-input", "rows": 4, "placeholder": "Tratamientos previos"}),
        }


class DpSolicitudForm(forms.ModelForm):
    class Meta:
        model = DpSolicitud
        fields = [
            # generales
            "material", "procedencia", "numero_muestras", "tratamientos",
            # desorción
            "ensayo_desorcion", "desorcion_temperatura", "desorcion_tiempo", "desorcion_presion", 
            "desorcion_gas", "desorcion_volumen_muestra",
            # permeación
            "ensayo_permeacion", "permeacion_temperatura", "permeacion_presion_alta", "permeacion_presion_baja",
            "permeacion_gas", "permeacion_espesor_membrana", "permeacion_area_membrana",
            # difusión
            "ensayo_difusion", "difusion_temperatura", "difusion_tiempo", "difusion_concentracion_inicial",
            "difusion_concentracion_final", "difusion_volumen_solucion",
            # adsorción
            "ensayo_adsorcion", "adsorcion_temperatura", "adsorcion_presion", "adsorcion_gas",
            "adsorcion_masa_muestra", "adsorcion_area_superficie",
            # notas
            "observaciones",
        ]
        widgets = {
            "material": forms.TextInput(attrs={"class": "form-input", "placeholder": "Material"}),
            "procedencia": forms.TextInput(attrs={"class": "form-input", "placeholder": "Procedencia"}),
            "numero_muestras": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
            "tratamientos": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Tratamientos"}),

            # Desorción
            "ensayo_desorcion": forms.CheckboxInput(),
            "desorcion_temperatura": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "°C"}),
            "desorcion_tiempo": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "horas"}),
            "desorcion_presion": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "bar"}),
            "desorcion_gas": forms.TextInput(attrs={"class": "form-input", "placeholder": "H2, D2, etc."}),
            "desorcion_volumen_muestra": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "cm³"}),

            # Permeación
            "ensayo_permeacion": forms.CheckboxInput(),
            "permeacion_temperatura": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "°C"}),
            "permeacion_presion_alta": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "bar"}),
            "permeacion_presion_baja": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "bar"}),
            "permeacion_gas": forms.TextInput(attrs={"class": "form-input", "placeholder": "H2, D2, etc."}),
            "permeacion_espesor_membrana": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "mm"}),
            "permeacion_area_membrana": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "cm²"}),

            # Difusión
            "ensayo_difusion": forms.CheckboxInput(),
            "difusion_temperatura": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "°C"}),
            "difusion_tiempo": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "horas"}),
            "difusion_concentracion_inicial": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "ppm"}),
            "difusion_concentracion_final": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "ppm"}),
            "difusion_volumen_solucion": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "ml"}),

            # Adsorción
            "ensayo_adsorcion": forms.CheckboxInput(),
            "adsorcion_temperatura": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "°C"}),
            "adsorcion_presion": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "bar"}),
            "adsorcion_gas": forms.TextInput(attrs={"class": "form-input", "placeholder": "Gas utilizado"}),
            "adsorcion_masa_muestra": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "mg"}),
            "adsorcion_area_superficie": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "m²/g"}),

            "observaciones": forms.Textarea(attrs={"class": "form-input", "rows": 4, "placeholder": "Anotaciones"}),
        }


class DpMuestraNombreForm(forms.ModelForm):
    class Meta:
        model = DpMuestraNombre
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input", "placeholder": "Nombre de la muestra"}),
        }


# Formset para múltiples nombres de muestras
DpMuestraNombreFormSet = forms.inlineformset_factory(
    DpSolicitud,
    DpMuestraNombre,
    form=DpMuestraNombreForm,
    extra=1,
    can_delete=True,
    can_delete_extra=True,
)


class DpSolicitudTermicaForm(forms.ModelForm):
    """Formulario para solicitudes de análisis térmico DP"""
    
    class Meta:
        model = DpSolicitudTermica
        fields = [
            'nombre_muestra',
            'material',
            'temperatura_maxima',
            'tasa_calentamiento',
            'tasa_enfriamiento',
            'tiempo_permanencia',
            'masa_registrar',
            'espesor_muestra',
            'tamaño_muestra',
            'geometria_muestra',
            'observaciones'
        ]
        widgets = {
            'nombre_muestra': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la muestra'
            }),
            'material': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Material de la muestra'
            }),
            'temperatura_maxima': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'max': '900',
                'placeholder': 'Temperatura máxima [ºC]'
            }),
            'tasa_calentamiento': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'max': '15',
                'placeholder': 'Tasa de calentamiento [ºC/min]'
            }),
            'tasa_enfriamiento': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'max': '15',
                'placeholder': 'Tasa de enfriamiento [ºC/min]'
            }),
            'tiempo_permanencia': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': 'Tiempo de permanencia [min]'
            }),
            'masa_registrar': forms.Select(attrs={
                'class': 'form-control'
            }),
            'espesor_muestra': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0.1',
                'max': '10',
                'placeholder': 'Espesor [mm]'
            }),
            'tamaño_muestra': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0.5',
                'placeholder': 'Tamaño [cm²]'
            }),
            'geometria_muestra': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Geometría (circular, cuadrada, etc.)'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales'
            })
        }

    def clean_temperatura_maxima(self):
        temperatura = self.cleaned_data.get('temperatura_maxima')
        if temperatura and temperatura > 900:
            raise forms.ValidationError("La temperatura máxima no puede superar 900ºC")
        return temperatura

    def clean_tasa_calentamiento(self):
        tasa = self.cleaned_data.get('tasa_calentamiento')
        if tasa and tasa > 15:
            raise forms.ValidationError("La tasa de calentamiento no puede superar 15ºC/min")
        return tasa

    def clean_tasa_enfriamiento(self):
        tasa = self.cleaned_data.get('tasa_enfriamiento')
        if tasa and tasa > 15:
            raise forms.ValidationError("La tasa de enfriamiento no puede superar 15ºC/min")
        return tasa

    def clean_espesor_muestra(self):
        espesor = self.cleaned_data.get('espesor_muestra')
        if espesor and (espesor < 0.1 or espesor > 10):
            raise forms.ValidationError("El espesor debe estar entre 0.1 y 10 mm")
        return espesor

    def clean_tamaño_muestra(self):
        tamaño = self.cleaned_data.get('tamaño_muestra')
        if tamaño and tamaño < 0.5:
            raise forms.ValidationError("El tamaño mínimo es 0.5 cm²")
        return tamaño


class DpResultadoTermicoForm(forms.ModelForm):
    """Formulario para subir resultados de análisis térmico"""
    
    class Meta:
        model = DpResultadoTermico
        fields = [
            'archivo_resultado',
            'archivo_resultado_2',
            'fecha_ensayo',
            'observaciones_tecnico'
        ]
        widgets = {
            'archivo_resultado': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.txt,.csv'
            }),
            'archivo_resultado_2': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.txt,.csv'
            }),
            'fecha_ensayo': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'observaciones_tecnico': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones del técnico'
            })
        }

    def clean_archivo_resultado(self):
        archivo = self.cleaned_data.get('archivo_resultado')
        if archivo:
            # Verificar extensión
            if not archivo.name.lower().endswith(('.txt', '.csv')):
                raise forms.ValidationError("Solo se permiten archivos .txt o .csv")
            # Verificar tamaño (máximo 10MB)
            if archivo.size > 10 * 1024 * 1024:
                raise forms.ValidationError("El archivo no puede superar 10MB")
        return archivo

    def clean_archivo_resultado_2(self):
        archivo = self.cleaned_data.get('archivo_resultado_2')
        if archivo:
            # Verificar extensión
            if not archivo.name.lower().endswith(('.txt', '.csv')):
                raise forms.ValidationError("Solo se permiten archivos .txt o .csv")
            # Verificar tamaño (máximo 10MB)
            if archivo.size > 10 * 1024 * 1024:
                raise forms.ValidationError("El archivo no puede superar 10MB")
        return archivo


class DpAnalisisDatosForm(forms.ModelForm):
    """Formulario para analisis de datos termicos"""

    solicitante = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        label="Usuario solicitante",
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        User = get_user_model()
        solicitantes_qs = (
            User.objects.filter(dp_solicitudes_termicas__isnull=False)
            .distinct()
            .order_by("first_name", "last_name", "username")
        )
        self.fields["solicitante"].queryset = solicitantes_qs
        self.fields["solicitante"].widget.attrs.setdefault("class", "form-select")
        self.fields["solicitante"].empty_label = "Selecciona un usuario"

        def _user_label(user):
            full_name = (user.get_full_name() or "").strip()
            if full_name and full_name.lower() != user.username.lower():
                return f"{full_name} ({user.username})"
            return full_name or user.username

        self.fields["solicitante"].label_from_instance = _user_label

        solicitud_field = self.fields["solicitud_termica"]
        solicitud_field.required = True
        solicitud_field.empty_label = "Selecciona una solicitud"
        solicitud_field.widget.attrs.update({"class": "form-select"})
        solicitud_field.queryset = DpSolicitudTermica.objects.none()
        solicitud_field.label = "Solicitud asociada"
        solicitud_field.help_text = "Selecciona la solicitud a la que pertenece este analisis."
        solicitud_field.label_from_instance = (
            lambda obj: f"DP-T#{obj.pk} - {obj.nombre_muestra} ({obj.get_estado_display()})"
        )

        def _resolve_user_id(value):
            if value in (None, ""):
                return None
            if hasattr(value, "pk"):
                return value.pk
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        if self.is_bound:
            selected_user_id = _resolve_user_id(self.data.get("solicitante"))
        else:
            initial_data = getattr(self, "initial", {})
            selected_user_id = _resolve_user_id(initial_data.get("solicitante"))
            if selected_user_id is None and self.instance.pk and self.instance.solicitud_termica_id:
                selected_user_id = self.instance.solicitud_termica.solicitante_id
                self.fields["solicitante"].initial = selected_user_id

        if selected_user_id:
            solicitud_field.queryset = (
                DpSolicitudTermica.objects.filter(solicitante_id=selected_user_id)
                .order_by("-creado_en")
            )
        if self.instance.pk and self.instance.solicitud_termica_id:
            solicitud_field.initial = self.instance.solicitud_termica

        self.fields["separador"].required = False
        self.fields["decimal"].required = False
        self.fields["codificacion"].required = False

        self.fields["separador"].widget.attrs.update(
            {
                "placeholder": "Deja vacio para deteccion automatica",
                "value": "",
            }
        )
        self.fields["decimal"].widget.attrs.update(
            {
                "placeholder": "Deja vacio para deteccion automatica",
                "value": "",
            }
        )
        self.fields["codificacion"].widget.attrs.update(
            {
                "placeholder": "cp1252, latin1, utf-8, etc.",
                "value": "cp1252",
            }
        )

    def clean(self):
        cleaned_data = super().clean()

        solicitante = cleaned_data.get("solicitante")
        solicitud = cleaned_data.get("solicitud_termica")
        if solicitud and solicitante and solicitud.solicitante_id != solicitante.id:
            self.add_error(
                "solicitud_termica",
                "La solicitud seleccionada no pertenece al usuario indicado.",
            )
        if solicitud is None and "solicitud_termica" not in self.errors:
            self.add_error("solicitud_termica", "Selecciona la solicitud asociada.")

        archivo = cleaned_data.get('archivo_datos')
        if archivo:
            if archivo.size == 0:
                raise forms.ValidationError("El archivo esta vacio.")
            if archivo.size > 50 * 1024 * 1024:
                raise forms.ValidationError("El archivo es demasiado grande. Maximo 50MB.")
            if not archivo.name or '.' not in archivo.name:
                archivo.name = archivo.name + '.txt' if archivo.name else 'datos.txt'

        separador = cleaned_data.get('separador', '').strip().lower()
        if separador in ['auto', '']:
            cleaned_data['separador'] = ''

        decimal = cleaned_data.get('decimal', '').strip().lower()
        if decimal in ['auto', '']:
            cleaned_data['decimal'] = ''

        codificacion = cleaned_data.get('codificacion', '').strip().lower()
        if codificacion in ['auto', '']:
            cleaned_data['codificacion'] = ''

        archivo = cleaned_data.get('archivo_datos')
        if archivo:
            from pathlib import Path as _Path
            suffix = _Path(archivo.name).suffix.lower().lstrip('.')
            if suffix in {'txt', 'csv', 'tsv', 'dat'}:
                cleaned_data['tipo_archivo'] = suffix
        return cleaned_data

    class Meta:
        model = DpAnalisisDatos
        fields = [
            'solicitud_termica',
            'nombre',
            'descripcion',
            'archivo_datos',
            'separador',
            'decimal',
            'codificacion',
            'mostrar_temperatura',
            'mostrar_leak',
            'mostrar_heater',
            'mostrar_overview'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del analisis'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripcion del analisis'
            }),
            'solicitud_termica': forms.Select(attrs={'class': 'form-select'}),
            'archivo_datos': forms.FileInput(attrs={'class': 'form-control', 'id': 'archivo-datos'}),
            'separador': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ejemplo: 	, ;, , (deja en blanco para autodetectar)'
            }),
            'decimal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ejemplo: , o . (deja en blanco para autodetectar)',
            }),
            'codificacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'cp1252, latin1, utf-8, etc.',
                'value': 'cp1252'
            }),
            'mostrar_temperatura': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'mostrar_leak': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'mostrar_heater': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'mostrar_overview': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    def clean_archivo_datos(self):
        archivo = self.cleaned_data.get('archivo_datos')
        if not archivo:
            return archivo

        nombre = archivo.name
        lower_name = nombre.lower()
        allowed = ('.txt', '.csv', '.tsv', '.dat')
        if '.' in lower_name:
            if not lower_name.endswith(allowed):
                raise forms.ValidationError("Solo se permiten archivos .txt, .csv, .tsv o .dat")
        else:
            tipo = self.data.get('tipo_archivo') or DpAnalisisDatos.TipoArchivo.TXT
            tipo = str(tipo).lower().strip()
            if tipo not in {'txt', 'csv', 'tsv', 'dat'}:
                tipo = DpAnalisisDatos.TipoArchivo.TXT
            archivo.name = f"{nombre}.{tipo}"

        if archivo.size > 50 * 1024 * 1024:
            raise forms.ValidationError("El archivo no puede superar 50MB")

        return archivo

    def clean(self):
        cleaned = super().clean()
        archivo = cleaned.get('archivo_datos')
        if archivo:
            from pathlib import Path as _Path
            suffix = _Path(archivo.name).suffix.lower().lstrip('.')
            if suffix in {'txt', 'csv', 'tsv', 'dat'}:
                cleaned['tipo_archivo'] = suffix
        return cleaned


    def clean_separador(self):
        separador = self.cleaned_data.get('separador')
        if separador is None:
            return 'auto'
        value = str(separador).strip()
        if not value:
            return 'auto'
        lower = value.lower()
        if lower in {'auto', 'automático', 'automatico'}:
            return 'auto'
        if lower in {'\t', 'tab', 'tabulador'}:
            return '\t'
        if len(value) == 1:
            return value
        return value

    def clean_decimal(self):
        decimal = self.cleaned_data.get('decimal')
        if decimal is None:
            return 'auto'
        value = str(decimal).strip()
        if not value:
            return 'auto'
        lower = value.lower()
        if lower in {'auto', 'automático', 'automatico'}:
            return 'auto'
        if lower in {',', 'coma'}:
            return ','
        if lower in {'.', 'punto'}:
            return '.'
        return value[0]








