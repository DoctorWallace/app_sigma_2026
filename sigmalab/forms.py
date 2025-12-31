from django import forms
from django.contrib.auth.models import User
from .models import Sample, Solicitud, Avance, DiarioEntrada, MuestraIndividual, SolicitudModificacion, SolicitudAnulacion, IncidenciaLaboratorio, RespuestaIncidencia, UsuarioAsociado, MensajeInterno, EquipoLaboratorio, PrestamoEquipo, NotificacionPrestamo


class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = ["code", "title", "notes"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "Código único"}),
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "Título descriptivo"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 5, "placeholder": "Notas (opcional)"}),
        }


class SolicitudForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = [
            "material",
            "numero_muestras",
            "material_radioactivo",
            "manejo_especial",
            "tratamiento_previo",
            "procedencia",
            "otro_dato_importante",
            "requisitos_finales",
            "observaciones",
            "imagen_muestra",
            "croquis",
            "corte",
            "empastillado",
            "lijado",
            "pulido",
            "electropulido",
            "trat_quimico",
            "trat_termico",
        ]
        widgets = {
            "material": forms.TextInput(attrs={"class": "form-input", "placeholder": "Material"}),
            "numero_muestras": forms.NumberInput(attrs={"class": "form-input", "min": 1, "max": 20}),
            "manejo_especial": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Describe el manejo especial requerido"}),
            "tratamiento_previo": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Describe el tratamiento previo realizado"}),
            "procedencia": forms.TextInput(attrs={"class": "form-input", "placeholder": "Procedencia de la muestra"}),
            "otro_dato_importante": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Otro dato importante de la muestra"}),
            "requisitos_finales": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Requisitos finales"}),
            "observaciones": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Observaciones (Trabajo autónomo)"}),
            "imagen_muestra": forms.FileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "croquis": forms.FileInput(attrs={"class": "form-input", "accept": "image/*"}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer que los campos de archivos no sean obligatorios
        self.fields['imagen_muestra'].required = False
        self.fields['croquis'].required = False


class MuestraIndividualForm(forms.ModelForm):
    class Meta:
        model = MuestraIndividual
        fields = ['identificacion', 'descripcion']
        widgets = {
            'identificacion': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Identificación de la muestra'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Descripción adicional'}),
        }


# Formset para manejar múltiples muestras
MuestraIndividualFormSet = forms.inlineformset_factory(
    Solicitud,
    MuestraIndividual,
    form=MuestraIndividualForm,
    extra=0,  # Se añadirán dinámicamente
    can_delete=False,
)


class AvanceForm(forms.ModelForm):
    class Meta:
        model = Avance
        fields = ["tipo", "contenido", "adjunto", "visible_para_usuario"]
        widgets = {
            "contenido": forms.Textarea(attrs={"rows": 4, "placeholder": "Describe el avance o mensaje."}),
        }


class EstadoForm(forms.Form):
    ACCION = (
        ("aceptar", "Aceptar"),
        ("rechazar", "Rechazar"),
        ("finalizar", "Finalizar"),
    )
    accion = forms.ChoiceField(choices=ACCION)
    codigo_muestra = forms.CharField(required=False, max_length=20)


class DiarioEntradaForm(forms.ModelForm):
    class Meta:
        model = DiarioEntrada
        fields = ["fecha", "etapa", "nota"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "etapa": forms.Select(attrs={"class": "form-input"}),
            "nota": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "form-input",
                    "placeholder": "Anota incidencias, tareas realizadas, etc.",
                }
            ),
        }


# ========= Formulario de Solicitud de Modificación =========
class SolicitudModificacionForm(forms.ModelForm):
    class Meta:
        model = SolicitudModificacion
        fields = [
            'tipo_modificacion', 
            'descripcion_cambio', 
            'justificacion'
        ]
        widgets = {
            'tipo_modificacion': forms.Select(attrs={
                'class': 'form-control',
                'onchange': 'toggleModificationFields()'
            }),
            'descripcion_cambio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe detalladamente qué cambios quieres realizar...'
            }),
            'justificacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explica por qué necesitas estos cambios...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.solicitud = kwargs.pop('solicitud', None)
        super().__init__(*args, **kwargs)
        
        # Añadir campos dinámicos según el tipo de modificación
        self.fields['nuevo_numero_muestras'] = forms.IntegerField(
            required=False,
            min_value=1,
            max_value=20,
            widget=forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nuevo número de muestras'
            })
        )
        
        self.fields['nuevos_requisitos_finales'] = forms.CharField(
            required=False,
            widget=forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Nuevos requisitos finales...'
            })
        )
        
        self.fields['nuevas_observaciones'] = forms.CharField(
            required=False,
            widget=forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Nuevas observaciones...'
            })
        )
        
        self.fields['nuevo_otro_dato_importante'] = forms.CharField(
            required=False,
            widget=forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Nuevos datos importantes...'
            })
        )
        
        self.fields['nuevo_manejo_especial'] = forms.CharField(
            required=False,
            widget=forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Nuevo manejo especial...'
            })
        )
        
        self.fields['nuevo_tratamiento_previo'] = forms.CharField(
            required=False,
            widget=forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Nuevo tratamiento previo...'
            })
        )
        
        self.fields['nueva_procedencia'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nueva procedencia...'
            })
        )
        
        # Campos para etapas de preparación
        etapas = [
            'corte', 'empastillado', 'lijado', 'pulido', 
            'electropulido', 'trat_quimico', 'trat_termico'
        ]
        
        for etapa in etapas:
            self.fields[f'nueva_{etapa}'] = forms.BooleanField(
                required=False,
                widget=forms.CheckboxInput(attrs={
                    'class': 'form-check-input'
                })
            )
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_modificacion = cleaned_data.get('tipo_modificacion')
        
        # Validar que se proporcionen los datos necesarios según el tipo
        if tipo_modificacion == 'numero_muestras':
            nuevo_numero = cleaned_data.get('nuevo_numero_muestras')
            if not nuevo_numero or nuevo_numero <= 0:
                self.add_error('nuevo_numero_muestras', 'Debes especificar un número válido de muestras (1-20)')
        
        elif tipo_modificacion == 'requisitos_finales':
            nuevos_requisitos = cleaned_data.get('nuevos_requisitos_finales')
            if not nuevos_requisitos or not nuevos_requisitos.strip():
                self.add_error('nuevos_requisitos_finales', 'Debes especificar los nuevos requisitos finales')
        
        elif tipo_modificacion == 'observaciones':
            nuevas_observaciones = cleaned_data.get('nuevas_observaciones')
            if not nuevas_observaciones or not nuevas_observaciones.strip():
                self.add_error('nuevas_observaciones', 'Debes especificar las nuevas observaciones')
        
        elif tipo_modificacion == 'otro_dato_importante':
            nuevo_dato = cleaned_data.get('nuevo_otro_dato_importante')
            if not nuevo_dato or not nuevo_dato.strip():
                self.add_error('nuevo_otro_dato_importante', 'Debes especificar los nuevos datos importantes')
        
        elif tipo_modificacion == 'manejo_especial':
            nuevo_manejo = cleaned_data.get('nuevo_manejo_especial')
            if not nuevo_manejo or not nuevo_manejo.strip():
                self.add_error('nuevo_manejo_especial', 'Debes especificar el nuevo manejo especial')
        
        elif tipo_modificacion == 'tratamiento_previo':
            nuevo_tratamiento = cleaned_data.get('nuevo_tratamiento_previo')
            if not nuevo_tratamiento or not nuevo_tratamiento.strip():
                self.add_error('nuevo_tratamiento_previo', 'Debes especificar el nuevo tratamiento previo')
        
        elif tipo_modificacion == 'procedencia':
            nueva_procedencia = cleaned_data.get('nueva_procedencia')
            if not nueva_procedencia or not nueva_procedencia.strip():
                self.add_error('nueva_procedencia', 'Debes especificar la nueva procedencia')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Configurar la solicitud original y el solicitante
        if self.solicitud:
            instance.solicitud_original = self.solicitud
        
        # Preparar los cambios solicitados según el tipo
        cambios = {}
        tipo_modificacion = self.cleaned_data.get('tipo_modificacion')
        
        if tipo_modificacion == 'numero_muestras':
            cambios['numero_muestras'] = self.cleaned_data.get('nuevo_numero_muestras')
        
        elif tipo_modificacion == 'requisitos_finales':
            cambios['requisitos_finales'] = self.cleaned_data.get('nuevos_requisitos_finales')
        
        elif tipo_modificacion == 'observaciones':
            cambios['observaciones'] = self.cleaned_data.get('nuevas_observaciones')
        
        elif tipo_modificacion == 'otro_dato_importante':
            cambios['otro_dato_importante'] = self.cleaned_data.get('nuevo_otro_dato_importante')
        
        elif tipo_modificacion == 'manejo_especial':
            cambios['manejo_especial'] = self.cleaned_data.get('nuevo_manejo_especial')
        
        elif tipo_modificacion == 'tratamiento_previo':
            cambios['tratamiento_previo'] = self.cleaned_data.get('nuevo_tratamiento_previo')
        
        elif tipo_modificacion == 'procedencia':
            cambios['procedencia'] = self.cleaned_data.get('nueva_procedencia')
        
        elif tipo_modificacion == 'etapas_preparacion':
            etapas = ['corte', 'empastillado', 'lijado', 'pulido', 'electropulido', 'trat_quimico', 'trat_termico']
            for etapa in etapas:
                cambios[etapa] = self.cleaned_data.get(f'nueva_{etapa}', False)
        
        instance.cambios_solicitados = cambios
        
        if commit:
            instance.save()
        
        return instance


# ========= Formulario de Aprobación de Modificación (para técnicos) =========
class AprobarModificacionForm(forms.ModelForm):
    class Meta:
        model = SolicitudModificacion
        fields = ['estado', 'comentarios_tecnico']
        widgets = {
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'comentarios_tecnico': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Comentarios sobre la modificación...'
            })
        }


# ========= Formulario de Anulación de Solicitud =========
class SolicitudAnulacionForm(forms.ModelForm):
    class Meta:
        model = SolicitudAnulacion
        fields = ['justificacion', 'tipo_anulacion']
        widgets = {
            'justificacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Explica por qué quieres anular esta solicitud...'
            }),
            'tipo_anulacion': forms.HiddenInput(),  # Se establece automáticamente
        }
    
    def __init__(self, *args, **kwargs):
        self.solicitud = kwargs.pop('solicitud', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Establecer el tipo de anulación según el estado de la solicitud
        if self.solicitud:
            if self.solicitud.estado == 'pendiente':
                self.fields['tipo_anulacion'].initial = 'usuario_pendiente'
            elif self.solicitud.estado in ['aceptada', 'en_curso']:
                self.fields['tipo_anulacion'].initial = 'usuario_aceptada'
    
    def clean_justificacion(self):
        justificacion = self.cleaned_data.get('justificacion')
        if not justificacion or not justificacion.strip():
            raise forms.ValidationError('Debes proporcionar una justificación para anular la solicitud.')
        if len(justificacion.strip()) < 10:
            raise forms.ValidationError('La justificación debe tener al menos 10 caracteres.')
        return justificacion.strip()
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.solicitud = self.solicitud
        instance.usuario_anulacion = self.user
        
        if commit:
            instance.save()
            
            # Cambiar el estado de la solicitud
            if self.solicitud.estado == 'pendiente':
                # Si está pendiente, se puede eliminar o marcar como anulada
                self.solicitud.estado = Solicitud.Estado.ANULADA
            else:
                # Si está aceptada o en curso, solo se marca como anulada (mantiene el código)
                self.solicitud.estado = Solicitud.Estado.ANULADA
            
            self.solicitud.save()
        
        return instance


# ========= Formulario de Estimación de Tiempo =========
class TiempoEstimacionForm(forms.Form):
    tiempo_estimado_numero = forms.IntegerField(
        label="Número",
        min_value=1,
        max_value=30,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '1-30'
        })
    )
    
    tiempo_estimado_unidad = forms.ChoiceField(
        label="Unidad de tiempo",
        choices=[
            ('', 'Seleccionar unidad'),
            ('dias', 'Días'),
            ('semanas', 'Semanas'),
            ('meses', 'Meses'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    tiempo_estimado_indeterminado = forms.BooleanField(
        label="Indeterminado",
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        indeterminado = cleaned_data.get('tiempo_estimado_indeterminado')
        numero = cleaned_data.get('tiempo_estimado_numero')
        unidad = cleaned_data.get('tiempo_estimado_unidad')
        
        if not indeterminado:
            if not numero or not unidad:
                raise forms.ValidationError(
                    'Debes especificar un número y una unidad de tiempo, o marcar "Indeterminado".'
                )
        
        return cleaned_data
    
    def get_tiempo_display(self):
        """Retorna el tiempo estimado en formato legible"""
        if self.cleaned_data.get('tiempo_estimado_indeterminado'):
            return "Indeterminado"
        
        numero = self.cleaned_data.get('tiempo_estimado_numero')
        unidad = self.cleaned_data.get('tiempo_estimado_unidad')
        
        if not numero or not unidad:
            return "No especificado"
        
        unidad_display = dict(self.fields['tiempo_estimado_unidad'].choices).get(unidad, unidad)
        return f"{numero} {unidad_display}"


# ========= Formularios de Incidencias del Laboratorio =========

class IncidenciaForm(forms.ModelForm):
    class Meta:
        model = IncidenciaLaboratorio
        fields = [
            'titulo', 'descripcion', 'categoria', 'prioridad',
            'ubicacion', 'equipos_afectados', 'archivo_adjunto',
            'impacto_operaciones', 'acciones_inmediatas'
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título descriptivo de la incidencia'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe detalladamente la incidencia...'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-control'
            }),
            'prioridad': forms.Select(attrs={
                'class': 'form-control'
            }),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ubicación específica (ej: Laboratorio 1, Sala de equipos)'
            }),
            'equipos_afectados': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Equipos o sistemas afectados'
            }),
            'archivo_adjunto': forms.ClearableFileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*,.pdf,.doc,.docx'
            }),
            'impacto_operaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe el impacto en las operaciones del laboratorio...'
            }),
            'acciones_inmediatas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Acciones inmediatas tomadas o recomendadas...'
            }),
        }
        labels = {
            'titulo': 'Título de la incidencia',
            'descripcion': 'Descripción detallada',
            'categoria': 'Categoría',
            'prioridad': 'Prioridad',
            'ubicacion': 'Ubicación',
            'equipos_afectados': 'Equipos afectados',
            'archivo_adjunto': 'Archivo adjunto',
            'impacto_operaciones': 'Impacto en operaciones',
            'acciones_inmediatas': 'Acciones inmediatas',
        }
    
    def clean_titulo(self):
        titulo = self.cleaned_data.get('titulo')
        if not titulo or len(titulo.strip()) < 5:
            raise forms.ValidationError('El título debe tener al menos 5 caracteres.')
        return titulo.strip()
    
    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion')
        if not descripcion or len(descripcion.strip()) < 10:
            raise forms.ValidationError('La descripción debe tener al menos 10 caracteres.')
        return descripcion.strip()


class RespuestaIncidenciaForm(forms.ModelForm):
    class Meta:
        model = RespuestaIncidencia
        fields = ['mensaje', 'es_resolucion', 'archivo_adjunto']
        widgets = {
            'mensaje': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Escribe tu respuesta o actualización...'
            }),
            'es_resolucion': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'archivo_adjunto': forms.ClearableFileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*,.pdf,.doc,.docx'
            }),
        }
        labels = {
            'mensaje': 'Mensaje',
            'es_resolucion': 'Marcar como resolución',
            'archivo_adjunto': 'Archivo adjunto',
        }
    
    def clean_mensaje(self):
        mensaje = self.cleaned_data.get('mensaje')
        if not mensaje or len(mensaje.strip()) < 5:
            raise forms.ValidationError('El mensaje debe tener al menos 5 caracteres.')
        return mensaje.strip()


class GestionarIncidenciaForm(forms.ModelForm):
    class Meta:
        model = IncidenciaLaboratorio
        fields = ['estado', 'asignado_a', 'prioridad']
        widgets = {
            'estado': forms.Select(attrs={
                'class': 'form-control'
            }),
            'asignado_a': forms.Select(attrs={
                'class': 'form-control'
            }),
            'prioridad': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'estado': 'Estado',
            'asignado_a': 'Asignar a',
            'prioridad': 'Prioridad',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo técnicos para la asignación
        self.fields['asignado_a'].queryset = User.objects.filter(
            groups__name__in=['tecnico_responsable_s_lab', 'tecnico_responsable_s_mec']
        ).order_by('first_name', 'last_name')


# ========= Formularios para Gestión de Becarios =========

class UsuarioAsociadoForm(forms.ModelForm):
    """Formulario para crear/editar becarios asociados"""
    
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
                'placeholder': 'Nombre del becario'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Apellidos del becario'
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
                'placeholder': 'Observaciones adicionales sobre el becario...'
            }),
        }
        labels = {
            'investigador_principal': 'Usuario DTF responsable',
            'nombre': 'Nombre',
            'apellidos': 'Apellidos',
            'email': 'Email',
            'telefono': 'Teléfono',
            'tipo_becario': 'Tipo de becario',
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
            # Si no es técnico, solo puede ver sus propios becarios (no debería llegar aquí)
            self.fields['investigador_principal'].queryset = User.objects.none()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        investigador_principal = self.cleaned_data.get('investigador_principal')
        
        if email and investigador_principal:
            # Verificar que no exista otro becario con el mismo email para este investigador
            queryset = UsuarioAsociado.objects.filter(
                investigador_principal=investigador_principal,
                email=email
            )
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError(
                    f'Ya existe un becario asociado con este email para {investigador_principal.get_full_name()}.'
                )
        
        return email
    
    def clean_fecha_fin(self):
        fecha_inicio = self.cleaned_data.get('fecha_inicio')
        fecha_fin = self.cleaned_data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise forms.ValidationError(
                'La fecha de finalización debe ser posterior a la fecha de inicio.'
            )
        
        return fecha_fin
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.creado_por:
            instance.creado_por = self.creado_por
        
        if commit:
            instance.save()
        
        return instance


class SolicitudConBecarioForm(forms.ModelForm):
    """Formulario de solicitud que incluye selección de becario"""
    
    class Meta:
        model = Solicitud
        fields = [
            "material",
            "numero_muestras",
            "material_radioactivo",
            "manejo_especial",
            "tratamiento_previo",
            "procedencia",
            "otro_dato_importante",
            "requisitos_finales",
            "observaciones",
            "imagen_muestra",
            "croquis",
            "corte",
            "empastillado",
            "lijado",
            "pulido",
            "electropulido",
            "trat_quimico",
            "trat_termico",
            "becario_asociado",
        ]
        widgets = {
            "material": forms.TextInput(attrs={"class": "form-input", "placeholder": "Material"}),
            "numero_muestras": forms.NumberInput(attrs={"class": "form-input", "min": 1, "max": 20}),
            "manejo_especial": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Describe el manejo especial requerido"}),
            "tratamiento_previo": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Describe el tratamiento previo realizado"}),
            "procedencia": forms.TextInput(attrs={"class": "form-input", "placeholder": "Procedencia de la muestra"}),
            "otro_dato_importante": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Otro dato importante de la muestra"}),
            "requisitos_finales": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Requisitos finales"}),
            "observaciones": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Observaciones (Trabajo autónomo)"}),
            "imagen_muestra": forms.FileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "croquis": forms.FileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "becario_asociado": forms.Select(attrs={"class": "form-input"}),
        }
    
    def __init__(self, *args, **kwargs):
        self.solicitante = kwargs.pop('solicitante', None)
        super().__init__(*args, **kwargs)
        
        # Hacer que los campos de archivos no sean obligatorios
        self.fields['imagen_muestra'].required = False
        self.fields['croquis'].required = False
        self.fields['becario_asociado'].required = False
        
        # Filtrar becarios activos del solicitante
        if self.solicitante:
            self.fields['becario_asociado'].queryset = UsuarioAsociado.objects.filter(
                investigador_principal=self.solicitante,
                estado='activo'
            ).order_by('nombre', 'apellidos')
            
            # Añadir opción vacía
            self.fields['becario_asociado'].empty_label = "Sin becario asociado"
        
        # Añadir etiqueta
        self.fields['becario_asociado'].label = "Becario que realizará la solicitud"
        self.fields['becario_asociado'].help_text = "Selecciona un becario si la solicitud será realizada por él/ella"


# ========= Formularios de Mensajes Internos =========

class MensajeInternoForm(forms.ModelForm):
    """Formulario para crear mensajes internos"""
    
    class Meta:
        model = MensajeInterno
        fields = ['destinatario', 'asunto', 'contenido', 'tipo_mensaje', 'solicitud']
        widgets = {
            'destinatario': forms.Select(attrs={
                'class': 'form-input',
                'placeholder': 'Seleccionar destinatario...'
            }),
            'asunto': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Asunto del mensaje...'
            }),
            'contenido': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Escribe tu mensaje aquí...'
            }),
            'tipo_mensaje': forms.Select(attrs={
                'class': 'form-input'
            }),
            'solicitud': forms.Select(attrs={
                'class': 'form-input'
            }),
        }
        labels = {
            'destinatario': 'Para',
            'asunto': 'Asunto',
            'contenido': 'Mensaje',
            'tipo_mensaje': 'Tipo',
            'solicitud': 'Solicitud relacionada (opcional)',
        }
    
    def __init__(self, *args, **kwargs):
        self.remitente = kwargs.pop('remitente', None)
        super().__init__(*args, **kwargs)

        # Hacer que la solicitud no sea obligatoria
        self.fields['solicitud'].required = False
        self.fields['solicitud'].empty_label = "Sin solicitud relacionada"

        # Filtrar destinatarios según el tipo de usuario
        if self.remitente:
            if self.remitente.groups.filter(name='tecnico_responsable_s_lab').exists():
                # Si es técnico, puede enviar a usuarios DTF
                self.fields['destinatario'].queryset = User.objects.filter(
                    groups__name='usuarios_dtf'
                ).order_by('first_name', 'last_name')
            else:
                # Si es usuario DTF, puede enviar a técnicos
                self.fields['destinatario'].queryset = User.objects.filter(
                    groups__name='tecnico_responsable_s_lab'
                ).order_by('first_name', 'last_name')

        # Filtrar solicitudes del remitente
        if self.remitente:
            self.fields['solicitud'].queryset = Solicitud.objects.filter(
                solicitante=self.remitente
            ).order_by('-creado_en')

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.remitente:
            instance.remitente = self.remitente
        if commit:
            instance.save()
        return instance


# ========= FORMULARIOS PARA SISTEMA DE EQUIPOS =========

class EquipoLaboratorioForm(forms.ModelForm):
    """Formulario para crear y editar equipos del laboratorio"""
    
    class Meta:
        model = EquipoLaboratorio
        fields = [
            'nombre', 'codigo', 'descripcion', 'categoria',
            'disponible_para_prestamo', 'ubicacion_laboratorio',
            'requiere_mantenimiento', 'instrucciones_uso', 'observaciones'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del equipo'
            }),
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código único del equipo'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción detallada del equipo'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-control'
            }),
            'ubicacion_laboratorio': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ubicación dentro del laboratorio'
            }),
            'instrucciones_uso': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Instrucciones de uso y manejo'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales'
            }),
        }
        labels = {
            'nombre': 'Nombre del Equipo',
            'codigo': 'Código Único',
            'descripcion': 'Descripción',
            'categoria': 'Categoría',
            'disponible_para_prestamo': 'Disponible para Préstamo',
            'ubicacion_laboratorio': 'Ubicación en el Laboratorio',
            'requiere_mantenimiento': 'Requiere Mantenimiento Especial',
            'instrucciones_uso': 'Instrucciones de Uso',
            'observaciones': 'Observaciones',
        }
    
    def __init__(self, *args, **kwargs):
        self.creado_por = kwargs.pop('creado_por', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.creado_por:
            instance.creado_por = self.creado_por
        if commit:
            instance.save()
        return instance


class PrestamoEquipoForm(forms.ModelForm):
    """Formulario para solicitar préstamo de equipos"""
    
    class Meta:
        model = PrestamoEquipo
        fields = ['equipo', 'dias_prestamo', 'proposito_uso', 'observaciones_prestamo']
        widgets = {
            'equipo': forms.Select(attrs={
                'class': 'form-control'
            }),
            'dias_prestamo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 30,
                'placeholder': 'Número de días'
            }),
            'proposito_uso': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe el propósito del uso del equipo'
            }),
            'observaciones_prestamo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones adicionales'
            }),
        }
        labels = {
            'equipo': 'Equipo a Prestar',
            'dias_prestamo': 'Días de Préstamo',
            'proposito_uso': 'Propósito del Uso',
            'observaciones_prestamo': 'Observaciones',
        }
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        self.tecnico_responsable = kwargs.pop('tecnico_responsable', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar solo equipos disponibles
        if 'equipo' in self.fields:
            self.fields['equipo'].queryset = EquipoLaboratorio.objects.filter(
                estado='disponible',
                disponible_para_prestamo=True
            ).order_by('nombre')
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.usuario:
            instance.usuario = self.usuario
        if self.tecnico_responsable:
            instance.tecnico_responsable = self.tecnico_responsable
        
        # Calcular fecha de devolución estimada
        from django.utils import timezone
        from datetime import timedelta
        instance.fecha_devolucion_estimada = timezone.now() + timedelta(days=instance.dias_prestamo)
        
        if commit:
            instance.save()
            # Actualizar estado del equipo
            instance.equipo.estado = 'prestado'
            instance.equipo.save()
        return instance


class DevolucionEquipoForm(forms.ModelForm):
    """Formulario para devolver equipos"""
    
    class Meta:
        model = PrestamoEquipo
        fields = ['observaciones_devolucion']
        widgets = {
            'observaciones_devolucion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones sobre la devolución del equipo'
            }),
        }
        labels = {
            'observaciones_devolucion': 'Observaciones de la Devolución',
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.marcar_como_devuelto(instance.observaciones_devolucion)
        return instance


class BuscarEquipoForm(forms.Form):
    """Formulario para buscar equipos"""
    
    BUSCAR_POR_CHOICES = [
        ('nombre', 'Nombre'),
        ('codigo', 'Código'),
        ('categoria', 'Categoría'),
    ]
    
    buscar_por = forms.ChoiceField(
        choices=BUSCAR_POR_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    termino_busqueda = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Término de búsqueda'
        })
    )
    solo_disponibles = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['buscar_por'].label = 'Buscar por'
        self.fields['termino_busqueda'].label = 'Término de Búsqueda'
        self.fields['solo_disponibles'].label = 'Solo equipos disponibles'


class FiltroPrestamosForm(forms.Form):
    """Formulario para filtrar préstamos"""
    
    ESTADO_CHOICES = [
        ('', 'Todos los estados'),
        ('activo', 'Activos'),
        ('devuelto', 'Devueltos'),
        ('vencido', 'Vencidos'),
        ('perdido', 'Perdidos'),
    ]
    
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    usuario = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="Todos los usuarios",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    equipo = forms.ModelChoiceField(
        queryset=EquipoLaboratorio.objects.all(),
        required=False,
        empty_label="Todos los equipos",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado'].label = 'Estado'
        self.fields['usuario'].label = 'Usuario'
        self.fields['equipo'].label = 'Equipo'
        self.fields['fecha_desde'].label = 'Fecha Desde'
        self.fields['fecha_hasta'].label = 'Fecha Hasta'

