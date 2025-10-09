from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    auth, reservas_opcion, usuarios, espacios, canchas, disciplinas, cupones,
    pagos, reportes, control_acceso, content
)
from app.database import engine, Base
from fastapi.staticfiles import StaticFiles

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Reservas Deportivas",
    description="API para gestión de reservas de espacios deportivos",
    version="1.0.0"
)

# Configuración CORS más específica
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Especifica los orígenes en lugar de "*"
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
app.include_router(content.router, prefix="/content", tags=["Contenido Dinámico"])

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return {"mensaje": "API de Reservas Deportivas funcionando correctamente"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}