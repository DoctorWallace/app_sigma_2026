#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dp.py — Representación genérica de ensayos térmicos (tab, coma decimal).

Funcionalidad:
  - Lee uno o varios ficheros tabulados con coma decimal y codificación Latin-1 (editable).
  - Estandariza columnas típicas a: time_min, time_h, t_target_c, t_c, t_sec_c,
    log_leak_mbar_l_s, heater_v.
  - Genera figuras PNG (temperatura, leak log, tensión, y panel overview) y un CSV limpio.
  - Auto-descubre ficheros si no se pasan argumentos (P*, N*, *.txt, *.tsv o --pattern).

Uso básico:
  py dp.py
  py dp.py P250401 N7588
  py dp.py --decimal "," --sep "\t" --outdir figuras

Requisitos:
  Python 3.9+  |  pip install pandas matplotlib numpy
"""

from __future__ import annotations
import argparse
import re
from pathlib import Path
from typing import Optional, Tuple, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ----------------------------- Utilidades -------------------------------------

def normalize_col(s: str) -> str:
    """Normaliza nombre de columna: minúsculas, sin acentos tipográficos, espacios compactados."""
    s0 = s.strip().lower()
    repl = {
        "º": "°",
        "°c": "c",
        "°": "",
        "·": "*",
        "−": "-",
        "’": "'",
        "”": '"',
        "“": '"',
    }
    for k, v in repl.items():
        s0 = s0.replace(k, v)
    s0 = re.sub(r"\s+", " ", s0)
    s0 = s0.replace("[", "(").replace("]", ")")
    return s0


def find_column(df: pd.DataFrame, patterns: Tuple[str, ...]) -> Optional[str]:
    """
    Devuelve el nombre REAL de la primera columna cuyo nombre normalizado
    encaje con alguno de los patrones (regex).
    """
    colmap = {c: normalize_col(str(c)) for c in df.columns}
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
    df = pd.read_csv(path, sep=sep, decimal=decimal, encoding=encoding, engine="python")
    return df


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

    # Tiempo principal en minutos
    c_time = find_column(df, (r"^time.*\(min\)$", r"^time.*min$", r"^tiempo", r"^time$"))
    if c_time is None:
        c_time_s = find_column(df, (r"^time.*\(s\)$", r"^time.*sec", r"^seg"))
        if c_time_s is not None:
            out["time_min"] = _to_numeric_local(df[c_time_s], decimal) / 60.0
        else:
            out["time_min"] = np.arange(len(df), dtype=float)  # índice relativo si no hay tiempo
    else:
        out["time_min"] = _to_numeric_local(df[c_time], decimal)

    # Temperaturas
    c_t_tar = find_column(df, (r"^target.*t", r"^t.*target", r"^set.*t", r"^tset"))
    if c_t_tar is not None:
        out["t_target_c"] = _to_numeric_local(df[c_t_tar], decimal)

    c_t = find_column(df, (r"^t\s*\(?.*c\)?$", r"^t$", r"^temp.*\(c\)$"))
    if c_t is not None:
        out["t_c"] = _to_numeric_local(df[c_t], decimal)

    c_tsec = find_column(df, (r"^t-?sec", r"^t2$", r"^secondary.*t"))
    if c_tsec is not None:
        out["t_sec_c"] = _to_numeric_local(df[c_tsec], decimal)

    # Log(leak rate)
    c_leak = find_column(df, (r".*log.*leak.*", r".*leak.*log.*", r"^log\(.*leak.*\)"))
    if c_leak is not None:
        out["log_leak_mbar_l_s"] = _to_numeric_local(df[c_leak], decimal)

    # Tensión del calefactor
    c_v = find_column(df, (r".*heater.*volt.*", r"^volt.*", r"\bv\b"))
    if c_v is not None:
        out["heater_v"] = _to_numeric_local(df[c_v], decimal)

    out["time_h"] = out["time_min"] / 60.0
    return out


# ----------------------------- Representación ---------------------------------

def plot_file(std: pd.DataFrame, title: str, outdir: Path, base: str) -> None:
    """
    Genera figuras individuales y un panel overview si hay ≥2 series útiles.
    """
    outdir.mkdir(parents=True, exist_ok=True)

    # 1) Temperaturas
    has_any_t = any(col in std.columns for col in ("t_c", "t_target_c", "t_sec_c"))
    if has_any_t:
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
        fig.savefig(outdir / f"{base}__temperature.png")
        plt.close(fig)

    # 2) Log(Leak rate)
    if "log_leak_mbar_l_s" in std:
        fig, ax = plt.subplots(figsize=(10, 3.6), dpi=150)
        ax.plot(std["time_h"], std["log_leak_mbar_l_s"], lw=1.2)
        ax.set_xlabel("Time [h]")
        ax.set_ylabel(r"$\log(\mathrm{Leak\ rate}\ [\mathrm{mbar\cdot l \cdot s^{-1}}])$")
        ax.set_title(f"{title} — Log(Leak rate)")
        ax.grid(True, which="both", alpha=0.25)
        fig.tight_layout()
        fig.savefig(outdir / f"{base}__leak.png")
        plt.close(fig)

    # 3) Tensión calefactor
    if "heater_v" in std:
        fig, ax = plt.subplots(figsize=(10, 3.6), dpi=150)
        ax.plot(std["time_h"], std["heater_v"], lw=1.2)
        ax.set_xlabel("Time [h]")
        ax.set_ylabel("Heater voltage [V]")
        ax.set_title(f"{title} — Heater voltage")
        ax.grid(True, which="both", alpha=0.25)
        fig.tight_layout()
        fig.savefig(outdir / f"{base}__heater.png")
        plt.close(fig)

    # 4) Panel overview
    ycols = [c for c in ("t_c", "t_target_c", "t_sec_c", "log_leak_mbar_l_s", "heater_v") if c in std]
    if len(ycols) >= 2:
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
        fig.savefig(outdir / f"{base}__overview.png")
        plt.close(fig)


def save_clean_csv(std: pd.DataFrame, outdir: Path, base: str) -> None:
    """Exporta CSV limpio con punto decimal y cabeceras estandarizadas."""
    outdir.mkdir(parents=True, exist_ok=True)
    std.to_csv(outdir / f"{base}__clean.csv", index=False)


# ----------------------------- Programa principal -----------------------------

def main():
    parser = argparse.ArgumentParser(description="Representación genérica de ficheros de ensayo térmico (tab, coma decimal).")
    parser.add_argument("files", nargs="*", help="Rutas a los ficheros a procesar. Si se omite, se autodetectan.")
    parser.add_argument("--sep", default="\\t", help="Separador (por defecto: tabulador). Use '\\t' para tab.")
    parser.add_argument("--decimal", default=",", help="Separador decimal (por defecto: ',').")
    parser.add_argument("--encoding", default="latin1", help="Codificación (por defecto: latin1).")
    parser.add_argument("--outdir", default="figuras", help="Directorio de salida para PNG y CSV limpios.")
    parser.add_argument("--pattern", default="", help="Patrón glob adicional para autodetección (p.ej. '*.dat').")
    args = parser.parse_args()

    # Normaliza separador visual "\t" -> carácter tab real
    sep = "\t" if args.sep in ("\\t", "TAB", "tab", "\t") else args.sep
    outdir = Path(args.outdir)

    # Lista de ficheros
    file_list: List[Path] = [Path(f) for f in args.files]
    if not file_list:
        # Auto-descubrimiento en carpeta actual
        cwd = Path.cwd()
        candidatas = set()
        for pat in ("*.txt", "*.tsv", "P*", "N*"):
            candidatas.update(cwd.glob(pat))
        if args.pattern:
            candidatas.update(cwd.glob(args.pattern))
        file_list = [p for p in sorted(candidatas) if p.is_file()]
        if not file_list:
            print("[ERROR] No se proporcionaron ficheros ni se encontraron candidatos en la carpeta actual.")
            print("       Pasa rutas explícitas o usa --pattern, p. ej.: --pattern '*.dat'")
            return

    for path in file_list:
        if not path.exists():
            print(f"[ADVERTENCIA] No existe: {path}")
            continue

        try:
            raw = read_table(path, sep=sep, decimal=args.decimal, encoding=args.encoding)
        except Exception as e:
            print(f"[ERROR] Fallo leyendo {path.name}: {e}")
            continue

        std = standardize_columns(raw, decimal=args.decimal)

        # Reconstrucción prudente de 'time_min' si todo es NaN o no existe
        if "time_min" not in std.columns or not np.isfinite(pd.to_numeric(std["time_min"], errors="coerce")).any():
            std["time_min"] = np.arange(len(std), dtype=float)
            std["time_h"] = std["time_min"] / 60.0
            print(f"[AVISO] {path.name}: no se pudo inferir tiempo real. Se usa índice relativo (1 min por muestra).")

        # Determina columnas numéricas presentes y con datos
        candidate_cols = ["t_c", "t_target_c", "t_sec_c", "log_leak_mbar_l_s", "heater_v"]
        present_cols = [c for c in candidate_cols if c in std.columns]
        for c in present_cols:
            std[c] = pd.to_numeric(std[c], errors="coerce")
        present_cols = [c for c in present_cols if np.isfinite(std[c].to_numpy()).sum() > 0]

        if len(present_cols) == 0:
            print(f"[AVISO] {path.name}: no hay columnas con datos numéricos útiles tras la estandarización. Revisa separador/decimal/encoding.")
            save_clean_csv(std, outdir, path.stem)
            continue

        # Limpieza: elimina filas donde TODAS las y-cols presentes son NaN
        std = std.dropna(subset=present_cols, how="all").reset_index(drop=True)

        base = path.stem
        title = base

        save_clean_csv(std, outdir, base)
        plot_file(std, title, outdir, base)

        # Estadísticos seguros
        tvals = pd.to_numeric(std["time_min"], errors="coerce").to_numpy()
        tvals = tvals[np.isfinite(tvals)]
        if tvals.size > 0:
            tmin, tmax = float(np.nanmin(tvals)), float(np.nanmax(tvals))
            dur_min = tmax - tmin
            print(f"{base}: duración = {dur_min:.2f} min ({dur_min/60:.2f} h); muestras = {len(std)}; columnas = {list(std.columns)}")
        else:
            print(f"{base}: sin tiempo válido; muestras = {len(std)}; columnas = {list(std.columns)}")

    print("Listo.")


if __name__ == "__main__":
    main()
