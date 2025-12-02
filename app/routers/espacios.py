from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.espacio_deportivo import EspacioDeportivo
from app.schemas.espacio_deportivo import EspacioDeportivoResponse, EspacioDeportivoCreate, EspacioDeportivoUpdate
from app.models.usuario import Usuario
from app.models.administra import Administra
from app.core.security import get_current_user
import uuid
import os
import shutil
from typing import Optional
from sqlalchemy import text

# Configuración para uploads
UPLOAD_DIR = "static/uploads/espacios"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Asegurar que el directorio existe
os.makedirs(UPLOAD_DIR, exist_ok=True)

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file: UploadFile) -> str:
    """Guarda un archivo subido y retorna la ruta relativa"""
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")
    
    # Generar nombre único
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Guardar archivo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return f"/{UPLOAD_DIR}/{unique_filename}"

router = APIRouter()

@router.get("/", response_model=list[EspacioDeportivoResponse])
def get_espacios(
    include_inactive: bool = False, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener espacios deportivos según el rol del usuario
    - Admin: ve todos los espacios con información del gestor
    - Gestor/Control: ve solo los espacios que administra
    """
    
    if current_user.rol == "admin":
        # Admin ve todos los espacios con la información del gestor
        query = db.query(EspacioDeportivo, Usuario)\
            .outerjoin(Administra, EspacioDeportivo.id_espacio_deportivo == Administra.id_espacio_deportivo)\
            .outerjoin(Usuario, Administra.id_usuario == Usuario.id_usuario)
    elif current_user.rol in ["gestor", "control_acceso"]:
        # Gestor o control_acceso ve solo los espacios que administra
        query = db.query(EspacioDeportivo, Usuario)\
            .join(Administra, EspacioDeportivo.id_espacio_deportivo == Administra.id_espacio_deportivo)\
            .join(Usuario, Administra.id_usuario == Usuario.id_usuario)\
            .filter(Administra.id_usuario == current_user.id_usuario)
    else:
        # Cliente o otros roles no deberían acceder aquí, pero por si acaso
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a estos espacios"
        )
    
    if not include_inactive:
        query = query.filter(EspacioDeportivo.estado == "activo")
    
    results = query.all()
    
    # Procesamos los resultados
    lista_final = []
    for espacio, gestor in results:
        espacio_data = espacio.__dict__
        
        if gestor:
            espacio_data['gestor_id'] = gestor.id_usuario
            espacio_data['gestor_nombre'] = gestor.nombre
            espacio_data['gestor_apellido'] = gestor.apellido
        else:
            espacio_data['gestor_id'] = None
            espacio_data['gestor_nombre'] = None
            espacio_data['gestor_apellido'] = None
            
        lista_final.append(espacio_data)
    
    return lista_final

@router.get("/{espacio_id}", response_model=EspacioDeportivoResponse)
def get_espacio(espacio_id: int, db: Session = Depends(get_db)):
    # Buscamos espacio y usuario en la misma consulta
    resultado = db.query(EspacioDeportivo, Usuario)\
        .outerjoin(Administra, EspacioDeportivo.id_espacio_deportivo == Administra.id_espacio_deportivo)\
        .outerjoin(Usuario, Administra.id_usuario == Usuario.id_usuario)\
        .filter(EspacioDeportivo.id_espacio_deportivo == espacio_id)\
        .first()

    if not resultado:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    espacio, gestor = resultado
    espacio_dict = espacio.__dict__

    if gestor:
        espacio_dict['gestor_id'] = gestor.id_usuario
        espacio_dict['gestor_nombre'] = gestor.nombre
        espacio_dict['gestor_apellido'] = gestor.apellido
    else:
        espacio_dict['gestor_id'] = None
        espacio_dict['gestor_nombre'] = None
        espacio_dict['gestor_apellido'] = None

    return espacio_dict

@router.post("/", response_model=EspacioDeportivoResponse)
async def create_espacio(
    nombre: str = Form(...),
    ubicacion: str = Form(...),
    capacidad: int = Form(...),
    descripcion: Optional[str] = Form(None),
    gestor_id: Optional[int] = Form(None),
    latitud: float = Form(None),
    longitud: float = Form(None),
    imagen: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Crear espacio deportivo con imagen - SOLO ADMIN"""
    
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden crear espacios deportivos"
        )
    
    try:
        # Verificar si ya existe un espacio con ese nombre
        existing_espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.nombre == nombre).first()
        if existing_espacio:
            raise HTTPException(status_code=400, detail="Ya existe un espacio deportivo con ese nombre")
        
        # Procesar imagen si se proporciona
        imagen_path = None
        if imagen and imagen.size > 0:
            if imagen.size > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="La imagen es demasiado grande (máximo 5MB)")
            imagen_path = save_uploaded_file(imagen)
        
        # Crear el espacio
        nuevo_espacio = EspacioDeportivo(
            nombre=nombre,
            ubicacion=ubicacion,
            capacidad=capacidad,
            descripcion=descripcion,
            latitud=latitud,
            longitud=longitud,
            imagen=imagen_path
        )
        
        db.add(nuevo_espacio)
        db.commit()
        db.refresh(nuevo_espacio)
        
        # ASIGNAR GESTOR SI SE PROPORCIONÓ
        if gestor_id:
            gestor = db.query(Usuario).filter(
                Usuario.id_usuario == gestor_id,
                Usuario.rol == "gestor",
                Usuario.estado == "activo"
            ).first()
            
            if gestor:
                nueva_asignacion = Administra(
                    id_espacio_deportivo=nuevo_espacio.id_espacio_deportivo,
                    id_usuario=gestor_id
                )
                db.add(nueva_asignacion)
                db.commit()
        
        return nuevo_espacio
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.put("/{espacio_id}", response_model=EspacioDeportivoResponse)
async def update_espacio(
    espacio_id: int,
    nombre: Optional[str] = Form(None),
    ubicacion: Optional[str] = Form(None),
    capacidad: Optional[int] = Form(None),
    descripcion: Optional[str] = Form(None),
    latitud: Optional[float] = Form(None),
    longitud: Optional[float] = Form(None),
    gestor_id: Optional[int] = Form(None),
    imagen: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Actualizar espacio deportivo con imagen - SOLO ADMIN"""
    
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden actualizar espacios deportivos"
        )
    
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    # Verificar nombre único si se está cambiando
    if nombre and nombre != espacio.nombre:
        existing_espacio = db.query(EspacioDeportivo).filter(
            EspacioDeportivo.nombre == nombre,
            EspacioDeportivo.id_espacio_deportivo != espacio_id
        ).first()
        if existing_espacio:
            raise HTTPException(status_code=400, detail="Ya existe un espacio deportivo con ese nombre")
    
    # Actualizar campos
    if nombre is not None:
        espacio.nombre = nombre
    if ubicacion is not None:
        espacio.ubicacion = ubicacion
    if capacidad is not None:
        espacio.capacidad = capacidad
    if descripcion is not None:
        espacio.descripcion = descripcion
    if latitud is not None:
        espacio.latitud = latitud
    if longitud is not None:
        espacio.longitud = longitud
    
    # Procesar nueva imagen si se proporciona
    if imagen and imagen.size > 0:
        if imagen.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="La imagen es demasiado grande (máximo 5MB)")
        
        # Eliminar imagen anterior si existe
        if espacio.imagen:
            old_image_path = espacio.imagen.lstrip('/')
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
        
        # Guardar nueva imagen
        espacio.imagen = save_uploaded_file(imagen)

    if gestor_id is not None:
        # 1. Eliminar asignaciones previas para este espacio
        db.query(Administra).filter(
            Administra.id_espacio_deportivo == espacio_id
        ).delete()
        
        # 2. Crear la nueva si no es vacío
        if gestor_id > 0:
            nuevo_admin = Administra(
                id_usuario=gestor_id,
                id_espacio_deportivo=espacio_id
            )
            db.add(nuevo_admin)
    
    db.commit()
    db.refresh(espacio)
    return espacio

@router.delete("/{espacio_id}")
def desactivar_espacio(
    espacio_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Desactivar espacio deportivo (borrado lógico) - SOLO ADMIN"""
    
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden desactivar espacios deportivos"
        )
    
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    if espacio.estado == "inactivo":
        raise HTTPException(status_code=400, detail="El espacio deportivo ya está inactivo")
    
    espacio.estado = "inactivo"
    db.commit()
    
    return {"detail": "Espacio deportivo desactivado exitosamente"}

@router.put("/{espacio_id}/activar")
def activar_espacio(
    espacio_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Reactivar un espacio deportivo - SOLO ADMIN"""
    
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden activar espacios deportivos"
        )
    
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    if espacio.estado == "activo":
        raise HTTPException(status_code=400, detail="El espacio deportivo ya está activo")
    
    espacio.estado = "activo"
    db.commit()
    
    return {"detail": "Espacio deportivo activado exitosamente"}

@router.get("/nearby")
def get_espacios_cercanos(lat: float, lon: float, radius_km: float = 5.0, db: Session = Depends(get_db)):
    """
    Devuelve espacios dentro de radius_km kilómetros del punto (lat, lon).
    Retorna cada fila con un campo distance_km.
    """
    # Haversine implementado en SQL (Postgres)
    sql = text("""
      SELECT id_espacio_deportivo, nombre, ubicacion, capacidad, descripcion, imagen, latitud, longitud,
      (6371 * acos(
        cos(radians(:lat)) * cos(radians(latitud)) * cos(radians(longitud) - radians(:lon))
        + sin(radians(:lat)) * sin(radians(latitud))
      )) AS distance_km
      FROM espacio_deportivo
      WHERE latitud IS NOT NULL AND longitud IS NOT NULL
      HAVING (6371 * acos(
        cos(radians(:lat)) * cos(radians(latitud)) * cos(radians(longitud) - radians(:lon))
        + sin(radians(:lat)) * sin(radians(latitud))
      )) <= :radius
      ORDER BY distance_km ASC
      LIMIT 200;
    """)
    result = db.execute(sql, {"lat": lat, "lon": lon, "radius": radius_km})
    rows = [dict(r) for r in result]
    return rows

@router.get("/public/disponibles", response_model=list[EspacioDeportivoResponse])
def get_espacios_disponibles(db: Session = Depends(get_db)):
    """Obtener espacios deportivos disponibles (público para reservas)"""
    return db.query(EspacioDeportivo).filter(EspacioDeportivo.estado == "activo").all()

@router.get("/public/{espacio_id}", response_model=EspacioDeportivoResponse)
def get_espacio_public(espacio_id: int, db: Session = Depends(get_db)):
    """Obtener un espacio específico (público para reservas)"""
    espacio = db.query(EspacioDeportivo).filter(
        EspacioDeportivo.id_espacio_deportivo == espacio_id,
        EspacioDeportivo.estado == "activo"
    ).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    return espacio

@router.get("/gestores/disponibles")
def get_gestores_disponibles(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener lista de gestores disponibles para asignar espacios - SOLO ADMIN"""
    
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver los gestores"
        )
    
    # Obtener todos los usuarios con rol "gestor" y estado "activo"
    gestores = db.query(Usuario).filter(
        Usuario.rol == "gestor",
        Usuario.estado == "activo"
    ).all()
    
    return [
        {
            "id_usuario": gestor.id_usuario,
            "nombre": gestor.nombre,
            "apellido": gestor.apellido,
            "email": gestor.email,
            "telefono": gestor.telefono
        }
        for gestor in gestores
    ]

@router.post("/{espacio_id}/asignar-gestor/{gestor_id}")
def asignar_gestor_espacio(
    espacio_id: int,
    gestor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Asignar un gestor a un espacio deportivo - SOLO ADMIN"""
    
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden asignar gestores"
        )
    
    # Verificar que el espacio existe
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    # Verificar que el usuario es un gestor
    gestor = db.query(Usuario).filter(
        Usuario.id_usuario == gestor_id,
        Usuario.rol == "gestor",
        Usuario.estado == "activo"
    ).first()
    
    if not gestor:
        raise HTTPException(status_code=404, detail="Gestor no encontrado o no está activo")
    
    # Verificar si ya existe la asignación
    existing_asignacion = db.query(Administra).filter(
        Administra.id_espacio_deportivo == espacio_id,
        Administra.id_usuario == gestor_id
    ).first()
    
    if existing_asignacion:
        raise HTTPException(
            status_code=400,
            detail="Este gestor ya está asignado a este espacio"
        )
    
    # Crear la asignación
    nueva_asignacion = Administra(
        id_espacio_deportivo=espacio_id,
        id_usuario=gestor_id
    )
    
    db.add(nueva_asignacion)
    db.commit()
    
    return {
        "detail": f"Gestor {gestor.nombre} {gestor.apellido} asignado exitosamente al espacio {espacio.nombre}",
        "asignacion": {
            "id_espacio": espacio_id,
            "id_gestor": gestor_id,
            "nombre_espacio": espacio.nombre,
            "nombre_gestor": f"{gestor.nombre} {gestor.apellido}"
        }
    }

@router.get("/{espacio_id}/gestor-asignado")
def get_gestor_asignado(
    espacio_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener el gestor asignado a un espacio deportivo - SOLO ADMIN"""
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver esta información"
        )
    
    # Buscar la asignación en la tabla administra
    asignacion = db.query(Administra).filter(
        Administra.id_espacio_deportivo == espacio_id
    ).first()
    
    if not asignacion:
        return {"gestor_asignado": None}
    
    # Obtener información del gestor
    gestor = db.query(Usuario).filter(Usuario.id_usuario == asignacion.id_usuario).first()
    
    if gestor:
        return {
            "gestor_asignado": {
                "id_usuario": gestor.id_usuario,
                "nombre": gestor.nombre,
                "apellido": gestor.apellido,
                "email": gestor.email
            }
        }
    else:
        return {"gestor_asignado": None}