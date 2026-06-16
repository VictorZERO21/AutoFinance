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
