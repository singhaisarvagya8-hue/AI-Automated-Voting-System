# Deploying votex.ai to Netlify

This guide details how to deploy your Flask-based voting system to **Netlify** using Netlify Functions and serverless WSGI, as well as alternative 1-click cloud platforms.

---

## 🚀 Option 1: Deploy to Netlify (Via GitHub)

The repository is fully configured with `netlify.toml` and `netlify/functions/server.py` using `serverless-wsgi`.

### Step 1: Push latest code to GitHub
Make sure all your latest changes are pushed to your repository:
```bash
git push origin main
```
Repository: `https://github.com/singhaisarvagya8-hue/AI-Automated-Voting-System.git`

### Step 2: Connect Repository to Netlify
1. Log in to [Netlify Dashboard](https://app.netlify.com/).
2. Click **"Add new site"** &rarr; **"Import an existing project"**.
3. Select **GitHub** and choose the `AI-Automated-Voting-System` repository.
4. Netlify will automatically detect `netlify.toml`:
   - **Build command**: `pip install -r requirements.txt`
   - **Functions directory**: `netlify/functions`
   - **Publish directory**: `static`
5. Click **"Deploy site"**.

### Step 3: (Optional) Connect a Production Cloud Database
By default, the application is configured with auto-detection:
- If no external database is configured, it automatically initializes a self-seeding SQLite database in `/tmp/voting_system.db` with default demo accounts (`ADMIN001` / `CS202601`).
- For persistent shared database storage across serverless instances:
  1. Create a free cloud MySQL or PostgreSQL database (e.g., [TiDB Serverless](https://tidb.cloud/), [Aiven](https://aiven.io/), or [Supabase](https://supabase.com/)).
  2. In your Netlify Site dashboard, go to **Site configuration** &rarr; **Environment variables**.
  3. Add variable `DATABASE_URL`:
     ```text
     DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:<port>/<dbname>
     ```
  4. Redeploy your site.

---

## ⚡ Option 2: Deploy to Render (Recommended for Flask)

Netlify is primarily a static and serverless platform. If you want a persistent Python WSGI server (Gunicorn) with continuous background workers:

1. Log in to [Render](https://dashboard.render.com/).
2. Click **"New +"** &rarr; **"Web Service"**.
3. Select your GitHub repository `AI-Automated-Voting-System`.
4. Render will read `render.yaml` / `Procfile`:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Click **"Create Web Service"**.

---

## 🔑 Default Login Credentials
- **Administrator**: `ADMIN001` / `password123`
- **Student Voter 1**: `CS202601` / `password123`
- **Student Voter 2**: `CS202602` / `password123`
- **Master Commissioner Key**: `master2026` or `password123`
