# ERP Management System

Proyecto personal de un ERP desarrollado con Django para gestionar compras, ventas, inventarios y datos maestros. Inicié este proyecto para explorar el desarrollo backend, la lógica de negocio y la integración de distintos procesos empresariales en una misma aplicación.

El proyecto sigue en desarrollo y está pensado para pruebas y demostraciones locales.

## Funcionalidades

- Gestión de materiales, clientes y proveedores, incluyendo importación de CSV.
- Órdenes de compra, recepciones de mercancía y facturas de compra.
- Movimientos de inventario, existencias diarias y costo promedio ponderado (WAC).
- Órdenes de venta, reservas de inventario y cálculo de márgenes (solo USD).
- Autenticación, permisos por módulo y generación interna de asientos contables.
- Filtros de búsqueda, paginación y exportación CSV.

Los envíos y la facturación de ventas, la interfaz de contabilidad y los reportes siguen en desarrollo.

## Tecnologías

- **Backend:** Python, Django, Django ORM
- **Frontend:** JavaScript, HTML, Tailwind CSS, Django Templates
- **Base de datos:** SQLite
- **Herramientas:** Git, GitHub, python-dotenv

## Instalación

Necesitarás Python 3.12 o superior (compatible con las versiones de las dependencias), Git y conexión a Internet para instalar las dependencias y cargar Tailwind CSS.

### 1. Clonar el repositorio

```bash
git clone https://github.com/Potato1Peeler/ERP-Management-System.git
cd ERP-Management-System
```

### 2. Crear un entorno virtual

Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

### 3. Configurar las variables de entorno

Copia `.env.example` a un nuevo archivo llamado `.env` en la raíz del proyecto.

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Pega la clave generada en `DJANGO_SECRET_KEY` dentro de `.env`. Puedes conservar el resto de la configuración de ejemplo para trabajar localmente. No subas `.env` al repositorio.

### 4. Preparar la base de datos

```bash
python manage.py migrate
python manage.py loaddata fixtures/master_data.json fixtures/demo_data.json
```

Los fixtures incluyen catálogos, roles, almacenes y materiales, clientes y proveedores ficticios. Cárgalos únicamente en una base de datos nueva, ya que podrían sobrescribir registros existentes.

### 5. Crear un usuario y asignar permisos

```bash
python manage.py createsuperuser --username demo
```

Introduce tu correo y elige una contraseña. Después, asigna el rol `Demo` para habilitar el acceso a los módulos del ERP:

```bash
python manage.py shell -c "from users.models import User, Role, UserRole; UserRole.objects.get_or_create(user_id=User.objects.get(username='demo'), role=Role.objects.get(role_name='Demo'))"
```

El ERP utiliza su propio sistema de roles, por lo que crear un superusuario de Django no es suficiente para habilitar los módulos del dashboard.

### 6. Ejecutar el proyecto

```bash
python manage.py runserver
```

Abre [http://127.0.0.1:8000/](http://127.0.0.1:8000/) e inicia sesión con las credenciales que creaste.

## Probar el ERP

La demostración comienza sin existencias ni órdenes registradas. Para probar la integración entre módulos:

1. Crea una orden de compra para el proveedor `DEMO-SUP-001` con 100 unidades de `DEMO-MAT-001` a 10 USD cada una.
2. Registra una recepción de las 100 unidades en el almacén `WH_DEMO01`.
3. Consulta las existencias y el historial de movimientos en Inventory; después crea la factura de compra.
4. Crea una orden de venta para el cliente `DEMO-CUST-001`, reservando 20 unidades del mismo material y almacén a 15 USD cada una.
5. Regresa a Stock. El resultado esperado es de 100 unidades físicas, 20 reservadas y 80 disponibles, con un WAC de 10 USD.

La orden de venta reserva mercancía; no registra su envío. Si las existencias no se han actualizado en la demostración local, ejecuta:

```bash
python manage.py shell -c "from inventory.views import sync_daily_stock_date; sync_daily_stock_date()"
```

Esta versión está destinada a demostraciones locales, no a entornos de producción.

## Autor

Alejandro Ku León — Estudiante de Ingeniería en Sistemas Computacionales en el Instituto Tecnológico de Mérida.

[GitHub](https://github.com/Potato1Peeler) · [LinkedIn](https://www.linkedin.com/in/alejandro-ku-le%C3%B3n-955879407/)
