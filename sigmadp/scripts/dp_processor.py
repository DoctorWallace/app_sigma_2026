#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dp_processor.py — Procesador de datos térmicos para Sigma DP.

Adaptado del script original dp.py para funcionar con Django.
Procesa archivos de datos térmicos y genera gráficas y CSV limpio.
"""

from __future__ import annotations
import re
import os
import tempfile
import unicodedata
from pathlib import Path
from typing import Optional, Tuple, List

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
    base = str(value).replace('º', '').replace('°', '')
    text_val = unicodedata.normalize('NFKD', base)
    text_val = ''.join(ch for ch in text_val if not unicodedata.combining(ch))
    text_val = text_val.replace('[', '(').replace(']', ')')
    text_val = text_val.lower().strip()
    text_val = re.sub(r"\s+", " ", text_val)
    return text_val



def find_column(df: pd.DataFrame, patterns: Tuple[str, ...], exclude: Optional[set] = None) -> Optional[str]:
    """
    Devuelve el nombre REAL de la primera columna cuyo nombre normalizado
    encaje con alguno de los patrones (regex).
    Permite excluir columnas ya utilizadas.
    """
    exclude = exclude or set()
    colmap = {c: normalize_col(str(c)) for c in df.columns if c not in exclude}
    for pat in patterns:
        rx = re.compile(pat)
        for original, normed in colmap.items():
            if rx.search(normed):
                return original
    return None



def read_table(path: Path, sep: str = "\t", decimal: str = ",", encoding: str = "latin1") -> pd.DataFrame:
    """
    Lectura robusta. No fuerza dtype=str para permitir a pandas parsear con 'decimal'.
    """
    df = pd.read_csv(path, sep=sep, decimal=decimal, encoding=encoding, engine="python", header=0)
    return df



def normalize_separator_input(separador: Optional[str]) -> Optional[str]:
    if separador is None:
        return None
    value = str(separador).strip()
    if not value:
        return None
    lower = value.lower()
    if lower in {"auto", "automático", "automatico"}:
        return None
    return SEPARATOR_ALIASES.get(lower, value)

def normalize_decimal_input(decimal: Optional[str]) -> Optional[str]:
    if decimal is None:
        return None
    value = str(decimal).strip()
    if not value:
        return None
    lower = value.lower()
    if lower in {"auto", "automático", "automatico"}:
        return None
    return DECIMAL_ALIASES.get(lower, value[0])

def format_separator_for_storage(sep: str) -> str:
    return "\t" if sep == "	" else sep

def separator_human_label(sep: Optional[str]) -> str:
    if not sep:
        return 'formato especificado'
    storage = format_separator_for_storage(sep)
    return SEPARATOR_LABELS.get(storage, f"separador '{storage}'")

def _sample_lines(path: Path, encoding: str, max_lines: int = 20) -> List[str]:
    lines: List[str] = []
    try:
        with path.open('r', encoding=encoding, errors='replace') as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    lines.append(line.rstrip('\n').rstrip('\r'))
                if len(lines) >= max_lines:
                    break
    except Exception:
        return lines
    return lines

def _detect_encoding(head_bytes: bytes) -> str:
    """Detectar codificación del archivo"""
    import chardet
    enc = chardet.detect(head_bytes).get("encoding") or "utf-8"
    return "utf-8" if enc.lower().startswith("utf") else enc

def _detect_delimiter(sample_text: str) -> str:
    """Detectar separador por conteo de caracteres"""
    lines = [l for l in sample_text.splitlines() if l.strip()][:50]
    sample = "\n".join(lines)
    counts = {c: sample.count(c) for c in [",",";","\t","|"," "]}
    
    # Priorizar tabulador si está presente
    if counts.get("\t", 0) > 0:
        return "\t"
    
    # Priorizar punto y coma si está presente
    if counts.get(";", 0) > 0:
        return ";"
    
    # Si no hay tabulador ni punto y coma, usar el más común
    delim = max(counts, key=counts.get)
    if delim == " " and any(counts[k]>0 for k in [",",";","\t","|"]):
        delim = max({k:v for k,v in counts.items() if k!=" "}, key=lambda k: counts[k])
    return delim

def _detect_decimal(sample_text: str) -> str:
    """Detectar separador decimal por patrones regex"""
    import re
    lines = sample_text.splitlines()[:200]
    comma_dec = sum(bool(re.search(r"\d+,\d+", ln)) for ln in lines)
    dot_dec   = sum(bool(re.search(r"\d+\.\d+", ln)) for ln in lines)
    return "," if comma_dec > dot_dec else "."

def _try_read(text: str, sep: str, dec: str) -> Tuple[pd.DataFrame, Optional[int]]:
    """Intentar leer con diferentes configuraciones de header"""
    import io
    import pandas as pd
    import numpy as np
    
    best, best_score, best_hdr = None, -1, None
    for hdr in range(0,5):
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep, decimal=dec, header=hdr, engine="python")
            score = len(df.select_dtypes(include=[np.number]).columns)
            if score > best_score and len(df)>0 and df.shape[1]>1:
                best, best_score, best_hdr = df, score, hdr
        except Exception:
            continue
    if best is None:
        df = pd.read_csv(io.StringIO(text), sep=sep, decimal=dec, header=None, engine="python", on_bad_lines="skip")
        return df, None
    return best, best_hdr

def _fallback_whitespace(text: str) -> pd.DataFrame:
    """Fallback usando espacios como separador"""
    import io
    import pandas as pd
    
    df = pd.read_csv(io.StringIO(text), sep=r"\s+", engine="python", header=None)
    first = df.iloc[0]
    nonnum = sum(pd.to_numeric(first, errors="coerce").isna())
    if nonnum >= 1:
        hdr = list(first.astype(str).str.strip())
        df = df.drop(index=0).reset_index(drop=True)
        # desambiguar duplicados
        seen, cols = {}, []
        for h in hdr:
            seen[h] = seen.get(h,0)+1
            cols.append(h if seen[h]==1 else f"{h}.{seen[h]}")
        df.columns = cols
    else:
        df.columns = [f"C{i}" for i in range(1, df.shape[1]+1)]
    return df

def _find_time_column(df: pd.DataFrame) -> Optional[str]:
    """Encontrar columna de tiempo automáticamente"""
    import pandas as pd
    import numpy as np
    
    hits = [c for c in df.columns if isinstance(c,str) and any(k in c.lower() for k in ["time","tiempo","[min]","[s]"," min"," sec"])]
    if hits: return hits[0]
    for c in df.select_dtypes(include=[np.number]).columns:
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        if len(s)>3 and (s.is_monotonic_increasing or s.is_monotonic_decreasing):
            return c
    return None

def load_robust(path: Path) -> Tuple[pd.DataFrame, dict]:
    """Carga robusta de archivos de datos con detección automática de formato"""
    import pandas as pd
    
    # Leer archivo
    with open(path, "rb") as f:
        head = f.read(65536)  # ~64 KB
        f.seek(0)
        enc = _detect_encoding(head)
        text = head.decode(enc, errors="replace")
    
    # Detectar propiedades
    sep = _detect_delimiter(text)
    dec = _detect_decimal(text)
    df, hdr = _try_read(text, sep, dec)
    
    # Fallback a whitespace si la estructura es pobre
    import numpy as np
    if df.select_dtypes(include=[np.number]).shape[1] <= 1 or df.shape[1] <= 2:
        df = _fallback_whitespace(text)
        sep = "whitespace"
        dec = "."  # irrelevante tras tokenizar por espacios
        hdr = 0 if not df.columns[0] == 0 else None
    
    # Normalizar nombres y tipos
    df.columns = [str(c).strip().replace("\ufeff","") for c in df.columns]
    df = df.apply(pd.to_numeric, errors="ignore")
    tcol = _find_time_column(df)
    
    meta = {
        "encoding": enc, "sep": sep, "decimal": dec, "header": hdr, 
        "time_column": tcol, "rows": len(df), "ncols": df.shape[1]
    }
    return df, meta

def detect_format_robust(path: Path, encoding: str) -> Tuple[str, str]:
    """Detección robusta de formato usando la función load_robust"""
    try:
        df, meta = load_robust(path)
        return meta["sep"], meta["decimal"]
    except:
        return '\t', ','

def detect_format(path: Path, encoding: str, preferred_sep: Optional[str], preferred_decimal: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    lines = _sample_lines(path, encoding)
    sep_result = preferred_sep
    decimal_result = preferred_decimal
    splitted_lines = None

    candidates: List[str] = []
    if preferred_sep:
        candidates.append(preferred_sep)
    # Priorizar tabulador para archivos de datos térmicos
    candidates.extend(['\t', ' ', ';', ',', '|'])
    seen = set()
    candidate_order: List[str] = []
    for candidate in candidates:
        if candidate not in seen:
            candidate_order.append(candidate)
            seen.add(candidate)

    if sep_result is None:
        best_sep = None
        best_score = -1.0
        best_splitted = None
        
        # Primero intentar con pandas directamente para mejor detección
        try:
            import pandas as pd
            for sep in ['\t', ';', ',', '|']:
                try:
                    # Intentar con diferentes configuraciones
                    for decimal in [',', '.']:
                        test_df = pd.read_csv(path, sep=sep, decimal=decimal, encoding=encoding, engine="python", nrows=5)
                        if len(test_df.columns) >= 4 and len(test_df.columns) <= 10:  # Rango típico para datos térmicos
                            score = len(test_df.columns) * 10
                            if sep == '\t':
                                score += 5  # Bonus para tabulador
                            if score > best_score:
                                best_score = score
                                best_sep = sep
                                break
                except:
                    continue
        except:
            pass
        
        # Si pandas no funcionó, usar método manual
        if best_sep is None:
            for sep in candidate_order:
                try:
                    splitted = [line.split(sep) for line in lines]
                except Exception:
                    continue
                if not splitted:
                    continue
                header_len = len(splitted[0])
                if header_len <= 1:
                    continue
                match_count = 0
                for row in splitted[1:]:
                    if len(row) == header_len:
                        match_count += 1
                total_rows = max(len(splitted) - 1, 1)
                match_ratio = match_count / total_rows
                score = match_ratio * 10.0 + header_len
                if match_count == 0:
                    score -= 5.0
                # Bonus para tabulador si parece ser un archivo de datos térmicos
                if sep == '\t' and header_len >= 4:
                    score += 2.0
                if score > best_score:
                    best_score = score
                    best_sep = sep
                    best_splitted = splitted
        
        sep_result = best_sep or '\t'
        if best_splitted is None:
            try:
                splitted_lines = [line.split(sep_result) for line in lines]
            except Exception:
                splitted_lines = None
        else:
            splitted_lines = best_splitted
    else:
        try:
            splitted_lines = [line.split(sep_result) for line in lines]
        except Exception:
            splitted_lines = None

    if decimal_result is None:
        decimal_counts = {',': 0, '.': 0}
        numeric_pattern = re.compile(r'^-?\d+[\.,]\d+$')
        if splitted_lines:
            for row in splitted_lines[1:]:
                for token in row:
                    token = token.strip()
                    if not token:
                        continue
                    if numeric_pattern.match(token):
                        if ',' in token:
                            decimal_counts[','] += 1
                        if '.' in token:
                            decimal_counts['.'] += 1
        if preferred_decimal in decimal_counts and decimal_counts.get(preferred_decimal):
            decimal_result = preferred_decimal
        elif decimal_counts[','] and decimal_counts[','] >= decimal_counts['.']:
            decimal_result = ','
        elif decimal_counts['.']:
            decimal_result = '.'
        else:
            decimal_result = preferred_decimal or ','

    if sep_result is None:
        sep_result = '\t'
    if decimal_result is None:
        decimal_result = ','
    return sep_result, decimal_result



def load_table(path: Path, sep: Optional[str], decimal: Optional[str], encoding: str = "latin1") -> Tuple[pd.DataFrame, str, str, bool]:
    user_sep = normalize_separator_input(sep)
    user_decimal = normalize_decimal_input(decimal)
    detected = False
    sep_result = user_sep
    decimal_result = user_decimal
    
    # Si no se especifican separador o decimal, usar detección robusta
    if not user_sep or not user_decimal or user_sep == '' or user_decimal == '':
        try:
            df, meta = load_robust(path)
            sep_result = meta["sep"]
            decimal_result = meta["decimal"]
            detected = True
            return df, sep_result, decimal_result, detected
        except Exception as e:
            # Si falla la detección robusta, usar método tradicional
            pass
    
    # Método tradicional si se especifican separador y decimal
    encodings_to_try = [encoding, "cp1252", "latin1", "utf-8", "iso-8859-1"]
    df = None
    encoding_used = encoding
    
    for enc in encodings_to_try:
        try:
            if sep_result is None:
                sep_result = "\t"
            if decimal_result is None:
                decimal_result = ","
            
            df = read_table(path, sep=sep_result, decimal=decimal_result, encoding=enc)
            encoding_used = enc
            break
        except (UnicodeDecodeError, UnicodeError, pd.errors.ParserError) as e:
            continue
    
    if df is None:
        raise ValueError(f"No se pudo leer el archivo con ninguna de las codificaciones: {encodings_to_try}")
    
    return df, sep_result, decimal_result, detected

def _to_numeric_local(s: pd.Series, decimal: str) -> pd.Series:
    """
    Conversión a numérico respetando decimal local.
    Si ya es numérico, devuelve tal cual; si es texto con coma y decimal==',', sustituye.
    """
    if pd.api.types.is_numeric_dtype(s):
        return s
    if s.dtype == object and decimal == ",":
        return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False), errors="coerce")
    return pd.to_numeric(s, errors="coerce")


def standardize_columns(df: pd.DataFrame, decimal: str = ",") -> pd.DataFrame:
    """
    Estandariza nombres y convierte a numérico columnas clave habituales.
    Crea también 'time_h' a partir de 'time_min'.
    """
    out = pd.DataFrame(index=df.index)
    used_columns: set[str] = set()

    # Tiempo principal en minutos
    c_time = find_column(df, (r"^time.*\(min\)$", r"^time.*min$", r"^tiempo", r"^time$"), exclude=used_columns)
    if c_time is None:
        c_time_s = find_column(df, (r"^time.*\(s\)$", r"^time.*sec", r"^seg"), exclude=used_columns)
        if c_time_s is not None:
            used_columns.add(c_time_s)
            out["time_min"] = _to_numeric_local(df[c_time_s], decimal) / 60.0
        else:
            out["time_min"] = np.arange(len(df), dtype=float)
    else:
        used_columns.add(c_time)
        out["time_min"] = _to_numeric_local(df[c_time], decimal)

    # Temperaturas
    c_t_tar = find_column(df, (r"^target.*t", r"^t.*target", r"^set.*t", r"^tset"), exclude=used_columns)
    if c_t_tar is not None:
        used_columns.add(c_t_tar)
        out["t_target_c"] = _to_numeric_local(df[c_t_tar], decimal)

    c_t = find_column(df, (r"^t\s*\(?.*c\)?$", r"^temperatura.*c", r"^t$", r"^temp.*\(c\)$"), exclude=used_columns)
    if c_t is not None:
        used_columns.add(c_t)
        out["t_c"] = _to_numeric_local(df[c_t], decimal)

    c_tsec = find_column(df, (r"^t-?sec", r"^t2$", r"^secondary.*t"), exclude=used_columns)
    if c_tsec is not None:
        used_columns.add(c_tsec)
        out["t_sec_c"] = _to_numeric_local(df[c_tsec], decimal)

    # Log(leak rate)
    c_leak = find_column(df, (r".*log.*leak.*", r".*leak.*log.*", r"^log\(.*leak.*\)"), exclude=used_columns)
    if c_leak is not None:
        used_columns.add(c_leak)
        out["log_leak_mbar_l_s"] = _to_numeric_local(df[c_leak], decimal)

    # Tensión del calefactor
    c_v = find_column(df, (r".*heater.*volt.*", r"^volt.*", r"\bv\b"), exclude=used_columns)
    if c_v is not None:
        used_columns.add(c_v)
        out["heater_v"] = _to_numeric_local(df[c_v], decimal)

    out["time_h"] = out["time_min"] / 60.0
    return out




# ----------------------------- Representación ---------------------------------

def plot_file(std: pd.DataFrame, title: str, outdir: Path, base: str, 
              mostrar_temperatura: bool = True, mostrar_leak: bool = True, 
              mostrar_heater: bool = True, mostrar_overview: bool = True) -> dict:
    """
    Genera figuras individuales y un panel overview si hay ≥2 series útiles.
    Retorna un diccionario con las rutas de los archivos generados.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    archivos_generados = {}

    # 1) Temperaturas
    has_any_t = any(col in std.columns for col in ("t_c", "t_target_c", "t_sec_c"))
    if has_any_t and mostrar_temperatura:
        fig, ax = plt.subplots(figsize=(10, 4.5), dpi=150)
        if "t_c" in std:
            ax.plot(std["time_h"], std["t_c"], label="T [°C]", lw=1.5)
        if "t_sec_c" in std:
            ax.plot(std["time_h"], std["t_sec_c"], label="T-sec [°C]", lw=1.2, alpha=0.9)
        if "t_target_c" in std:
            ax.plot(std["time_h"], std["t_target_c"], label="Target T [°C]", lw=1.2, ls="--")
        ax.set_xlabel("Time [h]")
        ax.set_ylabel("Temperature [°C]")
        ax.set_title(f"{title} — Temperature profile")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend()
        fig.tight_layout()
        temp_path = outdir / f"{base}__temperature.png"
        fig.savefig(temp_path)
        archivos_generados['temperatura'] = temp_path
        plt.close(fig)

    # 2) Log(Leak rate)
    if "log_leak_mbar_l_s" in std and mostrar_leak:
        fig, ax = plt.subplots(figsize=(10, 3.6), dpi=150)
        ax.plot(std["time_h"], std["log_leak_mbar_l_s"], lw=1.2)
        ax.set_xlabel("Time [h]")
        ax.set_ylabel(r"$\log(\mathrm{Leak\ rate}\ [\mathrm{mbar\cdot l \cdot s^{-1}}])$")
        ax.set_title(f"{title} — Log(Leak rate)")
        ax.grid(True, which="both", alpha=0.25)
        fig.tight_layout()
        leak_path = outdir / f"{base}__leak.png"
        fig.savefig(leak_path)
        archivos_generados['leak'] = leak_path
        plt.close(fig)

    # 3) Tensión calefactor
    if "heater_v" in std and mostrar_heater:
        fig, ax = plt.subplots(figsize=(10, 3.6), dpi=150)
        ax.plot(std["time_h"], std["heater_v"], lw=1.2)
        ax.set_xlabel("Time [h]")
        ax.set_ylabel("Heater voltage [V]")
        ax.set_title(f"{title} — Heater voltage")
        ax.grid(True, which="both", alpha=0.25)
        fig.tight_layout()
        heater_path = outdir / f"{base}__heater.png"
        fig.savefig(heater_path)
        archivos_generados['heater'] = heater_path
        plt.close(fig)

    # 4) Panel overview
    ycols = [c for c in ("t_c", "t_target_c", "t_sec_c", "log_leak_mbar_l_s", "heater_v") if c in std]
    if len(ycols) >= 2 and mostrar_overview:
        fig, axes = plt.subplots(nrows=len(ycols), ncols=1, figsize=(11, 2.7 * len(ycols)), dpi=150, sharex=True)
        if len(ycols) == 1:
            axes = [axes]
        labels = {
            "t_c": "T [°C]",
            "t_target_c": "Target T [°C]",
            "t_sec_c": "T-sec [°C]",
            "log_leak_mbar_l_s": r"$\log(\mathrm{Leak\ rate})$ [mbar·l·s$^{-1}$]",
            "heater_v": "Heater voltage [V]",
        }
        for ax, col in zip(axes, ycols):
            ax.plot(std["time_h"], std[col], lw=1.0)
            ax.set_ylabel(labels.get(col, col))
            ax.grid(True, which="both", alpha=0.25)
        axes[-1].set_xlabel("Time [h]")
        fig.suptitle(f"{title} — Overview", y=0.995)
        fig.tight_layout(rect=[0, 0, 1, 0.98])
        overview_path = outdir / f"{base}__overview.png"
        fig.savefig(overview_path)
        archivos_generados['overview'] = overview_path
        plt.close(fig)

    return archivos_generados


def save_clean_csv(std: pd.DataFrame, outdir: Path, base: str) -> Path:
    """Exporta CSV limpio con punto decimal y cabeceras estandarizadas."""
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / f"{base}__clean.csv"
    std.to_csv(csv_path, index=False)
    return csv_path


# ----------------------------- Procesador principal -----------------------------

def procesar_archivo_datos(archivo_path: str, nombre: str, separador: str = "\t", 
                          decimal: str = ",", codificacion: str = "latin1",
                          mostrar_temperatura: bool = True, mostrar_leak: bool = True,
                          mostrar_heater: bool = True, mostrar_overview: bool = True) -> dict:
    """
    Procesa un archivo de datos térmicos y genera gráficas y CSV limpio.
    
    Args:
        archivo_path: Ruta al archivo de datos
        nombre: Nombre del análisis
        separador: Separador de columnas
        decimal: Separador decimal
        codificacion: Codificación del archivo
        mostrar_*: Opciones de qué gráficas generar
    
    Returns:
        dict: Información del procesamiento y rutas de archivos generados
    """
    try:
        # Leer archivo
        path = Path(archivo_path)
        
        # Debug: mostrar información del archivo
        debug_info = {
            'archivo_path': str(path),
            'archivo_existe': path.exists(),
            'tamaño_archivo': path.stat().st_size if path.exists() else 0,
            'separador_solicitado': separador,
            'decimal_solicitado': decimal,
            'codificacion_solicitada': codificacion
        }
        
        df, sep_usado, decimal_usado, auto_detectado = load_table(
            path, separador, decimal, codificacion
        )
        
        debug_info.update({
            'separador_usado': sep_usado,
            'decimal_usado': decimal_usado,
            'auto_detectado': auto_detectado,
            'filas_leidas': len(df),
            'columnas_originales': list(df.columns)
        })

        # Estandarizar columnas
        std = standardize_columns(df, decimal=decimal_usado)
        
        debug_info['columnas_estandarizadas'] = list(std.columns)
        
        # Reconstrucción prudente de 'time_min' si todo es NaN o no existe
        if "time_min" not in std.columns or not np.isfinite(pd.to_numeric(std["time_min"], errors="coerce")).any():
            std["time_min"] = np.arange(len(std), dtype=float)
            std["time_h"] = std["time_min"] / 60.0
        
        # Determina columnas numéricas presentes y con datos
        candidate_cols = ["t_c", "t_target_c", "t_sec_c", "log_leak_mbar_l_s", "heater_v"]
        present_cols = [c for c in candidate_cols if c in std.columns]
        for c in present_cols:
            std[c] = pd.to_numeric(std[c], errors="coerce")
        present_cols = [c for c in present_cols if np.isfinite(std[c].to_numpy()).sum() > 0]
        
        debug_info['columnas_con_datos'] = present_cols
        
        if len(present_cols) == 0:
            return {
                'error': 'No hay columnas con datos numéricos útiles tras la estandarización',
                'columnas_detectadas': list(std.columns),
                'debug_info': debug_info
            }
        
        # Limpieza: elimina filas donde TODAS las y-cols presentes son NaN
        std = std.dropna(subset=present_cols, how="all").reset_index(drop=True)
        
        debug_info['filas_tras_limpieza'] = len(std)
        
        # Crear directorio temporal para archivos de salida
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Generar CSV limpio
            csv_path = save_clean_csv(std, temp_path, nombre)
            
            # Generar gráficas
            archivos_graficas = plot_file(
                std, nombre, temp_path, nombre,
                mostrar_temperatura, mostrar_leak, mostrar_heater, mostrar_overview
            )
            
            # Preparar resultado
            resultado = {
                'exito': True,
                'duracion_minutos': None,
                'num_muestras': len(std),
                'columnas_detectadas': list(std.columns),
                'archivos_generados': {},
                'debug_info': debug_info
            }
            resultado['formato_detectado'] = {
                'separador': format_separator_for_storage(sep_usado),
                'decimal': decimal_usado,
                'descripcion': separator_human_label(sep_usado),
                'automatico': auto_detectado
            }
            
            # Calcular duración
            tvals = pd.to_numeric(std["time_min"], errors="coerce").to_numpy()
            tvals = tvals[np.isfinite(tvals)]
            if tvals.size > 0:
                tmin, tmax = float(np.nanmin(tvals)), float(np.nanmax(tvals))
                duracion_min = tmax - tmin
                resultado['duracion_minutos'] = duracion_min
            
            # Guardar archivos en el storage de Django
            from django.core.files import File
            
            # CSV limpio
            with open(csv_path, 'rb') as f:
                resultado['archivos_generados']['csv'] = File(f, name=f"{nombre}__clean.csv")
            
            # Gráficas
            for tipo, archivo_path in archivos_graficas.items():
                with open(archivo_path, 'rb') as f:
                    resultado['archivos_generados'][tipo] = File(f, name=f"{nombre}__{tipo}.png")
            
            return resultado
            
    except Exception as e:
        import traceback
        return {
            'error': f'Error procesando archivo: {str(e)}',
            'exito': False,
            'debug_info': {
                'archivo_path': archivo_path,
                'archivo_existe': Path(archivo_path).exists() if archivo_path else False,
                'traceback': traceback.format_exc()
            }
        }


