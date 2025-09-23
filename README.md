# 🚀 Backend Taller TAW

Este proyecto está construido con **FastAPI** y **Uvicorn**.  
Sigue los pasos para instalarlo y ejecutarlo en tu máquina.

---

## 📌 Requisitos
- Python 3.10 o superior
- Git

---

## 🔹 Instalación

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/TallerTAW/backend.git
   cd backend

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   ```
3. **Activar entorno virtual**
   - En Windows:
     ```bash
     venv\Scripts\activate
     ```
   - En macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
4. **Instalar dependencias**
     ```bash
     pip install -r requirements.txt
     ```

5. **Ejecutar la aplicación**
   ```bash
   uvicorn main:app --reload
   ```
    La aplicación estará disponible en `http://127.0.0.1:8000`
    ```
---## 📚 Documentación de la API
    La documentación automática de la API está disponible en:
   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc: `http://127.0.0.1:8000/redoc`