"""
Módulo centralizado para la gestión de roles y grupos de usuarios.
Define constantes normalizadas y utilidades para verificar pertenencia a grupos.
"""
import unicodedata
from typing import Iterable, Optional, Set


def normalize_group_name(name: str) -> str:
    """Return a lower-cased, accent-free representation of a group name."""
    if not name:
        return ""
    normalized = unicodedata.normalize("NFKD", name)
    cleaned = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return cleaned.strip().casefold()


def _clean_targets(candidates: Iterable[str]) -> Set[str]:
    return {normalize_group_name(name) for name in candidates if name}


# Grupos ICTS
ICTS_CORE_GROUPS = _clean_targets({"icts_users", "users_icts"})
RESPONSABLE_GROUPS = _clean_targets({"responsables", "responsable"})
REVIEWER_GROUPS = _clean_targets({"revisores", "reviewers", "revisor", "reviewer"})
MANAGER_GROUPS = _clean_targets({"managers", "manager"})

# Grupos técnicos por módulo
SLAB_TECH_GROUPS = _clean_targets({
    "tecnico_responsable_s_lab",
    "tecnicos_responsables_s_lab",
    "tecnicos responsables s lab",
    "s-lab technicians",
})
MEC_TECH_GROUPS = _clean_targets({
    "tecnico_responsable_s_mec",
    "tecnicos_responsables_s_mec",
    "tecnicos responsables s mec",
    "s-mec technicians",
})
DP_TECH_GROUPS = _clean_targets({
    "tecnico_responsable_s_dp",
    "tecnicos_responsables_s_dp",
    "tecnicos responsables s dp",
    "tecnicos-responsables-s-dp",
    "tecnicos_s_dp",
})
OPTICS_TECH_GROUPS = _clean_targets({
    "tecnico_responsable_s_optics",
    "tecnicos_responsables_s_optics",
    "tecnicos responsables s optics",
    "s-optics technicians",
})
SEM_TECH_GROUPS = _clean_targets({
    "tecnicos_sem_fib",
    "tecnico_responsable_s_sem",
    "tecnico_responsable_s_fib",
    "tecnico_responsable_sem",
    "tecnico_responsable_fib",
    "sem technicians",
    "fib technicians",
})
IMP_TECH_GROUPS = _clean_targets({
    "imp_technicians",
    "implant_technicians",
    "implant technicians",
    "implant-technicians",
    "tecnico_imp",
    "tecnico implantador",
    "tecnicos implantador",
})
VDG_TECH_GROUPS = _clean_targets({
    "vdg_technicians",
    "vdg technicians",
    "vdg-technicians",
    "tecnico_vdg",
    "tecnico vdg",
    "tecnicos vdg",
})
CONF_TECH_GROUPS = _clean_targets({
    "confocal technicians",
    "confocal_technicians",
    "confocal-technicians",
    "tecnico_responsable_s_conf",
    "tecnicos_responsables_s_conf",
    "tecnico confocal",
})
OLMAT_TECH_GROUPS = _clean_targets({
    "olmat technicians",
    "olmat_technicians",
    "olmat-technicians",
    "olmat",
    "olmat tech",
    "ictsolmat",
    "tecnico_responsable_s_olmat",
    "tecnicos_responsables_s_olmat",
    "tecnico olmat",
    "tecnico_olmat",
})

ICTS_TECH_GROUPS = (
    SEM_TECH_GROUPS
    | IMP_TECH_GROUPS
    | VDG_TECH_GROUPS
    | CONF_TECH_GROUPS
    | OLMAT_TECH_GROUPS
)

# Grupos de usuarios DTF
DTF_USER_GROUPS = _clean_targets({
    "usuarios_dtf",
    "usuarios_autonomo_s_lab",
})

# Agrupaciones útiles
ALL_TECH_GROUPS = (
    SLAB_TECH_GROUPS
    | MEC_TECH_GROUPS
    | DP_TECH_GROUPS
    | OPTICS_TECH_GROUPS
    | SEM_TECH_GROUPS
    | IMP_TECH_GROUPS
    | VDG_TECH_GROUPS
    | CONF_TECH_GROUPS
    | OLMAT_TECH_GROUPS
)
ALL_DTF_GROUPS = (
    DTF_USER_GROUPS | SLAB_TECH_GROUPS | MEC_TECH_GROUPS | DP_TECH_GROUPS | OPTICS_TECH_GROUPS
)


def get_normalized_user_groups(user) -> Set[str]:
    """Obtiene los grupos normalizados de un usuario."""
    if not getattr(user, "is_authenticated", False):
        return set()
    return {
        normalize_group_name(name)
        for name in user.groups.values_list("name", flat=True)
    }


def user_in_groups(
    user,
    candidates: Iterable[str],
    groups: Optional[Set[str]] = None,
) -> bool:
    """Verifica si un usuario pertenece a alguno de los grupos candidatos."""
    if not getattr(user, "is_authenticated", False):
        return False
    targets = set(candidates)
    if not targets:
        return False
    group_names = groups or get_normalized_user_groups(user)
    return bool(group_names & targets)


def is_reviewer(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es revisor."""
    return getattr(user, "is_superuser", False) or user_in_groups(
        user, REVIEWER_GROUPS, groups
    )


def is_responsable(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es responsable."""
    return getattr(user, "is_superuser", False) or user_in_groups(
        user, RESPONSABLE_GROUPS, groups
    )


def is_manager(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es manager."""
    return user_in_groups(user, MANAGER_GROUPS, groups)


def is_icts_user(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario tiene acceso a ICTS."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    group_names = groups or get_normalized_user_groups(user)
    if group_names & (ICTS_CORE_GROUPS | ICTS_TECH_GROUPS):
        return True
    return any(
        checker(user, group_names)
        for checker in (is_reviewer, is_responsable, is_manager)
    )


def is_slab_tech(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es técnico de S-LAB."""
    return user_in_groups(user, SLAB_TECH_GROUPS, groups)


def is_mec_tech(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es técnico de S-MEC."""
    return user_in_groups(user, MEC_TECH_GROUPS, groups)


def is_dp_tech(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es técnico de S-DP."""
    return user_in_groups(user, DP_TECH_GROUPS, groups)


def is_optics_tech(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es técnico de S-OPTICS."""
    return user_in_groups(user, OPTICS_TECH_GROUPS, groups)


def is_sem_tech(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es técnico de SEM/FIB."""
    return user_in_groups(user, SEM_TECH_GROUPS, groups)

def is_imp_tech(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es técnico de Implantador."""
    return user_in_groups(user, IMP_TECH_GROUPS, groups)

def is_vdg_tech(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es tecnico de VDG."""
    return user_in_groups(user, VDG_TECH_GROUPS, groups)




def is_confocal_tech(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es técnico de Confocal."""
    return user_in_groups(user, CONF_TECH_GROUPS, groups)


def is_olmat_tech(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es técnico de OLMAT."""
    return user_in_groups(user, OLMAT_TECH_GROUPS, groups)


def is_dtf_user(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es usuario DTF."""
    return user_in_groups(user, DTF_USER_GROUPS, groups)


def user_can_access_dtf(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario puede acceder al portal DTF."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    group_names = groups or get_normalized_user_groups(user)
    return bool(group_names & ALL_DTF_GROUPS)


def user_can_access_icts(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario puede acceder al portal ICTS."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    group_names = groups or get_normalized_user_groups(user)
    if group_names & (ICTS_CORE_GROUPS | ICTS_TECH_GROUPS):
        return True
    return any(
        checker(user, group_names)
        for checker in (is_reviewer, is_responsable, is_manager)
    )


def is_any_tech(user, groups: Optional[Set[str]] = None) -> bool:
    """Verifica si el usuario es cualquier tipo de técnico."""
    return user_in_groups(user, ALL_TECH_GROUPS, groups)


# Nombres canónicos de grupos (para crear en migraciones)
CANONICAL_GROUP_NAMES = {
    # ICTS
    "icts_users",
    "revisores", 
    "responsables",
    "managers",
    
    # DTF
    "usuarios_dtf",
    "usuarios_autonomo_s_lab",
    "tecnico_responsable_s_lab",
    "tecnico_responsable_s_mec", 
    "tecnico_responsable_s_dp",
    "tecnico_responsable_s_optics",
    
    # Técnicos especializados
    "tecnicos_sem_fib",
    "vdg_technicians",
    "tecnico_vdg",
    "imp_technicians",
    "implant_technicians",
    "tecnico_imp",
    "confocal_technicians",
    "olmat_technicians",
}


__all__ = [
    # Constantes de grupos
    "ICTS_CORE_GROUPS",
    "RESPONSABLE_GROUPS", 
    "REVIEWER_GROUPS",
    "MANAGER_GROUPS",
    "SLAB_TECH_GROUPS",
    "MEC_TECH_GROUPS",
    "DP_TECH_GROUPS",
    "OPTICS_TECH_GROUPS",
    "SEM_TECH_GROUPS",
    "IMP_TECH_GROUPS",
    "VDG_TECH_GROUPS",
    "CONF_TECH_GROUPS",
    "OLMAT_TECH_GROUPS",
    "DTF_USER_GROUPS",
    "ICTS_TECH_GROUPS",
    "ALL_TECH_GROUPS",
    "ALL_DTF_GROUPS",
    "CANONICAL_GROUP_NAMES",
    
    # Funciones de utilidad
    "normalize_group_name",
    "get_normalized_user_groups",
    "user_in_groups",
    
    # Funciones de verificación
    "is_reviewer",
    "is_responsable", 
    "is_manager",
    "is_icts_user",
    "is_slab_tech",
    "is_mec_tech",
    "is_dp_tech",
    "is_optics_tech",
    "is_sem_tech",
    "is_imp_tech",
    "is_vdg_tech",
    "is_confocal_tech",
    "is_olmat_tech",
    "is_dtf_user",
    "user_can_access_dtf",
    "user_can_access_icts",
    "is_any_tech",
]
