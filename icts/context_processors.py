from .auth_utils import (
    CONF_TECH_GROUPS,
    ICTS_CORE_GROUPS,
    IMP_TECH_GROUPS,
    TECH_GROUPS,
    TECH_SEM_GROUPS,
    VDG_TECH_GROUPS,
    get_normalized_user_groups,
    is_manager,
    is_responsable,
    is_reviewer,
    user_in_groups,
)


def icts_ui(request):
    user = request.user
    role = ""
    if user.is_authenticated:
        groups = get_normalized_user_groups(user)
        if is_manager(user, groups):
            role = "Manager"
        elif is_responsable(user, groups):
            role = "Responsable"
        elif is_reviewer(user, groups):
            role = "Revisor"
        elif user_in_groups(user, CONF_TECH_GROUPS, groups):
            role = "Tecnico Confocal"
        elif user_in_groups(user, TECH_SEM_GROUPS, groups):
            role = "Tecnico SEM/FIB"
        elif user_in_groups(user, IMP_TECH_GROUPS, groups):
            role = "Tecnico IMP"
        elif user_in_groups(user, VDG_TECH_GROUPS, groups):
            role = "Tecnico VDG"
        elif groups & ICTS_CORE_GROUPS:
            role = "Usuario"
        elif user_in_groups(user, TECH_GROUPS, groups):
            role = "Tecnico"
        elif user.is_superuser:
            role = "Superusuario"
    return {"icts_role_name": role}
