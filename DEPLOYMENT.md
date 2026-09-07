# Votex.ai — Production Deployment Guide

This guide covers 4 battle-tested methods for deploying **Votex.ai**:
1. [Option 1: Railway.app (Recommended — Quickest Cloud PaaS with MySQL)](#option-1-railwayapp-quickest-cloud-paas)
2. [Option 2: Render.com (Cloud Web Service)](#option-2-rendercom)
3. [Option 3: Docker & Docker Compose (One-Command Deployment)](#option-3-docker--docker-compose)
4. [Option 4: Ubuntu Linux VPS (AWS EC2 / DigitalOcean / Linode)](#option-4-ubuntu-vps-aws--digitalocean--linode)

---

## Prerequisites Checklist
Before deploying, ensure you have:
- Access to the GitHub repository: `https://github.com/singhaisarvagya8-hue/AI-Automated-Voting-System.git`
- A strong production secret key (generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`)
- Database credentials for MySQL 8.0+

---

## Option 1: Railway.app (Quickest Cloud PaaS)

Railway is the easiest cloud platform for Flask + MySQL because it offers native MySQL plugins and automatic GitHub deployment.

### Step 1: Create a Railway Project
1. Go to [Railway.app](https://railway.app/) and sign in with GitHub.
2. Click **New Project** → **Provision MySQL**.
3. Railway will spin up a managed MySQL instance.

### Step 2: Seed the MySQL Database
1. In the Railway dashboard, click on the **MySQL** card.
2. Go to the **Data** or **Connect** tab.
3. Open the Query editor or connect locally using the CLI:
   ```bash
   mysql -h <RAILWAY_HOST> -u root -p<PASSWORD> --port <PORT> railway < seed_data.sql
   ```

### Step 3: Deploy the Votex.ai Web App
1. In the same project, click **New** → **GitHub Repo**.
2. Select `AI-Automated-Voting-System`.
3. Railway automatically detects the `Procfile` (`web: gunicorn app:app --bind 0.0.0.0:$PORT`).
4. In the service **Variables** tab, add:
   - `DATABASE_URL`: `mysql+pymysql://root:${{MySQL.MYSQLPASSWORD}}@${{MySQL.MYSQLHOST}}:${{MySQL.MYSQLPORT}}/${{MySQL.MYSQLDATABASE}}`
   - `SECRET_KEY`: `<your-generated-secret-key>`
5. Go to **Settings** → **Networking** → **Generate Domain** (e.g. `votex.up.railway.app`).
6. Your live web application is now online with automated HTTPS!

---

## Option 2: Render.com

Render offers free/low-cost Web Services connected directly to GitHub.

### Step 1: Set Up MySQL
Render provides native PostgreSQL, but for MySQL, use a free cloud MySQL tier like:
- [Aiven.io](https://aiven.io/) (Free MySQL tier)
- [Clever Cloud](https://www.clever-cloud.com/) (Free MySQL addon)
- [PlanetScale](https://planetscale.com/)

Import the schema:
```bash
mysql -h <HOST> -u <USER> -p <DATABASE> < seed_data.sql
```

### Step 2: Create Web Service on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) → **New** → **Web Service**.
2. Connect your GitHub repository: `AI-Automated-Voting-System`.
3. Configure the settings:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Add Environment Variables:
   - `DATABASE_URL`: `mysql+pymysql://<USER>:<PASSWORD>@<HOST>:<PORT>/<DATABASE>`
   - `SECRET_KEY`: `<your-secret-key>`
5. Click **Create Web Service**. Render builds and deploys your site at `https://<app-name>.onrender.com`.

---

## Option 3: Docker & Docker Compose

Deploy the entire platform (Votex.ai Web Container + MySQL Container + Seeding) on any server with a single command.

### Step 1: Install Docker & Compose
On your server (macOS / Linux / Windows WSL2), verify Docker is running:
```bash
docker --version
docker compose version
```

### Step 2: Clone and Launch
```bash
git clone https://github.com/singhaisarvagya8-hue/AI-Automated-Voting-System.git
cd AI-Automated-Voting-System
docker compose up -d --build
```

### Step 3: Verify
- MySQL starts up and automatically runs `seed_data.sql`.
- Once MySQL passes healthcheck, the Flask web container builds and launches on port `5001`.
- Open **`http://YOUR_SERVER_IP:5001`** in your browser.

---

## Option 4: Ubuntu VPS (AWS / DigitalOcean / Linode)

For a production deployment on a dedicated Ubuntu 22.04 or 24.04 server.

### Step 1: Server Setup
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git nginx mysql-server certbot python3-certbot-nginx
```

### Step 2: Configure MySQL
```bash
sudo mysql -e "CREATE DATABASE voting_system_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER 'votex_admin'@'localhost' IDENTIFIED BY 'StrongPassword123!';"
sudo mysql -e "GRANT ALL PRIVILEGES ON voting_system_db.* TO 'votex_admin'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"
mysql -u votex_admin -p'StrongPassword123!' voting_system_db < seed_data.sql
```

### Step 3: Clone Code & Setup Virtual Environment
```bash
cd /var/www
sudo git clone https://github.com/singhaisarvagya8-hue/AI-Automated-Voting-System.git votex
sudo chown -R $USER:$USER /var/www/votex
cd /var/www/votex

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Create Environment File (`.env`)
```bash
cat << 'EOF' > /var/www/votex/.env
DATABASE_URL=mysql+pymysql://votex_admin:StrongPassword123!@127.0.0.1:3306/voting_system_db
SECRET_KEY=replace-with-a-random-64-character-hex-string-2026
PORT=5001
EOF
```

### Step 5: Configure Systemd Daemon (`votex.service`)
```bash
sudo bash -c 'cat << EOF > /etc/systemd/system/votex.service
[Unit]
Description=Votex.ai Gunicorn Application Server
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/votex
EnvironmentFile=/var/www/votex/.env
ExecStart=/var/www/votex/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5001 app:app

[Install]
WantedBy=multi-user.target
EOF'

sudo chown -R www-data:www-data /var/www/votex
sudo systemctl daemon-reload
sudo systemctl start votex
sudo systemctl enable votex
```

### Step 6: Configure Nginx Reverse Proxy
```bash
sudo bash -c 'cat << EOF > /etc/nginx/sites-available/votex
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF'

sudo ln -s /etc/nginx/sites-available/votex /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 7: Enable SSL with Let's Encrypt
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 🔒 Production Security Checklist
- [ ] Change all default demo passwords (`ADMIN001`, `CS202601`, `CS202602`).
- [ ] Set `SECRET_KEY` to a cryptographically secure 256-bit random string.
- [ ] Ensure `DEBUG=False` in production.
- [ ] Restrict MySQL access to `localhost` or internal VPC network.
- [ ] Enforce HTTPS / TLS 1.3 with automated certificate renewal.
