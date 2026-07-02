## ⚠️ Nota importante antes de empezar
**Para hacer todo esto necesitarán instalar Git para abrir la terminal Bash. Si usan otra consola, diganle a la ia que lo adapte a su terminal c:**

---
- Paso 1: Clonar el repositorio limpio

git clone https://github.com/VictorZERO21/AutoFinance.git

cd AutoFinance

<br>

- Paso 2: Crear su propio entorno virtual local

python -m venv venv

<br>

- Paso 3: Activar el entorno virtual (En Bash)

source venv/Scripts/activate

<br>

- Paso 4: Instalar Django y las librerías necesarias

pip install django numpy-financial "psycopg[binary]"

<br>

- Paso 5: Cambiar la base de datos

En la carpeta autofinance_web en el archivo settings.py bajen hasta la parte de DATABASES y pongan su información

Y guardarlo con Control + S

<br>

- Paso 6: Crear las tablas y arrancar
  
python manage.py migrate

python manage.py runserver

---

## Probar en PostgreSQL (local)

Si quieren probar el proyecto en PostgreSQL sin tocar su SQLite, usen este flujo:

- Paso 1: Levantar PostgreSQL con Docker

docker compose -f docker-compose.postgres.yml up -d

- Paso 2: Crear su archivo .env local

Copien `.env.example` a `.env` y asegúrense de tener esta variable:

DATABASE_URL=postgresql://autofinance:autofinance@localhost:5432/autofinance

`settings.py` ya prioriza `DATABASE_URL`, así que al estar presente usará PostgreSQL automáticamente.

- Paso 3: Ejecutar migraciones en PostgreSQL

python manage.py migrate

- Paso 4: Arrancar el servidor

python manage.py runserver

- Paso 5: (Opcional) volver a SQLite

Quiten o comenten `DATABASE_URL` en `.env` y el proyecto volverá a usar `db.sqlite3`.
