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
- `GET /api/v1/providers/me/home`
- `GET /api/v1/providers/me/notifications`
- `PATCH /api/v1/providers/me/notifications/read-all`
- `PATCH /api/v1/providers/me/notifications/{notification_id}/read`
- `DELETE /api/v1/providers/me/notifications`
- `POST /api/v1/providers/me/services`
- `POST /api/v1/providers/me/services/drafts`
- `GET /api/v1/providers/me/services`
- `GET /api/v1/providers/me/services/{service_id}`
- `PATCH /api/v1/providers/me/services/{service_id}`
- `POST /api/v1/providers/me/services/{service_id}/images`
- `PATCH /api/v1/providers/me/services/{service_id}/images/main`
- `PATCH /api/v1/providers/me/services/{service_id}/images/reorder`
- `DELETE /api/v1/providers/me/services/{service_id}/images`
- `DELETE /api/v1/providers/me/services/{service_id}`
- `POST /api/v1/providers/me/services/{service_id}/products`
- `GET /api/v1/providers/me/services/{service_id}/products`
- `GET /api/v1/providers/me/services/by-name/{service_name}/products`
- `GET /api/v1/providers/me/services/{service_id}/products/{product_id}`
- `PATCH /api/v1/providers/me/services/{service_id}/products/{product_id}`
- `DELETE /api/v1/providers/me/services/{service_id}/products/{product_id}`
- `GET /api/v1/providers/me/products/reservations`
- `DELETE /api/v1/providers/me/products/{product_id}`
- `POST /api/v1/providers/me/services/{service_id}/products/{product_id}/images`
- `PATCH /api/v1/providers/me/services/{service_id}/products/{product_id}/images/main`
- `PATCH /api/v1/providers/me/services/{service_id}/products/{product_id}/images/reorder`
- `DELETE /api/v1/providers/me/services/{service_id}/products/{product_id}/images`
- `GET /api/v1/providers/me/products/{product_id}/availability`
- `PATCH /api/v1/providers/me/products/{product_id}/availability/{target_date}/block`
- `PATCH /api/v1/providers/me/products/{product_id}/availability/{target_date}/unblock`
- `POST /api/v1/providers/me/products/{product_id}/bookings/manual`
- `GET /api/v1/providers/me/bookings`
- `GET /api/v1/providers/me/bookings/{booking_id}`
- `PATCH /api/v1/providers/me/bookings/{booking_id}`
- `PATCH /api/v1/providers/me/bookings/{booking_id}/status`
- `GET /api/v1/providers/me/business-profile`
- `PUT /api/v1/providers/me/business-profile`
- `POST /api/v1/providers/me/business-profile/logo`
- `POST /api/v1/providers/me/business-profile/photos`
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
- endpoints de `providers` requieren:
  - `Authorization: Bearer <token>`
  - usuario con `role = provider`

## Perfil de negocio del proveedor
- `GET /api/v1/providers/me/business-profile`: devuelve el perfil del negocio del proveedor autenticado. Si aún no existe, responde un perfil vacío. Incluye `is_onboarding_completed` para que el cliente sepa si debe volver a mostrar el onboarding.
- `PUT /api/v1/providers/me/business-profile`: crea o actualiza el perfil del negocio del proveedor autenticado.
- `POST /api/v1/providers/me/business-profile/logo`: sube el logo al directorio local `uploads/`. Recibe `multipart/form-data` con campo `file` en formato `image/jpeg`, `image/png` o `image/webp`. El backend convierte la imagen a `.webp`.
- `POST /api/v1/providers/me/business-profile/photos`: sube una foto del negocio al directorio local `uploads/`. Recibe `multipart/form-data` con campo `file` en formato `image/jpeg`, `image/png` o `image/webp`. El backend convierte la imagen a `.webp`.

## Home del proveedor
- `GET /api/v1/providers/me/home`: devuelve la información principal para la pantalla home del proveedor.
- `GET /api/v1/providers/me/notifications`: devuelve las notificaciones del proveedor autenticado y el contador de no leídas.
- `PATCH /api/v1/providers/me/notifications/read-all`: marca todas las notificaciones como leídas.
- `PATCH /api/v1/providers/me/notifications/{notification_id}/read`: marca una notificación como leída.
- `DELETE /api/v1/providers/me/notifications`: elimina todas las notificaciones del proveedor autenticado.

Respuesta ejemplo de `GET /api/v1/providers/me/home`:
```json
{
  "provider_id": "provider_123",
  "display_name": "Jair",
  "business_name": "Sonido Fiesta",
  "avatar_url": "https://storage.example.com/logo.webp",
  "quick_stats": {
    "reservations_this_month": 0,
    "active_services": 0
  },
  "featured_services": []
}
```

Respuesta ejemplo de `GET /api/v1/providers/me/notifications`:
```json
{
  "items": [],
  "unread_count": 0
}
```

## Servicios del proveedor
- `POST /api/v1/providers/me/services`: crea un servicio padre.
- `POST /api/v1/providers/me/services/drafts`: crea un borrador mínimo de servicio para flujos como `CreateServiceView`.
- `GET /api/v1/providers/me/services`: lista los servicios padre del proveedor autenticado.
- `GET /api/v1/providers/me/services/{service_id}`: obtiene el detalle de un servicio padre.
- `PATCH /api/v1/providers/me/services/{service_id}`: actualiza parcialmente un servicio padre.
- `POST /api/v1/providers/me/services/{service_id}/images`: sube una imagen del servicio padre al directorio local `uploads/`. Recibe `multipart/form-data` con `file` y `is_main`. Acepta `jpg/png/webp` y la convierte a `.webp`.
- `PATCH /api/v1/providers/me/services/{service_id}/images/main`: cambia la foto principal del servicio padre usando `image_url`.
- `PATCH /api/v1/providers/me/services/{service_id}/images/reorder`: reordena las imágenes existentes del servicio padre usando la lista completa de `image_urls`.
- `DELETE /api/v1/providers/me/services/{service_id}/images`: elimina una imagen específica del servicio padre usando `image_url`.
- `DELETE /api/v1/providers/me/services/{service_id}`: elimina el servicio padre, sus productos hijos y todas sus imágenes locales del directorio `uploads/`.

Categorías soportadas:
- `dj`
- `photography`
- `entertainment`
- `banquet`
- `furniture`
- `equipment`
- `venue`
- `decoration`

Payload ejemplo para `POST /api/v1/providers/me/services`:
```json
{
  "category": "photography",
  "name": "Fotografía",
  "description": "Servicio principal de fotografía para eventos.",
  "status": "active"
}
```

Payload ejemplo para `POST /api/v1/providers/me/services/drafts`:
```json
{
  "category": "dj",
  "name": "DJ para eventos",
  "description": "Servicio base para eventos sociales."
}
```

## Productos del servicio
- `POST /api/v1/providers/me/services/{service_id}/products`: crea un producto hijo del servicio.
- `GET /api/v1/providers/me/services/{service_id}/products`: lista los productos hijos del servicio.
- `GET /api/v1/providers/me/services/by-name/{service_name}/products`: lista los productos hijos usando el nombre del servicio. Es útil para pantallas que todavía no navegan con `service_id`. Si el proveedor tiene servicios duplicados con el mismo nombre, responde conflicto.
- `GET /api/v1/providers/me/services/{service_id}/products/{product_id}`: obtiene el detalle de un producto.
- `PATCH /api/v1/providers/me/services/{service_id}/products/{product_id}`: actualiza parcialmente un producto.
- `DELETE /api/v1/providers/me/services/{service_id}/products/{product_id}`: elimina un producto y sus imágenes.
- `GET /api/v1/providers/me/products/reservations`: devuelve el resumen global de productos para la pantalla de reservas, incluyendo la próxima reserva por producto.
- `DELETE /api/v1/providers/me/products/{product_id}`: elimina un producto usando solo `product_id`, útil para flujos de resumen global.
- `POST /api/v1/providers/me/services/{service_id}/products/{product_id}/images`: sube una imagen del producto al directorio local `uploads/`. Recibe `multipart/form-data` con `file` y `is_main`. Acepta `jpg/png/webp` y la convierte a `.webp`.
- `PATCH /api/v1/providers/me/services/{service_id}/products/{product_id}/images/main`: cambia la foto principal del producto usando `image_url`.
- `PATCH /api/v1/providers/me/services/{service_id}/products/{product_id}/images/reorder`: reordena las imágenes del producto usando la lista completa de `image_urls`.
- `DELETE /api/v1/providers/me/services/{service_id}/products/{product_id}/images`: elimina una imagen específica del producto usando `image_url`.

Payload ejemplo para `POST /api/v1/providers/me/services/{service_id}/products`:
```json
{
  "name": "Cobertura premium",
  "description": "Cobertura completa para boda con entrega digital.",
  "price": 4500,
  "pricing_unit": "Por evento",
  "approx_photos": 300,
  "delivery_time": "15 días",
  "min_duration": "4 horas",
  "extra_hour_allowed": true,
  "extra_hour_price": 500,
  "inclusions": [
    "Edición básica",
    "Galería digital"
  ],
  "policies": [
    "50% de anticipo",
    "No reembolsable en cancelación"
  ]
}
```

Respuesta ejemplo de `GET /api/v1/providers/me/products/reservations`:
```json
{
  "items": [
    {
      "id": "prod_123",
      "service_id": "service_123",
      "product_name": "Cobertura premium",
      "category": "photography",
      "image_url": "https://storage.example.com/product.webp",
      "next_booking": {
        "booking_id": "booking_123",
        "customer_name": "Juan Perez",
        "customer_image_url": "",
        "date": "2026-03-28",
        "status": "Confirmada"
      }
    }
  ],
  "total": 1
}
```

## Disponibilidad del producto
- `GET /api/v1/providers/me/products/{product_id}/availability`: devuelve el calendario mensual de disponibilidad del producto. Requiere `year` y `month`.
- `PATCH /api/v1/providers/me/products/{product_id}/availability/{target_date}/block`: bloquea manualmente una fecha del producto.
- `PATCH /api/v1/providers/me/products/{product_id}/availability/{target_date}/unblock`: desbloquea una fecha bloqueada manualmente.
- El estado `reserved` se calcula a partir de reservas confirmadas del producto, incluidas las reservas manuales del proveedor.

Ejemplo:
`GET /api/v1/providers/me/products/prod_123/availability?year=2026&month=3`

Respuesta ejemplo:
```json
{
  "product_id": "prod_123",
  "product_name": "Cobertura premium",
  "year": 2026,
  "month": 3,
  "days": [
    {
      "date": "2026-03-01",
      "status": "available",
      "booking": null
    },
    {
      "date": "2026-03-02",
      "status": "reserved",
      "booking": {
        "booking_id": "booking_123",
        "customer_name": "Juan Perez",
        "customer_image_url": "",
        "event_type": "Boda",
        "guests": 150
      }
    }
  ]
}
```

## Reservas del proveedor
- `POST /api/v1/providers/me/products/{product_id}/bookings/manual`: crea una reserva manual confirmada y marca la fecha como `reserved` en disponibilidad.
- `GET /api/v1/providers/me/bookings`: lista reservas del proveedor autenticado. Acepta filtros opcionales `status`, `year`, `month` y `product_id`.
- `GET /api/v1/providers/me/bookings/{booking_id}`: obtiene el detalle de una reserva.
- `PATCH /api/v1/providers/me/bookings/{booking_id}`: modifica los datos editables de una reserva, incluidos montos y fecha. Si la reserva está confirmada y cambia de fecha, también se actualiza el calendario.
- `PATCH /api/v1/providers/me/bookings/{booking_id}/status`: actualiza el estado de una reserva. Cuando una reserva pasa a `confirmed` reserva la fecha del calendario; si sale de `confirmed`, libera esa fecha.

Payload ejemplo para `POST /api/v1/providers/me/products/{product_id}/bookings/manual`:
```json
{
  "customer_name": "Juan Perez",
  "event_date": "2026-03-28",
  "has_specific_schedule": true,
  "start_time": "18:30",
  "end_time": "23:00",
  "event_type": "Boda",
  "guests": 150,
  "contact_phone": "55 1234 5678",
  "contact_email": "cliente@correo.com",
  "event_location": "Jardin Las Palmas, Monterrey",
  "payment_details": "Anticipo de $2,000 recibido, resto pendiente",
  "total_amount": 8000,
  "paid_amount": 2000,
  "notes": "Anticipo liquidado. Montaje a las 16:00."
}
```

Respuesta ejemplo:
```json
{
  "id": "booking_123",
  "provider_id": "provider_123",
  "service_id": "service_123",
  "service_name": "Fotografia",
  "product_id": "prod_123",
  "product_name": "Cobertura premium",
  "customer_name": "Juan Perez",
  "customer_image_url": "",
  "event_date": "2026-03-28",
  "has_specific_schedule": true,
  "start_time": "18:30:00",
  "end_time": "23:00:00",
  "event_type": "Boda",
  "guests": 150,
  "contact_phone": "55 1234 5678",
  "contact_email": "cliente@correo.com",
  "event_location": "Jardin Las Palmas, Monterrey",
  "payment_details": "Anticipo de $2,000 recibido, resto pendiente",
  "total_amount": 8000,
  "paid_amount": 2000,
  "pending_amount": 6000,
  "time_label": "18:30 - 23:00",
  "status_label": "Confirmada",
  "notes": "Anticipo liquidado. Montaje a las 16:00.",
  "source": "manual",
  "status": "confirmed",
  "created_at": "2026-03-23T12:00:00Z",
  "updated_at": "2026-03-23T12:00:00Z"
}
```

Payload ejemplo para `PATCH /api/v1/providers/me/bookings/{booking_id}`:
```json
{
  "event_date": "2026-03-29",
  "start_time": "19:00",
  "end_time": "23:30",
  "total_amount": 9000,
  "paid_amount": 3000,
  "notes": "Cliente solicita una hora extra."
}
```

Payload ejemplo para `PATCH /api/v1/providers/me/bookings/{booking_id}/status`:
```json
{
  "status": "cancelled"
}
```

Payload ejemplo para `PATCH /api/v1/providers/me/services/{service_id}/images/main`:
```json
{
  "image_url": "https://firebasestorage.googleapis.com/..."
}
```

Payload ejemplo para `PATCH /api/v1/providers/me/services/{service_id}/images/reorder`:
```json
{
  "image_urls": [
    "https://firebasestorage.googleapis.com/...img2.webp",
    "https://firebasestorage.googleapis.com/...img1.webp"
  ]
}
```

Payload ejemplo:
```json
{
  "business_name": "Mi Negocio",
  "location": "Teziutlán, Puebla",
  "coverage_area": "Teziutlán y municipios cercanos",
  "contact_number": "+522221112233",
  "whatsapp": "+522221112233",
  "instagram": "@mi_negocio",
  "facebook": "Mi Negocio",
  "website": "https://minegocio.com",
  "logo_url": "https://storage.example.com/logo.jpg",
  "photo_urls": [
    "https://storage.example.com/photo-1.jpg",
    "https://storage.example.com/photo-2.jpg"
  ]
}
```

Archivos subidos:
- se guardan en `uploads/`
- se sirven públicamente desde `/uploads/...`
- si defines `UPLOADS_BASE_URL`, el backend regresará URLs absolutas; si no, regresará rutas relativas como `/uploads/providers/...`

Dependencias nuevas:
- `python-multipart`
- `Pillow`

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
