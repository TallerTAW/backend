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
from typing import Optional, List
from sqlalchemy import text, or_
from datetime import datetime

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
    
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
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
    - Admin: ve todos los espacios con información del gestor y control de acceso
    - Gestor/Control: ve solo los espacios que administra
    """
    
    if current_user.rol == "admin":
        # Admin ve todos los espacios
        espacios = db.query(EspacioDeportivo).all()
    elif current_user.rol in ["gestor", "control_acceso"]:
        # Gestor o control_acceso ve solo los espacios donde está asignado
        espacios = db.query(EspacioDeportivo)\
            .join(Administra, EspacioDeportivo.id_espacio_deportivo == Administra.id_espacio_deportivo)\
            .filter(Administra.id_usuario == current_user.id_usuario)\
            .all()
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a estos espacios"
        )
    
    if not include_inactive:
        espacios = [e for e in espacios if e.estado == "activo"]
    
    # Enriquecer cada espacio con información de asignaciones
    espacios_enriquecidos = []
    for espacio in espacios:
        # Obtener todos los usuarios asignados a este espacio
        usuarios_asignados = db.query(Usuario)\
            .join(Administra, Usuario.id_usuario == Administra.id_usuario)\
            .filter(Administra.id_espacio_deportivo == espacio.id_espacio_deportivo)\
            .all()
        
        # Separar por rol
        gestor_info = None
        control_info = None
        
        for usuario in usuarios_asignados:
            if usuario.rol == "gestor":
                gestor_info = usuario
            elif usuario.rol == "control_acceso":
                control_info = usuario
        
        espacio_dict = {
            "id_espacio_deportivo": espacio.id_espacio_deportivo,
            "nombre": espacio.nombre,
            "ubicacion": espacio.ubicacion,
            "capacidad": espacio.capacidad,
            "descripcion": espacio.descripcion,
            "imagen": espacio.imagen,
            "estado": espacio.estado,
            "latitud": espacio.latitud,
            "longitud": espacio.longitud,
            "fecha_creacion": espacio.fecha_creacion,
            "gestor_id": gestor_info.id_usuario if gestor_info else None,
            "gestor_nombre": gestor_info.nombre if gestor_info else None,
            "gestor_apellido": gestor_info.apellido if gestor_info else None,
            "control_acceso_id": control_info.id_usuario if control_info else None,
            "control_acceso_nombre": control_info.nombre if control_info else None,
            "control_acceso_apellido": control_info.apellido if control_info else None,
        }
        
        espacios_enriquecidos.append(espacio_dict)
    
    return espacios_enriquecidos

@router.get("/{espacio_id}", response_model=EspacioDeportivoResponse)
def get_espacio(
    espacio_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener un espacio específico con información de asignaciones"""
    
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    # Verificar permisos si no es admin
    if current_user.rol not in ["admin"] and current_user.rol in ["gestor", "control_acceso"]:
        # Verificar si el usuario está asignado a este espacio
        asignacion = db.query(Administra).filter(
            Administra.id_espacio_deportivo == espacio_id,
            Administra.id_usuario == current_user.id_usuario
        ).first()
        
        if not asignacion:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para acceder a este espacio"
            )
    
    # Obtener todos los usuarios asignados a este espacio
    usuarios_asignados = db.query(Usuario)\
        .join(Administra, Usuario.id_usuario == Administra.id_usuario)\
        .filter(Administra.id_espacio_deportivo == espacio_id)\
        .all()
    
    # Separar por rol
    gestor_info = None
    control_info = None
    
    for usuario in usuarios_asignados:
        if usuario.rol == "gestor":
            gestor_info = usuario
        elif usuario.rol == "control_acceso":
            control_info = usuario
    
    respuesta = {
        "id_espacio_deportivo": espacio.id_espacio_deportivo,
        "nombre": espacio.nombre,
        "ubicacion": espacio.ubicacion,
        "capacidad": espacio.capacidad,
        "descripcion": espacio.descripcion,
        "imagen": espacio.imagen,
        "estado": espacio.estado,
        "latitud": espacio.latitud,
        "longitud": espacio.longitud,
        "fecha_creacion": espacio.fecha_creacion,
        "gestor_id": gestor_info.id_usuario if gestor_info else None,
        "gestor_nombre": gestor_info.nombre if gestor_info else None,
        "gestor_apellido": gestor_info.apellido if gestor_info else None,
        "control_acceso_id": control_info.id_usuario if control_info else None,
        "control_acceso_nombre": control_info.nombre if control_info else None,
        "control_acceso_apellido": control_info.apellido if control_info else None,
    }
    
    return respuesta

@router.post("/", response_model=EspacioDeportivoResponse)
async def create_espacio(
    nombre: str = Form(...),
    ubicacion: str = Form(...),
    capacidad: int = Form(...),
    descripcion: Optional[str] = Form(None),
    gestor_id: Optional[int] = Form(None),
    control_acceso_id: Optional[int] = Form(None),
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
        if gestor_id and gestor_id > 0:
            gestor = db.query(Usuario).filter(
                Usuario.id_usuario == gestor_id,
                Usuario.rol == "gestor",
                Usuario.estado == "activo"
            ).first()
            
            if gestor:
                # Verificar que no haya ya un gestor asignado
                gestor_existente = db.query(Administra)\
                    .join(Usuario, Administra.id_usuario == Usuario.id_usuario)\
                    .filter(
                        Administra.id_espacio_deportivo == nuevo_espacio.id_espacio_deportivo,
                        Usuario.rol == "gestor"
                    ).first()
                
                if gestor_existente:
                    # Actualizar la asignación existente
                    gestor_existente.id_usuario = gestor_id
                else:
                    # Crear nueva asignación
                    nueva_asignacion = Administra(
                        id_espacio_deportivo=nuevo_espacio.id_espacio_deportivo,
                        id_usuario=gestor_id,
                        fecha_asignacion=datetime.now()
                    )
                    db.add(nueva_asignacion)
        
        # ASIGNAR CONTROL DE ACCESO SI SE PROPORCIONÓ
        if control_acceso_id and control_acceso_id > 0:
            control = db.query(Usuario).filter(
                Usuario.id_usuario == control_acceso_id,
                Usuario.rol == "control_acceso",
                Usuario.estado == "activo"
            ).first()
            
            if control:
                # Verificar que no haya ya un control asignado
                control_existente = db.query(Administra)\
                    .join(Usuario, Administra.id_usuario == Usuario.id_usuario)\
                    .filter(
                        Administra.id_espacio_deportivo == nuevo_espacio.id_espacio_deportivo,
                        Usuario.rol == "control_acceso"
                    ).first()
                
                if control_existente:
                    # Actualizar la asignación existente
                    control_existente.id_usuario = control_acceso_id
                else:
                    # Crear nueva asignación
                    nueva_asignacion = Administra(
                        id_espacio_deportivo=nuevo_espacio.id_espacio_deportivo,
                        id_usuario=control_acceso_id,
                        fecha_asignacion=datetime.now()
                    )
                    db.add(nueva_asignacion)
        
        db.commit()
        
        # Retornar el espacio creado con información de asignaciones
        return get_espacio(nuevo_espacio.id_espacio_deportivo, db, current_user)
        
    except HTTPException:
        db.rollback()
        raise
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
    control_acceso_id: Optional[int] = Form(None),
    imagen: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Actualizar espacio deportivo - SOLO ADMIN"""
    
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden actualizar espacios deportivos"
        )
    
    try:
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
        
        # Actualizar campos básicos
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
            if espacio.imagen and espacio.imagen.startswith(f"/{UPLOAD_DIR}/"):
                old_image_path = espacio.imagen.lstrip('/')
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            # Guardar nueva imagen
            espacio.imagen = save_uploaded_file(imagen)
        
        # GESTIÓN DE ASIGNACIONES DE GESTOR
        if gestor_id is not None:
            # Buscar gestor actual asignado
            gestor_actual = db.query(Administra)\
                .join(Usuario, Administra.id_usuario == Usuario.id_usuario)\
                .filter(
                    Administra.id_espacio_deportivo == espacio_id,
                    Usuario.rol == "gestor"
                ).first()
            
            if gestor_id and gestor_id > 0:
                # Verificar que el usuario existe y es gestor
                gestor = db.query(Usuario).filter(
                    Usuario.id_usuario == gestor_id,
                    Usuario.rol == "gestor",
                    Usuario.estado == "activo"
                ).first()
                
                if not gestor:
                    raise HTTPException(status_code=400, detail="El gestor especificado no existe o no está activo")
                
                if gestor_actual:
                    # Actualizar asignación existente
                    gestor_actual.id_usuario = gestor_id
                    gestor_actual.fecha_asignacion = datetime.now()
                else:
                    # Crear nueva asignación
                    nueva_asignacion = Administra(
                        id_espacio_deportivo=espacio_id,
                        id_usuario=gestor_id,
                        fecha_asignacion=datetime.now()
                    )
                    db.add(nueva_asignacion)
            else:
                # Eliminar asignación si se envía vacío
                if gestor_actual:
                    db.delete(gestor_actual)
        
        # GESTIÓN DE ASIGNACIONES DE CONTROL DE ACCESO
        if control_acceso_id is not None:
            # Buscar control actual asignado
            control_actual = db.query(Administra)\
                .join(Usuario, Administra.id_usuario == Usuario.id_usuario)\
                .filter(
                    Administra.id_espacio_deportivo == espacio_id,
                    Usuario.rol == "control_acceso"
                ).first()
            
            if control_acceso_id and control_acceso_id > 0:
                # Verificar que el usuario existe y es control de acceso
                control = db.query(Usuario).filter(
                    Usuario.id_usuario == control_acceso_id,
                    Usuario.rol == "control_acceso",
                    Usuario.estado == "activo"
                ).first()
                
                if not control:
                    raise HTTPException(status_code=400, detail="El control de acceso especificado no existe o no está activo")
                
                if control_actual:
                    # Actualizar asignación existente
                    control_actual.id_usuario = control_acceso_id
                    control_actual.fecha_asignacion = datetime.now()
                else:
                    # Crear nueva asignación
                    nueva_asignacion = Administra(
                        id_espacio_deportivo=espacio_id,
                        id_usuario=control_acceso_id,
                        fecha_asignacion=datetime.now()
                    )
                    db.add(nueva_asignacion)
            else:
                # Eliminar asignación si se envía vacío
                if control_actual:
                    db.delete(control_actual)
        
        db.commit()
        db.refresh(espacio)
        
        # Retornar el espacio actualizado con información de asignaciones
        return get_espacio(espacio_id, db, current_user)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

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
def get_espacios_cercanos(
    lat: float, 
    lon: float, 
    radius_km: float = 5.0, 
    db: Session = Depends(get_db)
):
    """
    Devuelve espacios dentro de radius_km kilómetros del punto (lat, lon).
    """
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
    espacios = db.query(EspacioDeportivo).filter(EspacioDeportivo.estado == "activo").all()
    
    return [
        {
            "id_espacio_deportivo": espacio.id_espacio_deportivo,
            "nombre": espacio.nombre,
            "ubicacion": espacio.ubicacion,
            "capacidad": espacio.capacidad,
            "descripcion": espacio.descripcion,
            "imagen": espacio.imagen,
            "estado": espacio.estado,
            "latitud": espacio.latitud,
            "longitud": espacio.longitud,
            "fecha_creacion": espacio.fecha_creacion,
            "gestor_id": None,
            "gestor_nombre": None,
            "gestor_apellido": None,
            "control_acceso_id": None,
            "control_acceso_nombre": None,
            "control_acceso_apellido": None,
        }
        for espacio in espacios
    ]

@router.get("/public/{espacio_id}", response_model=EspacioDeportivoResponse)
def get_espacio_public(espacio_id: int, db: Session = Depends(get_db)):
    """Obtener un espacio específico (público para reservas)"""
    espacio = db.query(EspacioDeportivo).filter(
        EspacioDeportivo.id_espacio_deportivo == espacio_id,
        EspacioDeportivo.estado == "activo"
    ).first()
    
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    return {
        "id_espacio_deportivo": espacio.id_espacio_deportivo,
        "nombre": espacio.nombre,
        "ubicacion": espacio.ubicacion,
        "capacidad": espacio.capacidad,
        "descripcion": espacio.descripcion,
        "imagen": espacio.imagen,
        "estado": espacio.estado,
        "latitud": espacio.latitud,
        "longitud": espacio.longitud,
        "fecha_creacion": espacio.fecha_creacion,
        "gestor_id": None,
        "gestor_nombre": None,
        "gestor_apellido": None,
        "control_acceso_id": None,
        "control_acceso_nombre": None,
        "control_acceso_apellido": None,
    }

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

@router.get("/controles-acceso/disponibles")
def get_controles_acceso_disponibles(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener lista de controles de acceso disponibles para asignar espacios - SOLO ADMIN"""
    
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver los controles de acceso"
        )
    
    controles = db.query(Usuario).filter(
        Usuario.rol == "control_acceso",
        Usuario.estado == "activo"
    ).all()
    
    return [
        {
            "id_usuario": control.id_usuario,
            "nombre": control.nombre,
            "apellido": control.apellido,
            "email": control.email,
            "telefono": control.telefono
        }
        for control in controles
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
    
    # Buscar si ya hay un gestor asignado
    gestor_actual = db.query(Administra)\
        .join(Usuario, Administra.id_usuario == Usuario.id_usuario)\
        .filter(
            Administra.id_espacio_deportivo == espacio_id,
            Usuario.rol == "gestor"
        ).first()
    
    if gestor_actual:
        # Actualizar asignación existente
        gestor_actual.id_usuario = gestor_id
        gestor_actual.fecha_asignacion = datetime.now()
    else:
        # Crear nueva asignación
        nueva_asignacion = Administra(
            id_espacio_deportivo=espacio_id,
            id_usuario=gestor_id,
            fecha_asignacion=datetime.now()
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

@router.post("/{espacio_id}/asignar-control-acceso/{control_id}")
def asignar_control_acceso_espacio(
    espacio_id: int,
    control_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Asignar un control de acceso a un espacio deportivo - SOLO ADMIN"""
    
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden asignar controles de acceso"
        )
    
    # Verificar que el espacio existe
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    # Verificar que el usuario es un control de acceso
    control = db.query(Usuario).filter(
        Usuario.id_usuario == control_id,
        Usuario.rol == "control_acceso",
        Usuario.estado == "activo"
    ).first()
    
    if not control:
        raise HTTPException(status_code=404, detail="Control de acceso no encontrado o no está activo")
    
    # Buscar si ya hay un control de acceso asignado
    control_actual = db.query(Administra)\
        .join(Usuario, Administra.id_usuario == Usuario.id_usuario)\
        .filter(
            Administra.id_espacio_deportivo == espacio_id,
            Usuario.rol == "control_acceso"
        ).first()
    
    if control_actual:
        # Actualizar asignación existente
        control_actual.id_usuario = control_id
        control_actual.fecha_asignacion = datetime.now()
    else:
        # Crear nueva asignación
        nueva_asignacion = Administra(
            id_espacio_deportivo=espacio_id,
            id_usuario=control_id,
            fecha_asignacion=datetime.now()
        )
        db.add(nueva_asignacion)
    
    db.commit()
    
    return {
        "detail": f"Control de acceso {control.nombre} {control.apellido} asignado exitosamente al espacio {espacio.nombre}",
        "asignacion": {
            "id_espacio": espacio_id,
            "id_control": control_id,
            "nombre_espacio": espacio.nombre,
            "nombre_control": f"{control.nombre} {control.apellido}"
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
    
    # Buscar el gestor asignado
    gestor_asignacion = db.query(Administra)\
        .join(Usuario, Administra.id_usuario == Usuario.id_usuario)\
        .filter(
            Administra.id_espacio_deportivo == espacio_id,
            Usuario.rol == "gestor"
        ).first()
    
    if not gestor_asignacion:
        return {"gestor_asignado": None}
    
    # Obtener información del gestor
    gestor = db.query(Usuario).filter(Usuario.id_usuario == gestor_asignacion.id_usuario).first()
    
    if gestor:
        return {
            "gestor_asignado": {
                "id_usuario": gestor.id_usuario,
                "nombre": gestor.nombre,
                "apellido": gestor.apellido,
                "email": gestor.email,
                "fecha_asignacion": gestor_asignacion.fecha_asignacion
            }
        }
    else:
        return {"gestor_asignado": None}

@router.get("/{espacio_id}/control-acceso-asignado")
def get_control_acceso_asignado(
    espacio_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener el control de acceso asignado a un espacio deportivo - SOLO ADMIN"""
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver esta información"
        )
    
    # Buscar el control de acceso asignado
    control_asignacion = db.query(Administra)\
        .join(Usuario, Administra.id_usuario == Usuario.id_usuario)\
        .filter(
            Administra.id_espacio_deportivo == espacio_id,
            Usuario.rol == "control_acceso"
        ).first()
    
    if not control_asignacion:
        return {"control_acceso_asignado": None}
    
    # Obtener información del control de acceso
    control = db.query(Usuario).filter(Usuario.id_usuario == control_asignacion.id_usuario).first()
    
    if control:
        return {
            "control_acceso_asignado": {
                "id_usuario": control.id_usuario,
                "nombre": control.nombre,
                "apellido": control.apellido,
                "email": control.email,
                "fecha_asignacion": control_asignacion.fecha_asignacion
            }
        }
    else:
        return {"control_acceso_asignado": None}