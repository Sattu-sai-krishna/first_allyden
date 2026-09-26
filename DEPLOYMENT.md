# Free online deployment

The deployment uses a free Render web service and a free Neon PostgreSQL
database. The app's local SQLite database is not uploaded; attendance data
created online will be stored in Neon.

## 1. Push the project to GitHub

Create a private GitHub repository and push this project. Check that `.env` and
the local `*.db` files are not staged or pushed.

## 2. Create a Neon database

1. Create a free project at [Neon](https://neon.tech/).
2. In the project dashboard, open **Connect** and copy the pooled connection
   string for the database. It should start with `postgresql://` and include
   `sslmode=require`.
3. Keep the connection string private.

## 3. Create the Render service

1. Create a free account at [Render](https://render.com/).
2. Choose **New + → Blueprint**, connect the GitHub repository, and deploy
   `render.yaml`.
3. When prompted, set these environment variables:
   - `DATABASE_URL`: the Neon connection string.
   - `ATTENDANCE_ADMIN_PASSWORD`: a new, strong password for the attendance
     administrator. Do not reuse your Neon password.
4. Render generates `ATTENDANCE_TOKEN_SECRET` automatically. Wait for the
   service to finish deploying, then open its `onrender.com` URL.
5. Sign in using the admin password you configured.

The first free-tier request after inactivity may take a little while because
Render may spin down idle services.

## Local development

From the project root, run:

```powershell
.\fast_venv\Scripts\python.exe -m uvicorn main:app --app-dir Backend --reload
```

Local-only default admin password: `local-dev-only`. Set
`ATTENDANCE_ADMIN_PASSWORD` before running the app if you want to change it.
Never use the local default password for an online deployment.
