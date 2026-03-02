# Festum API

API REST construida con **FastAPI** y **Firestore (Firebase)**, diseñada para ser **modular, escalable y mantenible**.  
Pensada para ser consumida por una app móvil Flutter.

## Stack
- FastAPI
- Firebase Admin SDK (Firestore)
- Pydantic v2 (validaciones)
- Uvicorn

## Arquitectura
```text
app/
  api/
    dependencies/      # Dependencias compartidas (auth, etc.)
    v1/
      endpoints/        # Controladores HTTP
      router.py
  core/                 # Config, seguridad JWT, excepciones, Firebase client
  repositories/         # Acceso a datos
  schemas/              # Request/Response models + validaciones
  services/             # Reglas de negocio
  main.py
```

## Requisitos
- Python 3.11+
- Proyecto Firebase ya configurado
- Archivo de credenciales de servicio para desarrollo local

## Configuración
1. Crear entorno virtual e instalar dependencias:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Crear archivo `.env`:
```bash
cp .env.example .env
```

3. Ajustar variables en `.env`:
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_CREDENTIALS_PATH`
- `FIREBASE_DATABASE_URL`
- `ALLOWED_ORIGINS`

## Ejecutar local
```bash
uvicorn app.main:app --reload
```

Documentación:
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints disponibles (v1)
- `GET /api/v1/health`
- `GET /api/v1/health/firebase`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`

## Autenticación JWT
- `register`: registra usuario con `first_name`, `last_name`, `email`, `password`, `confirm_password`
- `login`: inicio de sesión con `email` y `password`
- respuesta de auth incluye:
  - `access_token`
  - `token_type` (`bearer`)
  - `expires_in`
  - `user`
- endpoints de `users` requieren header:
  - `Authorization: Bearer <token>`

## Validaciones implementadas
- `first_name` y `last_name`: solo letras, normalización de espacios y capitalización
- `email`: formato válido y normalización a minúsculas
- `password`: mínimo 8 caracteres
- `confirm_password`: debe coincidir con `password`
- `phone`: formato internacional E.164 (opcional)
- `birth_date`: fecha válida (opcional)
- actualización parcial: al menos un campo requerido
- unicidad de email en registro

## Ejemplos de payload para Flutter
Registro:
```json
{
  "first_name": "Alan",
  "last_name": "Hernandez",
  "email": "alan@email.com",
  "password": "MyStrongPass123",
  "confirm_password": "MyStrongPass123"
}
```

Login:
```json
{
  "email": "alan@email.com",
  "password": "MyStrongPass123"
}
```

## Buenas prácticas aplicadas
- Separación por capas (`endpoint -> service -> repository`)
- Configuración por entorno con `.env`
- Manejo centralizado de errores de dominio
- Respuestas tipadas con Pydantic
- CORS configurable para Flutter y otros clientes

## Despliegue (resumen)
- Mantener `.env` fuera del repositorio
- En nube, ajustar valores de entorno sin modificar código
- Cambiar `FIREBASE_DATABASE_URL` y credenciales por las del entorno destino
- Para producción se recomienda credenciales gestionadas por proveedor cloud (IAM/Secrets)

## Próximos pasos recomendados
1. Incorporar refresh tokens y revocación de sesiones.
2. Agregar tests automatizados (unit + integración).
3. Agregar módulos nuevos por dominio (`events`, `bookings`, `payments`) siguiendo el mismo patrón por capas.
4. Añadir observabilidad (logging estructurado y métricas).
