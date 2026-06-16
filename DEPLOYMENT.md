# Production Deployment Guide

This guide provides step-by-step instructions to deploy the Shared Expenses App (Django backend + React frontend + PostgreSQL database) for free on **Neon**, **Render**, and **Vercel**.

---

## Step 1: Commit and Push the Latest Changes to GitHub

Before beginning, ensure that the latest settings and environment-variable fixes are pushed to your GitHub repository.

Run these commands in your local project root:
```bash
git add backend/config/settings.py frontend/src/api.js
git commit -m "Configure production environment variables for backend and frontend"
git push origin main
```

---

## Step 2: Set Up a Free PostgreSQL Database on Neon.tech

1. Go to [Neon.tech](https://neon.tech/) and sign up for a free account.
2. Click **Create Project**.
3. Name your project (e.g., `shared-expenses-db`), select PostgreSQL version **16**, and choose the region closest to you.
4. Once created, you will see a **Connection String** under "Connection Details". It will look like this:
   ```text
   postgresql://neondb_owner:password@ep-cool-breeze-12345.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
5. Copy this entire connection string. You will need it in the next step.

---

## Step 3: Deploy the Backend on Render

1. Go to [Render.com](https://render.com/) and sign up/log in.
2. Click the **New +** button and select **Web Service**.
3. Connect your GitHub account and select your `Shared-Expenses-App` repository.
4. Configure the Web Service settings:
   * **Name**: `shared-expenses-backend`
   * **Region**: Choose the same region as your Neon database.
   * **Branch**: `main`
   * **Runtime**: `Python 3`
   * **Root Directory**: `backend` (Make sure this is set to `backend` since Render needs to build from the subdirectory)
5. Set the build and start commands:
   * **Build Command**:
     ```bash
     pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
     ```
   * **Start Command**:
     ```bash
     gunicorn config.wsgi:application
     ```
6. Scroll down and click **Advanced** to add **Environment Variables**:
   * Add the following keys:
     | Key | Value | Description |
     | :--- | :--- | :--- |
     | `DATABASE_URL` | *Your copied Neon connection string* | Links Django to PostgreSQL. |
     | `SECRET_KEY` | `django-secure-production-random-key-123!@#` | Set a unique random key for production. |
     | `DEBUG` | `False` | Disables verbose debug views for security. |
7. Click **Create Web Service**.
8. Wait a few minutes for the build to complete. Once finished, Render will show **Live** and display your live URL (e.g., `https://shared-expenses-backend.onrender.com`).
9. Copy your backend URL.

---

## Step 4: Deploy the Frontend on Vercel

1. Go to [Vercel.com](https://vercel.com/) and sign up/log in.
2. Click **Add New...** and select **Project**.
3. Import your `Shared-Expenses-App` repository.
4. Configure the Vercel project settings:
   * **Framework Preset**: `Vite` (Vercel detects this automatically).
   * **Root Directory**: Click "Edit" and choose the `frontend` folder.
5. Expand the **Environment Variables** section and add:
   * **Name**: `VITE_API_URL`
   * **Value**: *Your copied Render backend URL* with `/api` appended at the end.
     * *Example*: `https://shared-expenses-backend.onrender.com/api` (Do not add a trailing slash after `/api`).
6. Click **Deploy**.
7. Vercel will build your React application. Once completed, your frontend app will be live on a `.vercel.app` URL.

---

## Step 5: Verification

1. Open your Vercel frontend URL.
2. Sign up a new user or log in.
3. Import the `expenses_export.csv` file using the UI and confirm the import report displays properly.
4. Query the AI Assistant in the group details drawer to verify backend communication is fully operational.
