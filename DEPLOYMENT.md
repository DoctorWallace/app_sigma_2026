# 🚀 Guía de Despliegue - SIGMA Portal

## 📋 Requisitos Previos

### Servidor
- **Ubuntu 20.04+** o **CentOS 8+**
- **Python 3.9+**
- **PostgreSQL 12+**
- **Nginx** o **Apache**
- **SSL Certificate** (Let's Encrypt recomendado)

### Software
```bash
# Instalar dependencias del sistema
sudo apt update
sudo apt install python3-pip python3-venv postgresql postgresql-contrib nginx git

# Crear usuario para la aplicación
sudo adduser sigma
sudo usermod -aG sudo sigma
```

## 🔧 Configuración del Entorno

### 1. Clonar y Configurar el Proyecto
```bash
# Cambiar al usuario sigma
sudo su - sigma

# Clonar el repositorio
git clone <tu-repositorio> /home/sigma/sigma-portal
cd /home/sigma/sigma-portal

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar Base de Datos
```bash
# Crear base de datos PostgreSQL
sudo -u postgres psql
CREATE DATABASE sigma_db;
CREATE USER sigma_user WITH PASSWORD 'tu_password_seguro';
GRANT ALL PRIVILEGES ON DATABASE sigma_db TO sigma_user;
\q
```

### 3. Configurar Variables de Entorno
```bash
# Crear archivo .env
cp .env.example .env
nano .env
```

Configurar las siguientes variables:
```env
DB_NAME=sigma_db
DB_USER=sigma_user
DB_PASSWORD=tu_password_seguro
DB_HOST=localhost
DB_PORT=5432

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=tu_email@gmail.com
EMAIL_PASSWORD=tu_app_password
DEFAULT_FROM_EMAIL=sigma@ciemat.es

SECRET_KEY=tu-clave-secreta-muy-larga-y-segura-aqui
SITE_URL=https://tu-dominio.com
```

### 4. Configurar la Aplicación
```bash
# Ejecutar script de configuración
python scripts/setup_production.py

# Crear directorio de logs
mkdir -p logs
chmod 755 logs
```

## 🌐 Configuración del Servidor Web

### Nginx Configuration
```nginx
# /etc/nginx/sites-available/sigma-portal
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com www.tu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;

    # Configuración SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Archivos estáticos
    location /static/ {
        alias /home/sigma/sigma-portal/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Archivos media
    location /media/ {
        alias /home/sigma/sigma-portal/media/;
        expires 1y;
        add_header Cache-Control "public";
    }

    # Aplicación Django
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Activar el sitio
```bash
sudo ln -s /etc/nginx/sites-available/sigma-portal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔄 Configuración de Gunicorn

### Archivo de configuración
```python
# gunicorn.conf.py
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
```

### Servicio systemd
```ini
# /etc/systemd/system/sigma-portal.service
[Unit]
Description=SIGMA Portal Gunicorn daemon
After=network.target

[Service]
User=sigma
Group=sigma
WorkingDirectory=/home/sigma/sigma-portal
Environment="PATH=/home/sigma/sigma-portal/venv/bin"
ExecStart=/home/sigma/sigma-portal/venv/bin/gunicorn --config gunicorn.conf.py automatizacion.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

### Activar el servicio
```bash
sudo systemctl daemon-reload
sudo systemctl enable sigma-portal
sudo systemctl start sigma-portal
sudo systemctl status sigma-portal
```

## 🔒 Configuración SSL

### Let's Encrypt
```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com

# Configurar renovación automática
sudo crontab -e
# Añadir: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Monitoreo y Logs

### Configurar logs
```bash
# Crear directorio de logs
sudo mkdir -p /var/log/sigma-portal
sudo chown sigma:sigma /var/log/sigma-portal

# Configurar logrotate
sudo nano /etc/logrotate.d/sigma-portal
```

```bash
# /etc/logrotate.d/sigma-portal
/var/log/sigma-portal/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 sigma sigma
    postrotate
        systemctl reload sigma-portal
    endscript
}
```

## 🔄 Backup y Mantenimiento

### Script de backup
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/sigma/backups"
DB_NAME="sigma_db"

mkdir -p $BACKUP_DIR

# Backup de base de datos
pg_dump $DB_NAME > $BACKUP_DIR/db_$DATE.sql

# Backup de archivos media
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Limpiar backups antiguos (más de 30 días)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### Configurar backup automático
```bash
# Añadir a crontab
crontab -e
# 0 2 * * * /home/sigma/sigma-portal/backup.sh
```

## 🚀 Comandos de Despliegue

### Actualización de la aplicación
```bash
# Cambiar al usuario sigma
sudo su - sigma
cd /home/sigma/sigma-portal

# Activar entorno virtual
source venv/bin/activate

# Actualizar código
git pull origin main

# Actualizar dependencias
pip install -r requirements.txt

# Ejecutar migraciones
python manage.py migrate

# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Reiniciar servicios
sudo systemctl restart sigma-portal
sudo systemctl reload nginx
```

## 🔍 Verificación del Despliegue

### Comandos de verificación
```bash
# Verificar estado de servicios
sudo systemctl status sigma-portal
sudo systemctl status nginx
sudo systemctl status postgresql

# Verificar logs
sudo journalctl -u sigma-portal -f
tail -f /var/log/nginx/error.log

# Verificar conectividad
curl -I https://tu-dominio.com
```

## 📞 Soporte y Mantenimiento

### Comandos útiles
```bash
# Ver logs en tiempo real
sudo journalctl -u sigma-portal -f

# Reiniciar aplicación
sudo systemctl restart sigma-portal

# Verificar configuración Nginx
sudo nginx -t

# Verificar estado de la base de datos
sudo -u postgres psql -c "SELECT version();"
```

### Contacto
- **Email**: sigma@ciemat.es
- **Documentación**: [Enlace a documentación]
- **Issues**: [Enlace al repositorio de issues]
