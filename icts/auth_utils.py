"""Utility helpers for ICTS roles delegating on core.roles."""
from core import roles as core_roles

ICTS_CORE_GROUPS = core_roles.ICTS_CORE_GROUPS
RESPONSABLE_GROUPS = core_roles.RESPONSABLE_GROUPS
REVIEWER_GROUPS = core_roles.REVIEWER_GROUPS
MANAGER_GROUPS = core_roles.MANAGER_GROUPS
SLAB_TECH_GROUPS = core_roles.SLAB_TECH_GROUPS
MEC_TECH_GROUPS = core_roles.MEC_TECH_GROUPS
OPTICS_TECH_GROUPS = core_roles.OPTICS_TECH_GROUPS
TECH_SEM_GROUPS = core_roles.SEM_TECH_GROUPS
TECH_SIMS_GROUPS = core_roles.SIMS_TECH_GROUPS
IMP_TECH_GROUPS = core_roles.IMP_TECH_GROUPS
VDG_TECH_GROUPS = core_roles.VDG_TECH_GROUPS
CONF_TECH_GROUPS = core_roles.CONF_TECH_GROUPS
OLMAT_TECH_GROUPS = core_roles.OLMAT_TECH_GROUPS
DP_TECH_GROUPS = core_roles.DP_TECH_GROUPS
TECH_GROUPS = (
    core_roles.SEM_TECH_GROUPS
    | core_roles.SIMS_TECH_GROUPS
    | core_roles.IMP_TECH_GROUPS
    | core_roles.VDG_TECH_GROUPS
    | core_roles.CONF_TECH_GROUPS
    | core_roles.OLMAT_TECH_GROUPS
)

normalize_group_name = core_roles.normalize_group_name
get_normalized_user_groups = core_roles.get_normalized_user_groups
user_in_groups = core_roles.user_in_groups
is_reviewer = core_roles.is_reviewer
is_responsable = core_roles.is_responsable
is_manager = core_roles.is_manager
is_icts_user = core_roles.is_icts_user
user_can_access_dtf = core_roles.user_can_access_dtf
user_can_access_icts = core_roles.user_can_access_icts

__all__ = [
    "ICTS_CORE_GROUPS",
    "RESPONSABLE_GROUPS",
    "REVIEWER_GROUPS",
    "MANAGER_GROUPS",
    "SLAB_TECH_GROUPS",
    "MEC_TECH_GROUPS",
    "OPTICS_TECH_GROUPS",
    "TECH_SEM_GROUPS",
    "TECH_SIMS_GROUPS",
    "IMP_TECH_GROUPS",
    "VDG_TECH_GROUPS",
    "CONF_TECH_GROUPS",
    "OLMAT_TECH_GROUPS",
    "DP_TECH_GROUPS",
    "TECH_GROUPS",
    "normalize_group_name",
    "get_normalized_user_groups",
    "user_in_groups",
    "is_reviewer",
    "is_responsable",
    "is_manager",
    "is_icts_user",
    "user_can_access_dtf",
    "user_can_access_icts",
]
