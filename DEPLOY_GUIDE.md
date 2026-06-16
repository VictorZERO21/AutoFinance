# Guía de Despliegue en Google Cloud Run

## Prerrequisitos

1. Cuenta de Google Cloud con facturación habilitada
2. Google Cloud SDK instalado ([Descargar](https://cloud.google.com/sdk/docs/install))
3. Docker instalado
4. Git instalado

## Paso 1: Configurar Google Cloud SDK

```bash
# Autenticar con Google Cloud
gcloud auth login

# Establecer el proyecto (reemplaza PROJECT_ID con tu ID)
gcloud config set project PROJECT_ID

# Habilitar APIs necesarias
gcloud services enable run.googleapis.com
gcloud services enable cloudsql.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

## Paso 2: Crear instancia de Cloud SQL PostgreSQL

```bash
# Crear instancia SQL
gcloud sql instances create autofinance-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Establecer contraseña de root
gcloud sql users set-password postgres \
  --instance=autofinance-postgres \
  --password=TU_CONTRASEÑA_SEGURA

# Crear base de datos
gcloud sql databases create autofinance_db \
  --instance=autofinance-postgres
```

## Paso 3: Obtener información de conexión

```bash
# Obtener CONNECTION_NAME (PROJECT_ID:REGION:INSTANCE_NAME)
gcloud sql instances describe autofinance-postgres \
  --format='value(connectionName)'
```

## Paso 4: Preparar la aplicación

```bash
# En el directorio del proyecto
cp .env.example .env

# Editar .env con tus valores:
# - SECRET_KEY: Generar una nueva clave segura
# - CLOUD_SQL_PASSWORD: La contraseña que estableciste
# - CLOUD_SQL_HOST: El CONNECTION_NAME que obtuviste
# - ALLOWED_HOSTS: Tu dominio de Cloud Run
```

## Paso 5: Desplegar a Cloud Run

```bash
# Opción A: Usando gcloud (más simple)
gcloud run deploy autofinance \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "USE_CLOUD_SQL=True,CLOUD_SQL_DATABASE=autofinance_db,CLOUD_SQL_USER=postgres,CLOUD_SQL_PASSWORD=TU_CONTRASEÑA,CLOUD_SQL_HOST=/cloudsql/PROJECT_ID:us-central1:autofinance-postgres,DEBUG=False,SECRET_KEY=TU_SECRET_KEY"

# Opción B: Usando Docker (si prefieres más control)
# Primero habilitar Container Registry
gcloud services enable containerregistry.googleapis.com

# Build y push
gcloud builds submit --tag gcr.io/PROJECT_ID/autofinance

# Deploy
gcloud run deploy autofinance \
  --image gcr.io/PROJECT_ID/autofinance \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "USE_CLOUD_SQL=True,CLOUD_SQL_DATABASE=autofinance_db,CLOUD_SQL_USER=postgres,CLOUD_SQL_PASSWORD=TU_CONTRASEÑA,CLOUD_SQL_HOST=/cloudsql/PROJECT_ID:us-central1:autofinance-postgres,DEBUG=False,SECRET_KEY=TU_SECRET_KEY"
```

## Paso 6: Ejecutar migraciones

```bash
# Conectar a Cloud Run (obtén la URL del paso anterior)
# Luego ejecuta migraciones (necesitas SSH o crear una tarea de Cloud Tasks)

# Alternativa: Crear un script de inicialización en el Dockerfile
```

## Paso 7: Verificar despliegue

Visita la URL que proporciona Cloud Run. Deberías ver tu aplicación AutoFinance en línea.

## Pasos posteriores

1. **Configurar dominio personalizado**: En Cloud Run > autofinance > Manage Custom Domains
2. **Habilitar SSL**: Se configura automáticamente con Cloud Run
3. **Configurar CI/CD**: Conecta GitHub a Cloud Build para deployments automáticos
4. **Monitoreo**: Usa Cloud Logging y Cloud Monitoring para revisar logs

## Solución de problemas

### Error de conexión a Cloud SQL
- Asegúrate que la instancia SQL está en la misma región que Cloud Run
- Verifica que el CONNECTION_NAME es correcto

### Error de archivos estáticos
- Ejecuta `python manage.py collectstatic` antes de desplegar
- Verifica que `STATIC_ROOT` está configurado correctamente

### Error de migraciones
- Ejecuta migraciones antes del primer despliegue
- Usa Cloud SQL Proxy para conectar localmente:
  ```bash
  cloud-sql-proxy PROJECT_ID:us-central1:autofinance-postgres &
  python manage.py migrate --database postgresql
  ```

## Costos estimados (tier gratuito)

- Cloud Run: 2 millones de requests/mes gratis
- Cloud SQL: db-f1-micro tiene créditos gratuitos
- Costo mensual estimado: $0-10 USD (con uso moderado)
