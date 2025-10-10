from fastapi import FastAPI, status, Depends
from fastapi.middleware.cors import CORSMiddleware
# 🚨 Importación para el manejador de excepciones
from fastapi.responses import JSONResponse 

from app.routers import (
    auth, reservas_opcion, usuarios, espacios, canchas, disciplinas, cupones,
    pagos, reportes, control_acceso, cancelacion, cancha_disciplina, administra,
    # Router de contenido
    content 
)
from app.database import engine, Base

# 🚨 Importación del modelo de contenido (necesario para la creación de tablas)
import app.models.website_content 

# 🚨 Importación de la excepción personalizada
from app.core.exceptions import AuthException 

# Crear tablas. Esto debe ejecutarse después de que todos los modelos hayan sido importados.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Reservas Deportivas",
    description="API para gestión de reservas de espacios deportivos",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
# 🚨 CORRECCIÓN: Quitamos el 'prefix' redundante en auth.router
app.include_router(auth.router, prefix="/auth", tags=["Autenticación"]) # <-- CÓDIGO CORREGIDO: Añade el prefijo aquí

app.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios"])
app.include_router(espacios.router, prefix="/espacios", tags=["Espacios Deportivos"])
app.include_router(canchas.router, prefix="/canchas", tags=["Canchas"])
app.include_router(cupones.router, prefix="/cupones", tags=["Cupones"])
app.include_router(disciplinas.router, prefix="/disciplinas", tags=["Disciplinas"])
app.include_router(reservas_opcion.router, prefix="/reservas", tags=["Reservas"])
app.include_router(pagos.router, prefix="/pagos", tags=["Pagos"])
app.include_router(reportes.router, prefix="/reportes", tags=["Reportes"])
app.include_router(control_acceso.router, prefix="/control-acceso", tags=["Control de Acceso"])
app.include_router(cancelacion.router, prefix="/cancelaciones", tags=["Cancelaciones"])
app.include_router(administra.router, prefix="/administracion", tags=["Administración"])
app.include_router(cancha_disciplina.router, prefix="/canchas-disciplinas", tags=["Canchas y Disciplinas"])

# Router de contenido (ya corregido el prefix)
app.include_router(content.router, tags=["Contenido Dinámico"]) 


# -----------------------------------------------------------
# MANEJADOR DE EXCEPCIONES GLOBAL PARA AUTENTICACIÓN
# -----------------------------------------------------------

@app.exception_handler(AuthException)
def auth_exception_handler(request, exc: AuthException):
    """Maneja AuthException para asegurar que devuelva 401 Unauthorized."""
    # Retornar una respuesta JSON con el código 401 para que el frontend lo reconozca
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)},
    )


# -----------------------------------------------------------
# RUTAS BASE
# -----------------------------------------------------------

@app.get("/")
def read_root():
    return {"mensaje": "API de Reservas Deportivas funcionando correctamente"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}