from django.db import migrations
import unicodedata


def strip_accents(text: str) -> str:
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


def clean_alpha(text: str) -> str:
    text = strip_accents(text).upper().strip()
    return "".join(ch for ch in text if ch.isalpha())


def generate_siglas_for(first_name: str, last_name: str, used_upper: set[str]) -> str:
    fn = clean_alpha(first_name) or "X"
    ln_raw = strip_accents(last_name or "").strip()
    parts = [p for p in ln_raw.split() if p]
    s1 = clean_alpha(parts[0]) if parts else clean_alpha(last_name or "") or "X"
    s2 = clean_alpha(parts[1]) if len(parts) > 1 else ""

    initial = fn[0]

    candidates: list[str] = []
    if len(s1) >= 1:
        first = s1[0]
        last = s1[-1]
        candidates.append((initial + first + last).upper())
    if s2:
        candidates.append((initial + s1[:1] + s2[:1]).upper())
    for k in range(1, max(1, len(s1) - 1)):
        try:
            candidates.append((initial + s1[k] + s1[-1]).upper())
        except IndexError:
            break
    # Numerar si hace falta
    extra = []
    for base in list(candidates):
        for n in range(2, 100):
            extra.append(f"{base}{n}")
    candidates.extend(extra)

    for cand in candidates:
        if cand.upper() not in used_upper:
            used_upper.add(cand.upper())
            return cand
    # fallback
    fallback = (initial + "XX").upper()
    if fallback not in used_upper:
        used_upper.add(fallback)
    return fallback


def forwards(apps, schema_editor):
    Profile = apps.get_model("icts", "ICTSUserProfile")
    User = apps.get_model("auth", "User")

    used = set(
        p.user_siglas.upper()
        for p in Profile.objects.exclude(user_siglas__isnull=True)
        if p.user_siglas
    )

    to_fill = Profile.objects.filter(user_siglas__isnull=True)
    for p in to_fill.select_related("user"):
        # Cargar user asociado
        try:
            u = p.user  # historical relation
        except Exception:
            u = User.objects.filter(pk=p.user_id).first()
        first_name = getattr(u, "first_name", "")
        last_name = getattr(u, "last_name", "")
        sig = generate_siglas_for(first_name, last_name, used)
        p.user_siglas = sig
        p.save(update_fields=["user_siglas"])


def backwards(apps, schema_editor):
    # No revertimos los valores asignados
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("icts", "0004_ictsuserprofile_user_siglas_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

