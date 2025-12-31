from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from icts.models import AccessProposal
from .models import SEMAnalysis, SEMSample

User = get_user_model()


class SEMAnalysisForm(forms.ModelForm):
    """Formulario para crear análisis SEM/FIB"""
    
    class Meta:
        model = SEMAnalysis
        fields = [
            'access_proposal',
            'analysis_type',
            'analysis_date',
            'client_requirements',
            'observations',
            'session_comments'
        ]
        widgets = {
            'access_proposal': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_access_proposal'
            }),
            'analysis_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_analysis_type'
            }),
            'analysis_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'client_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Requerimientos del cliente'
            }),
            'observations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones del técnico'
            }),
            'session_comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Comentarios y observaciones durante la sesión'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar propuestas que tengan SEM o FIB seleccionado
        from django.db import models
        self.fields['access_proposal'].queryset = AccessProposal.objects.filter(
            status='accepted'
        ).filter(
            models.Q(facility_sem=True) | models.Q(facility_sem_fib=True)
        ).order_by('-created_at')
        
        # Establecer fecha por defecto
        if not self.instance.pk:
            self.fields['analysis_date'].initial = timezone.now().date()


class SEMSampleForm(forms.ModelForm):
    """Formulario para agregar muestras adicionales"""
    
    class Meta:
        model = SEMSample
        fields = ['identification', 'name', 'description']
        widgets = {
            'identification': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Identificación de la muestra'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la muestra'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la muestra'
            })
        }


class SampleSelectionForm(forms.Form):
    """Formulario para seleccionar muestras de la propuesta ICTS"""
    
    selected_samples = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        help_text="Selecciona las muestras de la propuesta ICTS"
    )
    
    def __init__(self, proposal=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if proposal:
            # Obtener muestras de la propuesta ICTS
            samples = []
            if hasattr(proposal, 'samples') and proposal.samples:
                for sample in proposal.samples:
                    samples.append((sample.id, f"{sample.name} - {sample.description}"))
            
            self.fields['selected_samples'].choices = samples


class AddSampleForm(forms.Form):
    """Formulario para agregar una nueva muestra durante la sesión"""
    
    identification = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Identificación de la muestra'
        })
    )
    
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de la muestra'
        })
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Descripción de la muestra'
        })
    )


class FileBrowserForm(forms.Form):
    """Formulario para el explorador de archivos"""
    
    folder_path = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ruta de la carpeta',
            'id': 'folder-path'
        }),
        help_text="Selecciona una carpeta que contenga archivos de imagen (.jpg, .png, .tiff)"
    )
