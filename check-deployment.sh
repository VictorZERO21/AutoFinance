#!/bin/bash

# Script de verificación pre-despliegue
# Uso: ./check-deployment.sh

echo "✅ Verificando preparación para despliegue..."
echo ""

# Verificar Python
if command -v python &> /dev/null; then
    echo "✓ Python: $(python --version)"
else
    echo "✗ Python no encontrado"
    exit 1
fi

# Verificar requirements.txt
if [ -f "requirements.txt" ]; then
    echo "✓ requirements.txt existe"
else
    echo "✗ requirements.txt no encontrado"
    exit 1
fi

# Verificar Dockerfile
if [ -f "Dockerfile" ]; then
    echo "✓ Dockerfile existe"
else
    echo "✗ Dockerfile no encontrado"
    exit 1
fi

# Verificar manage.py
if [ -f "manage.py" ]; then
    echo "✓ manage.py existe"
else
    echo "✗ manage.py no encontrado"
    exit 1
fi

# Verificar settings.py
if [ -f "autofinance_web/settings.py" ]; then
    echo "✓ settings.py configurado"
    if grep -q "decouple" autofinance_web/settings.py; then
        echo "✓ settings.py usa decouple para variables de entorno"
    else
        echo "⚠️  settings.py no usa decouple (necesario para Cloud Run)"
    fi
else
    echo "✗ settings.py no encontrado"
    exit 1
fi

# Verificar .env.example
if [ -f ".env.example" ]; then
    echo "✓ .env.example existe"
else
    echo "✗ .env.example no encontrado"
    exit 1
fi

# Verificar gunicorn en requirements
if grep -q "gunicorn" requirements.txt; then
    echo "✓ gunicorn está en requirements.txt"
else
    echo "⚠️  gunicorn no encontrado en requirements.txt"
fi

# Verificar whitenoise en requirements
if grep -q "whitenoise" requirements.txt; then
    echo "✓ whitenoise está en requirements.txt"
else
    echo "⚠️  whitenoise no encontrado en requirements.txt"
fi

echo ""
echo "📋 Resumen de archivos para despliegue:"
ls -lh Dockerfile requirements.txt manage.py autofinance_web/settings.py .env.example 2>/dev/null | tail -n +2 | awk '{print "  -", $9, "("$5")"}'

echo ""
echo "✅ Verificación completada"
echo ""
echo "Próximo paso: Ejecutar 'bash deploy.sh' para desplegar en Google Cloud"
