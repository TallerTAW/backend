from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Importaciones de routers (Se incluyen todos los routers de tu proyecto más grande)
from app.routers import (
    auth, reservas_opcion, usuarios, espacios, canchas, disciplinas, cupones,
    pagos, reportes, control_acceso, content, incidentes, comentarios,
    cancelacion, cancha_disciplina, administra
)

# Importaciones de la base de datos y excepciones
from app.database import engine, Base
from app.core.exceptions import AuthException 

# Importación de modelos para asegurar que SQLAlchemy los conozca antes de crear tablas
# Esto es CRUCIAL para que Base.metadata.create_all funcione correctamente
# Agregué 'website_content' que vi en tu primer ejemplo
import app.models.website_content 


# Crear tablas (Se ejecuta una sola vez al cargar la app)
# Este es el punto más probable de fallo de importación. Si falla, es porque una 
# de las importaciones anteriores (como app.database o app.models.*) falló.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Reservas Deportivas",
    description="API para gestión de reservas de espacios deportivos",
    version="1.0.0"
)

# Configuración CORS específica (Mejor que "*")
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token",
    ],
    expose_headers=["*"],
    max_age=600,
)

# -----------------------------------------------------------
# MANEJADOR DE EXCEPCIONES GLOBAL PARA AUTENTICACIÓN
# -----------------------------------------------------------

@app.exception_handler(AuthException)
def auth_exception_handler(request, exc: AuthException):
    """Maneja AuthException para asegurar que devuelva 401 Unauthorized."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)},
    )


# -----------------------------------------------------------
# REGISTRO DE ROUTERS
# -----------------------------------------------------------

app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
app.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios"])
app.include_router(espacios.router, prefix="/espacios", tags=["Espacios Deportivos"])
app.include_router(canchas.router, prefix="/canchas", tags=["Canchas"])
app.include_router(cupones.router, prefix="/cupones", tags=["Cupones"])
app.include_router(disciplinas.router, prefix="/disciplinas", tags=["Disciplinas"])
app.include_router(reservas_opcion.router, prefix="/reservas", tags=["Reservas"])
app.include_router(pagos.router, prefix="/pagos", tags=["Pagos"])
app.include_router(reportes.router, prefix="/reportes", tags=["Reportes"])
app.include_router(control_acceso.router, prefix="/control-acceso", tags=["Control de Acceso"])
app.include_router(content.router, prefix="/content", tags=["Contenido Dinámico"])
app.include_router(incidentes.router, prefix="/incidentes", tags=["Incidentes"])
app.include_router(comentarios.router, prefix="/comentarios", tags=["Comentarios"])

# Routers adicionales de tu proyecto más completo
app.include_router(cancelacion.router, prefix="/cancelaciones", tags=["Cancelaciones"])
app.include_router(administra.router, prefix="/administracion", tags=["Administración"])
app.include_router(cancha_disciplina.router, prefix="/canchas-disciplinas", tags=["Canchas y Disciplinas"])


# -----------------------------------------------------------
# ARCHIVOS ESTÁTICOS
# -----------------------------------------------------------

app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------------------------------------------
# RUTAS BASE
# -----------------------------------------------------------

@app.get("/")
def read_root():
    return {"mensaje": "API de Reservas Deportivas funcionando correctamente"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
