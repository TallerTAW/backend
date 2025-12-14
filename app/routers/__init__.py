from .auth import router as auth_router
from .usuarios import router as usuarios_router
from .espacios import router as espacios_router
from .canchas import router as canchas_router
from .cupones import router as cupones_router
from .disciplinas import router as disciplinas_router
from .pagos import router as pagos_router
from .reportes import router as reportes_router
from .control_acceso import router as control_acceso_router
from .reservas_opcion import router as reservas_router

__all__ = [
    "auth_router", "usuarios_router", "espacios_router", "canchas_router", "cupones_router",
    "disciplinas_router", "reservas_router", "pagos_router", "reportes_router",
    "control_acceso_router"
]