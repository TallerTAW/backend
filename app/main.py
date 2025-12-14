# En main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.config import settings
from app.routers import (
    auth, 
    notifications, 
    reservas_opcion, 
    usuarios, 
    espacios, 
    canchas, 
    disciplinas, 
    cupones, 
    pagos, 
    reportes, 
    control_acceso, 
    content, 
    incidentes, 
    comentarios,
    libelula # <--- ¡Nuevo Router Importado!
)


app = FastAPI(
    title="Sistema de Reservas Deportivas - OlympiaHub",
    description="API para gestión de reservas de espacios deportivos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", 
"OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token",
        "Access-Control-Allow-Origin",
    ],
    expose_headers=["*"],
    max_age=600,
)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
app.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios"])
app.include_router(espacios.router, prefix="/espacios", tags=["Espacios Deportivos"])
app.include_router(canchas.router, prefix="/canchas", tags=["Canchas"])
app.include_router(cupones.router, prefix="/cupones", tags=["Cupones"])
app.include_router(disciplinas.router, prefix="/disciplinas", tags=["Disciplinas"])
app.include_router(reservas_opcion.router, prefix="/reservas", tags=["Reservas Completas"])
app.include_router(pagos.router, prefix="/pagos", tags=["Pagos"])

# INCLUSIÓN DEL NUEVO ROUTER DE LIBÉLULA (usa el prefix y tags definidos en libelula.py)
app.include_router(libelula.router) 

app.include_router(reportes.router, prefix="/reportes", tags=["Reportes"])
app.include_router(control_acceso.router, prefix="/control-acceso", tags=["Control de Acceso"])
app.include_router(content.router, prefix="/content", tags=["Contenido Dinámico"])
app.include_router(incidentes.router, prefix="/incidentes", tags=["Incidentes"])
app.include_router(comentarios.router, prefix="/comentarios", tags=["Comentarios"])
app.include_router(notifications.router, prefix="/notificaciones", tags=["Notificaciones"])

@app.get("/")
def read_root():
    return {
        "mensaje": "OlympiaHub API funcionando correctamente",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "OlympiaHub API",
    }