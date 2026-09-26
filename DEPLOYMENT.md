# Free online deployment

The app can run on Render's free web service with SQLite and no external
database account. This is suitable for a demo, but Render's free service has
ephemeral storage: attendance data can be lost when the service restarts or
redeploys. Use PostgreSQL for real attendance records that must persist.

## 1. Push the project to GitHub

Push this project to a GitHub repository. Check that `.env`, local database
files, and student data files are not staged or pushed.

## 2. Create the Render service

1. Create a free account at [Render](https://render.com/).
2. Choose **New + → Blueprint**, connect the GitHub repository, and deploy
   `render.yaml`.
3. Render generates a secure `ATTENDANCE_ADMIN_PASSWORD` and
   `ATTENDANCE_TOKEN_SECRET` automatically. No `DATABASE_URL` is needed for the
   SQLite demo.
4. After deployment, find and reveal `ATTENDANCE_ADMIN_PASSWORD` in the
   service's Environment settings, then open its `onrender.com` URL and sign
   in with that password.

The first free-tier request after inactivity may take a little while because
Render may spin down idle services.

To retain attendance data across restarts and redeploys, configure a persistent
PostgreSQL database and set `DATABASE_URL` in the Render service environment.

## Local development

From the project root, run:

```powershell
.\fast_venv\Scripts\python.exe -m uvicorn main:app --app-dir Backend --reload
```

Local-only default admin password: `local-dev-only`. Set
`ATTENDANCE_ADMIN_PASSWORD` before running the app if you want to change it.
Never use the local default password for an online deployment.
