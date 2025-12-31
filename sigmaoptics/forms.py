from django import forms
from django.forms import inlineformset_factory
from .models import OpticsSolicitud, OpticsMuestra, OpticsAnalisisDatos, OpticsResultado


class OpticsSolicitudForm(forms.ModelForm):
    """Formulario para crear solicitudes de análisis óptico"""
    
    class Meta:
        model = OpticsSolicitud
        fields = [
            'material',
            'numero_muestras',
            'referencia_muestras',
            'tipo_tamano',
            'diametro_muestra',
            'lado1_muestra',
            'lado2_muestra',
            'medidas_realizar',
            'formato_resultado',
            'otros_datos'
        ]
        widgets = {
            'material': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del material'
            }),
            'numero_muestras': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'id': 'numero_muestras'
            }),
            'referencia_muestras': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Referencia de las muestras'
            }),
            'tipo_tamano': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
            'diametro_muestra': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0.1',
                'placeholder': 'Diámetro en cm'
            }),
            'lado1_muestra': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0.1',
                'placeholder': 'Lado 1 en cm'
            }),
            'lado2_muestra': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0.1',
                'placeholder': 'Lado 2 en cm'
            }),
            'medidas_realizar': forms.Select(attrs={
                'class': 'form-select'
            }),
            'formato_resultado': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
            'otros_datos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Otros datos de interés o información relevante'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['medidas_realizar'].empty_label = "Seleccione una opción"
        
        # Configurar labels más descriptivos
        self.fields['tipo_tamano'].label = "Tipo de medida de tamaño"
        self.fields['diametro_muestra'].label = "Diámetro (cm)"
        self.fields['lado1_muestra'].label = "Lado 1 (cm)"
        self.fields['lado2_muestra'].label = "Lado 2 (cm)"
        self.fields['formato_resultado'].label = "¿En qué formato desea los resultados?"
        
        # Hacer que los campos de tamaño sean opcionales
        self.fields['diametro_muestra'].required = False
        self.fields['lado1_muestra'].required = False
        self.fields['lado2_muestra'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_tamano = cleaned_data.get('tipo_tamano')
        diametro = cleaned_data.get('diametro_muestra')
        lado1 = cleaned_data.get('lado1_muestra')
        lado2 = cleaned_data.get('lado2_muestra')
        
        # Validar que se proporcione al menos una medida de tamaño
        if tipo_tamano == 'diametro' and not diametro:
            self.add_error('diametro_muestra', 'Debe especificar el diámetro de la muestra.')
        elif tipo_tamano == 'lados' and (not lado1 or not lado2):
            if not lado1:
                self.add_error('lado1_muestra', 'Debe especificar el lado 1 de la muestra.')
            if not lado2:
                self.add_error('lado2_muestra', 'Debe especificar el lado 2 de la muestra.')
        
        return cleaned_data


class OpticsMuestraForm(forms.ModelForm):
    """Formulario para muestras individuales"""
    
    class Meta:
        model = OpticsMuestra
        fields = ['identificacion', 'descripcion']
        widgets = {
            'identificacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Identificación de la muestra'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Descripción de la muestra'
            })
        }


# Formset para manejar múltiples muestras dinámicamente
OpticsMuestraFormSet = inlineformset_factory(
    OpticsSolicitud,
    OpticsMuestra,
    form=OpticsMuestraForm,
    extra=0,
    can_delete=False,
    fields=['identificacion', 'descripcion']
)


class OpticsAnalisisDatosForm(forms.ModelForm):
    """Formulario para análisis de datos ópticos"""
    
    class Meta:
        model = OpticsAnalisisDatos
        fields = [
            'nombre', 'descripcion', 'archivo_datos', 'tipo_archivo',
            'separador', 'decimal', 'codificacion',
            'mostrar_espectro', 'mostrar_transmitancia', 'mostrar_absorbancia', 'mostrar_overview'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del análisis'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del análisis'
            }),
            'archivo_datos': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.txt,.csv,.tsv,.dat'
            }),
            'tipo_archivo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'separador': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '\\t, ;, ,, |'
            }),
            'decimal': forms.Select(attrs={
                'class': 'form-select'
            }),
            'codificacion': forms.Select(attrs={
                'class': 'form-select'
            }),
            'mostrar_espectro': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'mostrar_transmitancia': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'mostrar_absorbancia': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'mostrar_overview': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar detección automática
        self.fields['separador'].initial = 'auto'
        self.fields['separador'].widget.attrs.update({
            'readonly': True,
            'value': 'auto'
        })
        self.fields['separador'].help_text = "Detección automática activada"
        
        # Cambiar el campo decimal a TextInput para que sea de solo lectura
        self.fields['decimal'].widget = forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': True,
            'value': 'auto'
        })
        self.fields['decimal'].initial = 'auto'
        self.fields['decimal'].help_text = "Detección automática activada"
        
        self.fields['codificacion'].choices = [
            ('auto', 'Detección automática'),
            ('cp1252', 'Windows-1252 (cp1252)'),
            ('utf-8', 'UTF-8'),
            ('latin1', 'Latin-1 (latin1)'),
            ('ascii', 'ASCII')
        ]
        self.fields['codificacion'].initial = 'auto'
    
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
            tipo = self.data.get('tipo_archivo') or OpticsAnalisisDatos.TipoArchivo.TXT
            tipo = str(tipo).lower().strip()
            if tipo not in {'txt', 'csv', 'tsv', 'dat'}:
                tipo = OpticsAnalisisDatos.TipoArchivo.TXT
            archivo.name = f"{nombre}.{tipo}"

        if archivo.size > 50 * 1024 * 1024:
            raise forms.ValidationError("El archivo no puede superar 50MB")

        return archivo


class OpticsResultadoForm(forms.ModelForm):
    """Formulario para subir resultados de análisis óptico"""
    
    class Meta:
        model = OpticsResultado
        fields = ['archivo_resultado', 'observaciones']
        widgets = {
            'archivo_resultado': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones del técnico'
            })
        }


class OpticsSolicitudTecnicoForm(forms.ModelForm):
    """Formulario para que el técnico gestione la solicitud"""
    
    class Meta:
        model = OpticsSolicitud
        fields = ['estado', 'codigo_analisis']
        widgets = {
            'estado': forms.Select(attrs={
                'class': 'form-select'
            }),
            'codigo_analisis': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['codigo_analisis'].help_text = "Código generado automáticamente"
