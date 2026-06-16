#!/bin/bash

# Script de despliegue a Google Cloud Run
# Uso: ./deploy.sh

set -e

echo "🚀 AutoFinance - Despliegue a Google Cloud Run"
echo "=============================================="

# Verificar que Google Cloud SDK esté instalado
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud SDK no está instalado"
    echo "Descárgalo en: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Variables de configuración
read -p "Ingresa tu PROJECT_ID: " PROJECT_ID
read -p "Ingresa la REGIÓN (default: us-central1): " REGION
REGION=${REGION:-us-central1}
read -p "Ingresa la contraseña de PostgreSQL: " DB_PASSWORD
read -p "Ingresa SECRET_KEY (o presiona Enter para generar): " SECRET_KEY

if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(openssl rand -base64 32)
    echo "🔑 SECRET_KEY generada: $SECRET_KEY"
fi

echo ""
echo "📋 Resumen de configuración:"
echo "  - Project ID: $PROJECT_ID"
echo "  - Región: $REGION"
echo "  - Base de datos: autofinance-postgres"
echo ""
read -p "¿Continuar? (s/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    exit 1
fi

# 1. Configurar Google Cloud
echo ""
echo "1️⃣  Configurando Google Cloud..."
gcloud config set project $PROJECT_ID

# 2. Habilitar APIs
echo "2️⃣  Habilitando APIs necesarias..."
gcloud services enable run.googleapis.com
gcloud services enable cloudsql.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 3. Crear instancia Cloud SQL
echo "3️⃣  Creando instancia Cloud SQL..."
gcloud sql instances create autofinance-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  2>/dev/null || echo "   ⚠️  La instancia ya existe"

# 4. Establecer contraseña
echo "4️⃣  Configurando contraseña de PostgreSQL..."
gcloud sql users set-password postgres \
  --instance=autofinance-postgres \
  --password=$DB_PASSWORD

# 5. Crear base de datos
echo "5️⃣  Creando base de datos..."
gcloud sql databases create autofinance_db \
  --instance=autofinance-postgres \
  2>/dev/null || echo "   ⚠️  La base de datos ya existe"

# 6. Obtener CONNECTION_NAME
echo "6️⃣  Obteniendo CONNECTION_NAME..."
CONNECTION_NAME=$(gcloud sql instances describe autofinance-postgres \
  --format='value(connectionName)')
echo "   CONNECTION_NAME: $CONNECTION_NAME"

# 7. Build y deploy
echo "7️⃣  Construyendo y desplegando a Cloud Run..."
gcloud run deploy autofinance \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 3600 \
  --set-env-vars "USE_CLOUD_SQL=True,CLOUD_SQL_DATABASE=autofinance_db,CLOUD_SQL_USER=postgres,CLOUD_SQL_PASSWORD=$DB_PASSWORD,CLOUD_SQL_HOST=/cloudsql/$CONNECTION_NAME,DEBUG=False,SECRET_KEY=$SECRET_KEY,ALLOWED_HOSTS=autofinance-***.run.app"

# 8. Obtener URL
echo ""
echo "8️⃣  Obteniendo URL de la aplicación..."
SERVICE_URL=$(gcloud run services describe autofinance --platform managed --region $REGION --format='value(status.url)')
echo "✅ Aplicación desplegada en: $SERVICE_URL"

echo ""
echo "📝 Próximos pasos:"
echo "1. Visita $SERVICE_URL para ver tu aplicación"
echo "2. Para ejecutar migraciones:"
echo "   cloud-sql-proxy $CONNECTION_NAME &"
echo "   python manage.py migrate"
echo "3. Configura dominio personalizado en la consola de Google Cloud"
echo ""
echo "🎉 ¡Despliegue completado!"
