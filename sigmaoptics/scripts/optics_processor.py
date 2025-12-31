#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
optics_processor.py — Procesador de datos ópticos para Sigma Optic.

Procesa archivos de datos ópticos y genera gráficas de espectro, transmitancia, absorbancia y overview.
"""

from __future__ import annotations
import re
import os
import tempfile
import unicodedata
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


# ----------------------------- Utilidades -------------------------------------

SEPARATOR_ALIASES = {
    '\\t': '\t',
    '\\\\t': '\t',
    'tab': '\t',
    'tabulador': '\t',
}

DECIMAL_ALIASES = {
    ',': ',',
    '.': '.',
    'coma': ',',
    'punto': '.',
}

SEPARATOR_LABELS = {
    '\t': 'tabulador (\t)',
    ';': 'punto y coma (;)',
    ',': 'coma (,)',
    '|': 'barra vertical (|)',
}

def normalize_col(value: str) -> str:
    """Normaliza el nombre de columna eliminando diacríticos y símbolos de grado."""
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value))
    cleaned = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return cleaned.strip().casefold()


def detect_separator(file_path: str, encoding: str = 'cp1252') -> str:
    """Detecta automáticamente el separador del archivo."""
    try:
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            # Leer las primeras 10 líneas
            lines = []
            for i, line in enumerate(f):
                if i >= 10:
                    break
                lines.append(line.strip())
        
        if not lines:
            return '\t'
        
        # Contar separadores comunes
        separators = {'\t': 0, ';': 0, ',': 0, '|': 0}
        for line in lines:
            if line:
                for sep in separators:
                    separators[sep] += line.count(sep)
        
        # Retornar el separador más común
        return max(separators, key=separators.get)
    except:
        return '\t'


def detect_decimal_separator(file_path: str, encoding: str = 'cp1252') -> str:
    """Detecta automáticamente el separador decimal."""
    try:
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            # Leer las primeras 20 líneas
            lines = []
            for i, line in enumerate(f):
                if i >= 20:
                    break
                lines.append(line.strip())
        
        # Buscar patrones de números
        comma_count = 0
        dot_count = 0
        
        for line in lines:
            # Buscar números con coma como decimal
            comma_count += len(re.findall(r'\d+,\d+', line))
            # Buscar números con punto como decimal
            dot_count += len(re.findall(r'\d+\.\d+', line))
        
        return ',' if comma_count > dot_count else '.'
    except:
        return '.'


def load_dual_spectrum_csv(file_path: str, separador: str = ',', encoding: str = 'cp1252') -> Tuple[str, pd.DataFrame, pd.DataFrame]:
    """
    CSV con:
      - Fila 0: títulos/nombres
      - Fila 1: encabezados
      - Filas 2..: datos
      - Estructura típica: Wavelength,%T,Wavelength,%T (posibles columnas vacías al final)
    Devuelve: title, df1(x_1,y_1), df2(x_2,y_2) donde cada df tiene columnas x_i,y_i.
    """
    try:
        raw = pd.read_csv(file_path, header=None, sep=separador, engine="python", encoding=encoding)
        raw = raw.dropna(axis=1, how="all")
        headers = raw.iloc[1].tolist()
        headers = [h if isinstance(h, str) and h.strip() != "" else f"col{i}" for i, h in enumerate(headers)]
        data = raw.iloc[2:].copy()
        data.columns = headers
        for c in data.columns:
            data[c] = pd.to_numeric(data[c], errors="coerce")
        title_cells = [str(x) for x in raw.iloc[0].tolist() if pd.notna(x) and str(x).strip() != ""]
        title = " | ".join(title_cells) if title_cells else os.path.basename(file_path)

        cols = list(data.columns)
        pairs = []
        if len(cols) >= 2:
            pairs.append((cols[0], cols[1]))
        if len(cols) >= 4:
            pairs.append((cols[2], cols[3]))

        spectra = []
        for i, (cx, cy) in enumerate(pairs, start=1):
            dfxy = data[[cx, cy]].dropna()
            dfxy = dfxy.rename(columns={cx: f"x_{i}", cy: f"y_{i}"})
            spectra.append(dfxy)
        while len(spectra) < 2:
            spectra.append(None)
        return title, spectra[0], spectra[1]
    except Exception as e:
        raise Exception(f"Error al cargar espectro dual: {str(e)}")


def load_simple_xy_csv(file_path: str, separador: str = ',', encoding: str = 'cp1252') -> pd.DataFrame:
    """
    CSV simple con cabecera en primera fila (p.ej. 'Wavenumber,Intensity')
    y datos desde la segunda. Devuelve df con columnas renombradas a x,y.
    """
    try:
        df = pd.read_csv(file_path, header=0, sep=separador, engine="python", encoding=encoding)
        df = df.dropna(how="all", axis=1)
        if len(df.columns) < 2:
            raise ValueError("El archivo no tiene al menos dos columnas para X e Y.")
        xcol, ycol = df.columns[:2]
        df = df.rename(columns={xcol: "x", ycol: "y"})
        df["x"] = pd.to_numeric(df["x"], errors="coerce")
        df["y"] = pd.to_numeric(df["y"], errors="coerce")
        df = df.dropna(subset=["x", "y"])
        return df
    except Exception as e:
        raise Exception(f"Error al cargar CSV simple: {str(e)}")


def load_data(file_path: str, separador: str = '\t', decimal: str = '.', 
              encoding: str = 'cp1252') -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Carga y procesa el archivo de datos ópticos con algoritmo mejorado."""
    
    # Normalizar separador
    if separador == 'auto':
        separador = detect_separator(file_path, encoding)
    elif separador in SEPARATOR_ALIASES:
        separador = SEPARATOR_ALIASES[separador]
    
    # Normalizar decimal
    if decimal in DECIMAL_ALIASES:
        decimal = DECIMAL_ALIASES[decimal]
    
    try:
        # Intentar formato dual primero
        try:
            title, df1, df2 = load_dual_spectrum_csv(file_path, separador, encoding)
            if df1 is not None and {"x_1", "y_1"}.issubset(df1.columns):
                # Combinar los datos en un solo DataFrame
                df_combined = df1.copy()
                if df2 is not None and {"x_2", "y_2"}.issubset(df2.columns):
                    # Añadir las columnas del segundo espectro
                    df_combined = pd.concat([df_combined, df2], axis=1)
                
                metadata = {
                    'formato_detectado': 'dual_spectrum',
                    'titulo': title,
                    'separador_detectado': separador,
                    'decimal_detectado': decimal,
                    'num_filas': len(df_combined),
                    'num_columnas': len(df_combined.columns),
                    'espectros': 2 if df2 is not None else 1
                }
                
                return df_combined, metadata
        except Exception:
            pass
        
        # Alternativa: formato simple
        try:
            df = load_simple_xy_csv(file_path, separador, encoding)
            
            metadata = {
                'formato_detectado': 'simple_xy',
                'separador_detectado': separador,
                'decimal_detectado': decimal,
                'num_filas': len(df),
                'num_columnas': len(df.columns),
                'espectros': 1
            }
            
            return df, metadata
        except Exception:
            pass
        
        # Fallback: método original
        df = pd.read_csv(
            file_path,
            sep=separador,
            decimal=decimal,
            encoding=encoding,
            na_values=['', 'NA', 'N/A', 'NULL', 'null', 'NULL']
        )
        
        # Limpiar nombres de columnas
        df.columns = [normalize_col(col) for col in df.columns]
        
        # Detectar columnas numéricas
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Detectar columnas de longitud de onda y datos ópticos
        wavelength_cols = [col for col in df.columns if any(keyword in col.lower() 
                          for keyword in ['wavelength', 'lambda', 'nm', 'longitud', 'onda'])]
        
        intensity_cols = [col for col in df.columns if any(keyword in col.lower() 
                         for keyword in ['intensity', 'intensidad', 'absorbance', 'absorbancia', 
                                       'transmittance', 'transmitancia', 'spectrum', 'espectro'])]
        
        # Si no se detectan automáticamente, usar las primeras columnas numéricas
        if not wavelength_cols and numeric_cols:
            wavelength_cols = [numeric_cols[0]]
        if not intensity_cols and len(numeric_cols) > 1:
            intensity_cols = numeric_cols[1:]
        
        metadata = {
            'formato_detectado': 'fallback',
            'separador_detectado': separador,
            'decimal_detectado': decimal,
            'columnas_numericas': numeric_cols,
            'columnas_longitud_onda': wavelength_cols,
            'columnas_intensidad': intensity_cols,
            'num_filas': len(df),
            'num_columnas': len(df.columns),
            'espectros': 1
        }
        
        return df, metadata
        
    except Exception as e:
        raise Exception(f"Error al cargar el archivo: {str(e)}")


def plot_xy(df: pd.DataFrame, xlabel: str, ylabel: str, title: str, outpath: str) -> bytes:
    """Función auxiliar para crear gráficas XY genéricas."""
    plt.figure(figsize=(12, 8))
    plt.plot(df.iloc[:, 0], df.iloc[:, 1], linewidth=2)
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Guardar en bytes
    buffer = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    plt.savefig(buffer.name, dpi=300, bbox_inches='tight')
    plt.close()
    
    with open(buffer.name, 'rb') as f:
        image_data = f.read()
    
    os.unlink(buffer.name)
    return image_data


def create_spectrum_plot(df: pd.DataFrame, metadata: Dict[str, Any], title: str = "Espectro Óptico") -> bytes:
    """Crea gráfica de espectro óptico con algoritmo mejorado."""
    plt.figure(figsize=(12, 8))
    
    formato = metadata.get('formato_detectado', 'fallback')
    
    if formato == 'dual_spectrum':
        # Manejar espectros duales
        if 'x_1' in df.columns and 'y_1' in df.columns:
            plt.plot(df['x_1'], df['y_1'], label='Espectro 1', linewidth=2)
        if 'x_2' in df.columns and 'y_2' in df.columns:
            plt.plot(df['x_2'], df['y_2'], label='Espectro 2', linewidth=2)
        plt.xlabel('Longitud de Onda (nm)', fontsize=12)
        plt.ylabel('%T', fontsize=12)
        if metadata.get('titulo'):
            title = f"{title} - {metadata['titulo']}"
    elif formato == 'simple_xy':
        # Manejar formato simple XY
        if 'x' in df.columns and 'y' in df.columns:
            plt.plot(df['x'], df['y'], linewidth=2)
        plt.xlabel('X', fontsize=12)
        plt.ylabel('Y', fontsize=12)
    else:
        # Fallback: método original
        wavelength_cols = metadata.get('columnas_longitud_onda', [])
        intensity_cols = metadata.get('columnas_intensidad', [])
        
        if wavelength_cols and intensity_cols:
            wavelength_col = wavelength_cols[0]
            for i, intensity_col in enumerate(intensity_cols[:5]):  # Máximo 5 curvas
                if wavelength_col in df.columns and intensity_col in df.columns:
                    plt.plot(df[wavelength_col], df[intensity_col], 
                            label=f'Curva {i+1}', linewidth=2)
        plt.xlabel('Longitud de Onda (nm)', fontsize=12)
        plt.ylabel('Intensidad', fontsize=12)
    
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    if len(plt.gca().get_lines()) > 1:
        plt.legend()
    plt.tight_layout()
    
    # Guardar en bytes
    buffer = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    plt.savefig(buffer.name, dpi=300, bbox_inches='tight')
    plt.close()
    
    with open(buffer.name, 'rb') as f:
        image_data = f.read()
    
    os.unlink(buffer.name)
    return image_data


def create_transmittance_plot(df: pd.DataFrame, metadata: Dict[str, Any], title: str = "Transmitancia") -> bytes:
    """Crea gráfica de transmitancia con algoritmo mejorado."""
    plt.figure(figsize=(12, 8))
    
    formato = metadata.get('formato_detectado', 'fallback')
    
    if formato == 'dual_spectrum':
        # Manejar espectros duales
        if 'x_1' in df.columns and 'y_1' in df.columns:
            plt.plot(df['x_1'], df['y_1'], label='Transmitancia 1', linewidth=2)
        if 'x_2' in df.columns and 'y_2' in df.columns:
            plt.plot(df['x_2'], df['y_2'], label='Transmitancia 2', linewidth=2)
        plt.xlabel('Longitud de Onda (nm)', fontsize=12)
        plt.ylabel('%T', fontsize=12)
    elif formato == 'simple_xy':
        # Manejar formato simple XY
        if 'x' in df.columns and 'y' in df.columns:
            plt.plot(df['x'], df['y'], linewidth=2)
        plt.xlabel('X', fontsize=12)
        plt.ylabel('Y', fontsize=12)
    else:
        # Fallback: método original
        wavelength_cols = metadata.get('columnas_longitud_onda', [])
        intensity_cols = metadata.get('columnas_intensidad', [])
        
        if wavelength_cols and intensity_cols:
            wavelength_col = wavelength_cols[0]
            for i, intensity_col in enumerate(intensity_cols[:5]):
                if wavelength_col in df.columns and intensity_col in df.columns:
                    # Calcular transmitancia (normalizar a 100%)
                    data = df[intensity_col].dropna()
                    if len(data) > 0:
                        transmittance = (data / data.max()) * 100
                        plt.plot(df[wavelength_col], transmittance, 
                                label=f'Transmitancia {i+1}', linewidth=2)
        plt.xlabel('Longitud de Onda (nm)', fontsize=12)
        plt.ylabel('Transmitancia (%)', fontsize=12)
    
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    if len(plt.gca().get_lines()) > 1:
        plt.legend()
    plt.tight_layout()
    
    buffer = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    plt.savefig(buffer.name, dpi=300, bbox_inches='tight')
    plt.close()
    
    with open(buffer.name, 'rb') as f:
        image_data = f.read()
    
    os.unlink(buffer.name)
    return image_data


def create_absorbance_plot(df: pd.DataFrame, metadata: Dict[str, Any], title: str = "Absorbancia") -> bytes:
    """Crea gráfica de absorbancia con algoritmo mejorado."""
    plt.figure(figsize=(12, 8))
    
    formato = metadata.get('formato_detectado', 'fallback')
    
    if formato == 'dual_spectrum':
        # Manejar espectros duales
        if 'x_1' in df.columns and 'y_1' in df.columns:
            plt.plot(df['x_1'], df['y_1'], label='Absorbancia 1', linewidth=2)
        if 'x_2' in df.columns and 'y_2' in df.columns:
            plt.plot(df['x_2'], df['y_2'], label='Absorbancia 2', linewidth=2)
        plt.xlabel('Longitud de Onda (nm)', fontsize=12)
        plt.ylabel('Absorbancia', fontsize=12)
    elif formato == 'simple_xy':
        # Manejar formato simple XY
        if 'x' in df.columns and 'y' in df.columns:
            plt.plot(df['x'], df['y'], linewidth=2)
        plt.xlabel('X', fontsize=12)
        plt.ylabel('Y', fontsize=12)
    else:
        # Fallback: método original
        wavelength_cols = metadata.get('columnas_longitud_onda', [])
        intensity_cols = metadata.get('columnas_intensidad', [])
        
        if wavelength_cols and intensity_cols:
            wavelength_col = wavelength_cols[0]
            for i, intensity_col in enumerate(intensity_cols[:5]):
                if wavelength_col in df.columns and intensity_col in df.columns:
                    # Calcular absorbancia: A = -log10(T/100)
                    data = df[intensity_col].dropna()
                    if len(data) > 0:
                        transmittance = (data / data.max()) * 100
                        absorbance = -np.log10(transmittance / 100 + 1e-10)  # Evitar log(0)
                        # Filtrar valores infinitos
                        valid_mask = np.isfinite(absorbance)
                        if valid_mask.any():
                            plt.plot(df[wavelength_col][valid_mask], absorbance[valid_mask], 
                                    label=f'Absorbancia {i+1}', linewidth=2)
        plt.xlabel('Longitud de Onda (nm)', fontsize=12)
        plt.ylabel('Absorbancia', fontsize=12)
    
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    if len(plt.gca().get_lines()) > 1:
        plt.legend()
    plt.tight_layout()
    
    buffer = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    plt.savefig(buffer.name, dpi=300, bbox_inches='tight')
    plt.close()
    
    with open(buffer.name, 'rb') as f:
        image_data = f.read()
    
    os.unlink(buffer.name)
    return image_data


def create_overview_plot(df: pd.DataFrame, metadata: Dict[str, Any], title: str = "Resumen Óptico") -> bytes:
    """Crea gráfica de resumen con múltiples subplots usando algoritmo mejorado."""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(title, fontsize=16, fontweight='bold')
    
    formato = metadata.get('formato_detectado', 'fallback')
    
    if formato == 'dual_spectrum':
        # Manejar espectros duales
        if 'x_1' in df.columns and 'y_1' in df.columns:
            axes[0, 0].plot(df['x_1'], df['y_1'], label='Espectro 1', linewidth=2)
            axes[0, 1].plot(df['x_1'], df['y_1'], label='Transmitancia 1', linewidth=2)
            axes[1, 0].plot(df['x_1'], df['y_1'], label='Absorbancia 1', linewidth=2)
        if 'x_2' in df.columns and 'y_2' in df.columns:
            axes[0, 0].plot(df['x_2'], df['y_2'], label='Espectro 2', linewidth=2)
            axes[0, 1].plot(df['x_2'], df['y_2'], label='Transmitancia 2', linewidth=2)
            axes[1, 0].plot(df['x_2'], df['y_2'], label='Absorbancia 2', linewidth=2)
        
        axes[0, 0].set_xlabel('Longitud de Onda (nm)')
        axes[0, 0].set_ylabel('%T')
        axes[0, 1].set_xlabel('Longitud de Onda (nm)')
        axes[0, 1].set_ylabel('%T')
        axes[1, 0].set_xlabel('Longitud de Onda (nm)')
        axes[1, 0].set_ylabel('Absorbancia')
        
    elif formato == 'simple_xy':
        # Manejar formato simple XY
        if 'x' in df.columns and 'y' in df.columns:
            axes[0, 0].plot(df['x'], df['y'], linewidth=2)
            axes[0, 1].plot(df['x'], df['y'], linewidth=2)
            axes[1, 0].plot(df['x'], df['y'], linewidth=2)
        
        axes[0, 0].set_xlabel('X')
        axes[0, 0].set_ylabel('Y')
        axes[0, 1].set_xlabel('X')
        axes[0, 1].set_ylabel('Y')
        axes[1, 0].set_xlabel('X')
        axes[1, 0].set_ylabel('Y')
        
    else:
        # Fallback: método original
        wavelength_cols = metadata.get('columnas_longitud_onda', [])
        intensity_cols = metadata.get('columnas_intensidad', [])
        
        if wavelength_cols and intensity_cols:
            wavelength_col = wavelength_cols[0]
            
            # Espectro original
            for i, intensity_col in enumerate(intensity_cols[:3]):
                if wavelength_col in df.columns and intensity_col in df.columns:
                    axes[0, 0].plot(df[wavelength_col], df[intensity_col], 
                                   label=f'Curva {i+1}', linewidth=2)
            axes[0, 0].set_xlabel('Longitud de Onda (nm)')
            axes[0, 0].set_ylabel('Intensidad')
            
            # Transmitancia
            for i, intensity_col in enumerate(intensity_cols[:3]):
                if wavelength_col in df.columns and intensity_col in df.columns:
                    data = df[intensity_col].dropna()
                    if len(data) > 0:
                        transmittance = (data / data.max()) * 100
                        axes[0, 1].plot(df[wavelength_col], transmittance, 
                                       label=f'Transmitancia {i+1}', linewidth=2)
            axes[0, 1].set_xlabel('Longitud de Onda (nm)')
            axes[0, 1].set_ylabel('Transmitancia (%)')
            
            # Absorbancia
            for i, intensity_col in enumerate(intensity_cols[:3]):
                if wavelength_col in df.columns and intensity_col in df.columns:
                    data = df[intensity_col].dropna()
                    if len(data) > 0:
                        transmittance = (data / data.max()) * 100
                        absorbance = -np.log10(transmittance / 100 + 1e-10)
                        valid_mask = np.isfinite(absorbance)
                        if valid_mask.any():
                            axes[1, 0].plot(df[wavelength_col][valid_mask], absorbance[valid_mask], 
                                           label=f'Absorbancia {i+1}', linewidth=2)
            axes[1, 0].set_xlabel('Longitud de Onda (nm)')
            axes[1, 0].set_ylabel('Absorbancia')
    
    # Configurar subplots
    axes[0, 0].set_title('Espectro Original')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].legend()
    
    axes[0, 1].set_title('Transmitancia')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].legend()
    
    axes[1, 0].set_title('Absorbancia')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].legend()
    
    # Estadísticas
    axes[1, 1].set_title('Estadísticas')
    stats_text = f"Puntos de datos: {len(df)}\n"
    stats_text += f"Columnas: {len(df.columns)}\n"
    stats_text += f"Formato: {formato}\n"
    if formato == 'dual_spectrum' and metadata.get('titulo'):
        stats_text += f"Título: {metadata['titulo']}\n"
    if 'x_1' in df.columns:
        stats_text += f"Rango X: {df['x_1'].min():.1f} - {df['x_1'].max():.1f}"
    elif 'x' in df.columns:
        stats_text += f"Rango X: {df['x'].min():.1f} - {df['x'].max():.1f}"
    axes[1, 1].text(0.1, 0.5, stats_text, fontsize=12, 
                    verticalalignment='center', transform=axes[1, 1].transAxes)
    axes[1, 1].axis('off')
    
    plt.tight_layout()
    
    buffer = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    plt.savefig(buffer.name, dpi=300, bbox_inches='tight')
    plt.close()
    
    with open(buffer.name, 'rb') as f:
        image_data = f.read()
    
    os.unlink(buffer.name)
    return image_data


def procesar_archivo_optics(archivo_path: str, nombre: str, separador: str = '\t', 
                          decimal: str = '.', codificacion: str = 'cp1252',
                          mostrar_espectro: bool = True, mostrar_transmitancia: bool = True,
                          mostrar_absorbancia: bool = True, mostrar_overview: bool = True) -> Dict[str, Any]:
    """
    Procesa un archivo de datos ópticos y genera gráficas.
    
    Args:
        archivo_path: Ruta al archivo de datos
        nombre: Nombre del análisis
        separador: Separador de columnas
        decimal: Separador decimal
        codificacion: Codificación del archivo
        mostrar_espectro: Generar gráfica de espectro
        mostrar_transmitancia: Generar gráfica de transmitancia
        mostrar_absorbancia: Generar gráfica de absorbancia
        mostrar_overview: Generar gráfica de resumen
    
    Returns:
        Dict con el resultado del procesamiento
    """
    try:
        # Cargar datos
        df, metadata = load_data(archivo_path, separador, decimal, codificacion)
        
        if df.empty:
            return {
                'exito': False,
                'error': 'El archivo está vacío o no se pudieron cargar los datos'
            }
        
        # Obtener columnas detectadas
        wavelength_cols = metadata.get('columnas_longitud_onda', [])
        intensity_cols = metadata.get('columnas_intensidad', [])
        
        if not wavelength_cols and not intensity_cols:
            # Si no se detectan automáticamente, usar las primeras columnas numéricas
            numeric_cols = metadata.get('columnas_numericas', [])
            if len(numeric_cols) >= 2:
                wavelength_cols = [numeric_cols[0]]
                intensity_cols = numeric_cols[1:]
            else:
                return {
                    'exito': False,
                    'error': 'No se pudieron detectar columnas de longitud de onda e intensidad'
                }
        
        # Generar archivos
        archivos_generados = {}
        
        # CSV limpio
        csv_buffer = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        df.to_csv(csv_buffer.name, index=False, encoding='utf-8')
        with open(csv_buffer.name, 'rb') as f:
            archivos_generados['csv'] = ContentFile(f.read(), name=f"{nombre}_clean.csv")
        os.unlink(csv_buffer.name)
        
        # Gráficas usando algoritmo mejorado
        if mostrar_espectro:
            try:
                archivos_generados['espectro'] = ContentFile(
                    create_spectrum_plot(df, metadata, f"Espectro - {nombre}"),
                    name=f"{nombre}_espectro.png"
                )
            except Exception as e:
                print(f"Error generando espectro: {e}")
        
        if mostrar_transmitancia:
            try:
                archivos_generados['transmitancia'] = ContentFile(
                    create_transmittance_plot(df, metadata, f"Transmitancia - {nombre}"),
                    name=f"{nombre}_transmitancia.png"
                )
            except Exception as e:
                print(f"Error generando transmitancia: {e}")
        
        if mostrar_absorbancia:
            try:
                archivos_generados['absorbancia'] = ContentFile(
                    create_absorbance_plot(df, metadata, f"Absorbancia - {nombre}"),
                    name=f"{nombre}_absorbancia.png"
                )
            except Exception as e:
                print(f"Error generando absorbancia: {e}")
        
        if mostrar_overview:
            try:
                archivos_generados['overview'] = ContentFile(
                    create_overview_plot(df, metadata, f"Resumen - {nombre}"),
                    name=f"{nombre}_overview.png"
                )
            except Exception as e:
                print(f"Error generando overview: {e}")
        
        return {
            'exito': True,
            'archivos_generados': archivos_generados,
            'duracion_minutos': len(df) / 1000,  # Estimación
            'num_muestras': len(intensity_cols),
            'columnas_detectadas': list(df.columns),
            'metadata': metadata
        }
        
    except Exception as e:
        return {
            'exito': False,
            'error': str(e)
        }
