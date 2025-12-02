from typing import Any, List

def allowed_roles(current_user: Any, required_roles: List[str]) -> bool:
    """
    Verifica si el rol del usuario actual está entre los roles permitidos.
    
    current_user debe ser el objeto retornado por get_current_user,
    y asumimos que tiene un atributo 'rol'.
    """
    # Convertimos el rol del usuario a minúsculas
    user_role = current_user.rol.lower() 
    
    # Verificamos si el rol del usuario está en la lista de roles requeridos
    return user_role in [r.lower() for r in required_roles]