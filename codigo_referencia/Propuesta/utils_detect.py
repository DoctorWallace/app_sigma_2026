# sigmadp/utils_detect.py
import io, re, pandas as pd, numpy as np, chardet
from typing import Optional, Tuple

def _detect_encoding(head: bytes) -> str:
    guess = chardet.detect(head).get("encoding") or "utf-8"
    return "utf-8" if guess.lower().startswith("utf") else guess

def _detect_delimiter(sample: str) -> str:
    lines = [l for l in sample.splitlines() if l.strip()][:50]
    text = "\n".join(lines)
    counts = {c: text.count(c) for c in [",",";","\t","|"," "]}
    delim = max(counts, key=counts.get) if counts else ","
    if delim == " " and any(counts[k] for k in [",",";","\t","|"]):
        delim = max({k:v for k,v in counts.items() if k!=" "}, key=lambda k: counts[k])
    return delim

def _detect_decimal(sample: str) -> str:
    lines = sample.splitlines()[:200]
    c = sum(bool(re.search(r"\d+,\d+", l)) for l in lines)
    d = sum(bool(re.search(r"\d+\.\d+", l)) for l in lines)
    return "," if c > d else "."

def _try_read_csv(text: str, sep: str, dec: str) -> Tuple[pd.DataFrame, Optional[int]]:
    best, score, hdr_best = None, -1, None
    for hdr in range(0, 5):
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep, decimal=dec, header=hdr, engine="python")
            if df.shape[1] > 1:
                s = len(df.select_dtypes(include=[np.number]).columns)
                if s > score:
                    best, score, hdr_best = df, s, hdr
        except Exception:
            pass
    if best is None:
        try:
            best = pd.read_csv(io.StringIO(text), sep=sep, decimal=dec, header=None, engine="python", on_bad_lines="skip")
        except Exception:
            best = pd.DataFrame()
    return best, hdr_best

def _fallback_whitespace(text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text), sep=r"\s+", engine="python", header=None)
    if not df.empty:
        first = df.iloc[0]
        if sum(pd.to_numeric(first, errors="coerce").isna()) >= 1:
            hdr = list(first.astype(str).str.strip())
            df = df.drop(index=0).reset_index(drop=True)
            seen, cols = {}, []
            for h in hdr:
                seen[h] = seen.get(h,0)+1
                cols.append(h if seen[h]==1 else f"{h}.{seen[h]}")
            df.columns = cols
        else:
            df.columns = [f"C{i}" for i in range(1, df.shape[1]+1)]
    return df

def _find_time_column(df: pd.DataFrame) -> Optional[str]:
    hits = [c for c in df.columns if isinstance(c,str) and any(k in c.lower() for k in ["time","tiempo","[min]","[s]"," min"," sec"])]
    if hits: return hits[0]
    for c in df.select_dtypes(include=[np.number]).columns:
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        if len(s) > 3 and (s.is_monotonic_increasing or s.is_monotonic_decreasing):
            return c
    return None

def detect_and_preview(upload) -> dict:
    head = upload.read(65536)
    upload.seek(0)
    enc = _detect_encoding(head)
    text = head.decode(enc, errors="replace")
    sep = _detect_delimiter(text)
    dec = _detect_decimal(text)
    df, hdr = _try_read_csv(text, sep, dec)
    if df.empty or df.shape[1] <= 1 or df.select_dtypes(include=[np.number]).shape[1] <= 1:
        df = _fallback_whitespace(text)
        sep, dec, hdr = "whitespace", ".", None  # el decimal es irrelevante tras tokenizar
    df.columns = [str(c).strip().replace("\ufeff","") for c in df.columns]
    df = df.apply(pd.to_numeric, errors="ignore")
    tcol = _find_time_column(df)
    preview = df.head(20)
    # salida lista para la plantilla
    return {
        "encoding": enc,
        "separator": sep,
        "decimal": dec,
        "header": hdr,
        "columns": list(df.columns),
        "rows": int(len(df)),
        "ncols": int(df.shape[1]),
        "time_column": tcol,
        "preview_rows": preview.to_dict(orient="records")
    }
