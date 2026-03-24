# Client Endpoints Summary

Este documento resume los endpoints nuevos del módulo `client` en Festum API, su propósito y flujo esperado.

## Seguridad

Todos los endpoints de este documento requieren JWT:

- Header: `Authorization: Bearer <token>`   
- El token se obtiene en `POST /api/v1/auth/login` o `POST /api/v1/auth/register`.

## Base Path

`/api/v1/client`

## 1) Cart

### `GET /api/v1/client/cart`
Obtiene los elementos actuales del carrito del cliente autenticado.

Respuesta:
- `200 OK`
- Formato:
```json
{
  "items": [
    {
      "id": "hall-aurora",
      "name": "Salón Aurora",
      "quantity": 1,
      "unit_price_cents": 4120000
    }
  ]
}
```

### `DELETE /api/v1/client/cart`
Limpia por completo el carrito del cliente autenticado.

Respuesta:
- `200 OK`
```json
{ "ok": true }
```

### `GET /api/v1/client/cart/contains/{serviceId}`
Valida si un servicio ya está en carrito.

Respuesta:
- `200 OK`
```json
{ "contains": true }
```

### `POST /api/v1/client/cart/items`
Agrega un servicio único al carrito.  
Regla de negocio: no permite duplicados por `service_id`.

Body:
```json
{
  "service_id": "hall-aurora",
  "name": "Salón Aurora",
  "unit_price_cents": 4120000
}
```

Respuestas:
- `201 Created` con el item creado.
- `409 Conflict` si el servicio ya existe:
```json
{
  "success": false,
  "message": "Service already in cart",
  "detail": "Service already in cart",
  "code": "CART_DUPLICATE_ITEM"
}
```

### `DELETE /api/v1/client/cart/items/{id}`
Elimina un item del carrito y devuelve el item removido (útil para undo en UI).

Respuestas:
- `200 OK`
```json
{
  "item": {
    "id": "hall-aurora",
    "name": "Salón Aurora",
    "quantity": 1,
    "unit_price_cents": 4120000
  }
}
```
- `404 Not Found` si no existe.

### `POST /api/v1/client/cart/restore`
Restaura un item previamente removido en el carrito.

Body:
```json
{
  "item": {
    "id": "hall-aurora",
    "name": "Salón Aurora",
    "quantity": 1,
    "unit_price_cents": 4120000
  },
  "index": 0
}
```

Respuesta:
- `200 OK`
```json
{ "ok": true }
```

## 2) Orders

### `GET /api/v1/client/orders`
Lista las órdenes del cliente autenticado.

Respuesta:
- `200 OK`
```json
{
  "items": [
    {
      "id": "FST-2202",
      "title": "Salón Aurora +1 servicios",
      "status": "pending_payment",
      "total_label": "$56,900 MXN",
      "created_at": "2026-03-23T12:00:00Z"
    }
  ]
}
```

### `POST /api/v1/client/orders`
Crea una orden nueva.

Body:
```json
{
  "title": "Salón Aurora +1 servicios",
  "status": "pending_payment",
  "total_label": "$56,900 MXN"
}
```

Respuesta:
- `201 Created` con la orden creada.

### `PATCH /api/v1/client/orders/{orderId}/status`
Actualiza el estado de una orden.

Body:
```json
{ "status": "confirmed" }
```

Respuestas:
- `200 OK`:
```json
{ "ok": true }
```
- `404 Not Found` si la orden no existe.
- `409 Conflict` si la transición no es válida:
```json
{
  "success": false,
  "message": "Invalid transition: pending_payment -> completed",
  "detail": "Invalid transition: pending_payment -> completed",
  "code": "ORDER_INVALID_TRANSITION"
}
```

Transiciones válidas:
- `pending_payment` -> `confirmed`, `cancelled`
- `confirmed` -> `in_progress`, `cancelled`
- `in_progress` -> `completed`, `cancelled`
- `completed` -> (sin transición)
- `cancelled` -> (sin transición)

## 3) Services

### `GET /api/v1/client/services/home`
Devuelve servicios agrupados para pantalla Home.

Respuesta:
- `200 OK`
```json
{
  "salones-sociales": [],
  "mobiliario": [],
  "banquetes": []
}
```

### `GET /api/v1/client/services?category={category}`
Lista servicios por categoría.

Categorías válidas:
- `salones-sociales`
- `mobiliario`
- `banquetes`

Respuesta:
- `200 OK` con arreglo de servicios.

### `GET /api/v1/client/services/{serviceId}?category={category}`
Obtiene detalle de un servicio por `id` y valida categoría.

Respuestas:
- `200 OK` con el servicio.
- `404 Not Found` si no existe o no coincide con la categoría.

## Estructura de almacenamiento (Firestore)

Se implementó con el siguiente esquema:

- `services/{serviceId}`: catálogo de servicios.
- `client_carts/{userId}/items/{serviceId}`: carrito por cliente.
- `client_orders/{userId}/items/{orderId}`: órdenes por cliente.

## Notas para Flutter

- Usa `service_id` como llave estable para carrito (evita duplicados).
- Guarda el item removido localmente para usar `restore`.
- Para UX, refresca carrito y órdenes después de `add/remove/create/update`.

