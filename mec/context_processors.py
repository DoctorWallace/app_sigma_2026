# mec/context_processors.py
from icts.auth_utils import MEC_TECH_GROUPS, get_normalized_user_groups, user_in_groups

def mec_role(request):
    """
    Devuelve MEC_ROLE = "TECNICO" | "USUARIO" | None
    para pintar el badge en la barra superior.
    """
    role = None
    if request.user.is_authenticated:
        if request.user.is_superuser:
            role = "TECNICO"
        else:
            groups = get_normalized_user_groups(request.user)
            if user_in_groups(request.user, MEC_TECH_GROUPS, groups):
                role = "TECNICO"
            else:
                role = "USUARIO"
    return {"MEC_ROLE": role}

