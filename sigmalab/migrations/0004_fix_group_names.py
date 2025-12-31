from django.db import migrations
import unicodedata


VARIANTS = {
    "Técnicos S-LAB": [
        "Técnicos S-LAB",
        "Tecnicos S-LAB",
        "Tecnicos S LAB",
        "Técnicos S LAB",
    ],
    "Técnicos responsables S-MEC": [
        "Técnicos responsables S-MEC",
        "Tecnicos responsables S-MEC",
        "Técnicos responsables S MEC",
        "Tecnicos responsables S MEC",
    ],
    "Técnicos S-MEC": [
        "Técnicos S-MEC",
        "Tecnicos S-MEC",
        "Técnicos S MEC",
        "Tecnicos S MEC",
    ],
}


def _normalize(value: str) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn").casefold()


def normalize_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")

    canonical_by_normalized = {}
    for canonical_name, aliases in VARIANTS.items():
        for alias in aliases:
            canonical_by_normalized[_normalize(alias)] = canonical_name

    for group in Group.objects.all():
        normalized_name = _normalize(group.name)
        new_name = canonical_by_normalized.get(normalized_name)
        if not new_name or group.name == new_name:
            continue
        if Group.objects.filter(name=new_name).exists():
            continue
        group.name = new_name
        group.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("sigmalab", "0003_solicitud_autonomo_diarioentrada"),
        ("auth", "__latest__"),
    ]

    operations = [
        migrations.RunPython(normalize_groups, migrations.RunPython.noop),
    ]
