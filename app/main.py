from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    auth, reservas_opcion, usuarios, espacios, canchas, disciplinas, cupones,
    pagos, reportes, control_acceso, cancelacion, cancha_disciplina, administra,
    # 🚨 Importación del router de contenido
    content 
)
from app.database import engine, Base

# 🚨 CORRECCIÓN 2: Importar explícitamente el modelo de contenido
# Esto asegura que SQLAlchemy "vea" el modelo y cree la tabla.
import app.models.website_content 

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
app.include_router(cancelacion.router, prefix="/cancelaciones", tags=["Cancelaciones"])
app.include_router(administra.router, prefix="/administracion", tags=["Administración"])
app.include_router(cancha_disciplina.router, prefix="/canchas-disciplinas", tags=["Canchas y Disciplinas"])

# 🚨 CORRECCIÓN 1: Incluir el router de contenido SIN el prefijo redundante.
# El prefijo "/content" ya está definido dentro de app/routers/content.py
app.include_router(content.router, tags=["Contenido Dinámico"]) 


@app.get("/")
def read_root():
    return {"mensaje": "API de Reservas Deportivas funcionando correctamente"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}