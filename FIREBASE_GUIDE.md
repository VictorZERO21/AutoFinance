# Guía de Despliegue en Firebase + Cloud Run

## Arquitectura

```
Firebase Hosting (Frontend)
    ↓ (API calls)
Cloud Run (Django Backend)
    ↓
Cloud SQL (PostgreSQL)
```

## Paso 1: Crear Proyecto en Firebase

1. Ve a https://console.firebase.google.com
2. Haz clic en "Create Project"
3. Nombre: `autofinance`
4. Desactiva Google Analytics
5. Crea el proyecto

## Paso 2: Obtener credenciales de Firebase

1. En Firebase Console, ve a **Project Settings** (⚙️)
2. Copia tu **Project ID**
3. Ve a la pestaña **Service Accounts**
4. Genera una **nueva clave privada**
5. Guarda el JSON (lo necesitarás después)

## Paso 3: Crear .firebaserc

```bash
cd c:\Users\PC\AutoFinance
firebase projects:list  # Verifica tus proyectos
firebase use autofinance  # Selecciona tu proyecto
```

O crea manualmente `.firebaserc`:
```json
{
  "projects": {
    "default": "autofinance"
  }
}
```

## Paso 4: Obtener configuración de Firebase

En Firebase Console → Project Settings → General → Web apps:
- Copia el objeto de configuración
- Reemplaza en `public/firebase-config.js`

## Paso 5: Desplegar Django en Cloud Run

```bash
# Usar los mismos pasos que Cloud Run anterior
bash deploy.sh
```

Anota la URL de Cloud Run (ej: `https://autofinance-xyz.run.app`)

## Paso 6: Actualizar firebase.json

Reemplaza `autofinance` con el ID real de tu servicio en Cloud Run:

```json
{
  "hosting": {
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "autofinance",
          "region": "us-central1"
        }
      }
    ]
  }
}
```

## Paso 7: Preparar Hosting

```bash
# Copiar templates como HTML estático (opcional)
# O mantener solo la API en Cloud Run

firebase deploy --only hosting
```

## Paso 8: Configurar CORS

En `autofinance_web/settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    "https://autofinance-xxxxx.web.app",
    "https://autofinance-xxxxx.firebaseapp.com",
]
```

## Alternativa: Desplegar Django en Cloud Run + usar Firebase Hosting como proxy

Esto es lo que haremos. Aquí está el flujo:

### 1. Cloud Run ejecuta Django normalmente
### 2. Firebase Hosting redirige `/api/*` a Cloud Run
### 3. El resto de requests van a Firebase Hosting (estáticos)

## Costos Estimados

| Servicio | Tier Gratuito | Precio |
|----------|---|---|
| Firebase Hosting | 1GB almacenamiento, 10GB/mes ancho de banda | Gratis |
| Cloud Run | 2M requests/mes, 360K GB-seg | Gratis |
| Cloud SQL | db-f1-micro con créditos | $10-15/mes |
| **TOTAL** | | **Gratis - $15/mes** |

## Troubleshooting

### Error: "Cannot find project"
```bash
firebase login
firebase projects:list
firebase use --add  # Agregar proyecto
```

### Error: CORS issues
Asegúrate que `ALLOWED_HOSTS` en Django incluya el dominio de Firebase.

### Error: Archivos estáticos no se sirven
Firebase Hosting necesita que los archivos estén en `public/`.
Copia tus templates Django a `public/` o sírvelos desde Cloud Run.

## Comandos Útiles

```bash
# Ver proyectos disponibles
firebase projects:list

# Cambiar proyecto activo
firebase use PROJECT_ID

# Deploy solo Hosting
firebase deploy --only hosting

# Ver logs en tiempo real
firebase functions:log

# Conectar localmente
firebase emulators:start

# Eliminar un deployment
firebase hosting:delete
```
