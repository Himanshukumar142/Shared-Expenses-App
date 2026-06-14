# FairShare - Shared Expenses App

FairShare is a Splitwise-like Shared Expenses App built as a software engineering internship assignment. It features JWT Authentication, temporal group memberships, USD/INR multi-currency support, debt settlements simplification, balance ledger traceability, and an interactive CSV import anomaly detection engine with a review workflow.

---

## Technical Stack
* **Backend**: Django REST Framework (DRF) + Simple JWT.
* **Frontend**: React (Vite) + Tailwind CSS + Axios.
* **Database**: PostgreSQL (with a self-healing local SQLite fallback).
* **AI Collaborator**: Gemini 3.5 Flash (High).

---

## Features Implemented
1. **JWT Auth**: Registration and secure logins.
2. **Temporal Memberships**: Excludes Sam from March bills and Meera from April bills (Joined/Left timeline filters).
3. **Traceability (Rohan's Request)**: Clicking balances breaks down exact splits and paid items (no magic numbers).
4. **USD Multi-currency (Priya's Request)**: Preserves original values, applies exchange rates, and stores normalized INR.
5. **Debt Simplification (Aisha's Request)**: Greedy creditor-debtor matching to minimize transactions.
6. **CSV Import Anomaly Engine**: Parses inconsistent dates, quoted amounts, spelling aliases (`Priya S` -> `Priya`), and handles duplicates (Meera's review workflow).

---

## Setup & Run Guide

### Prerequisite
Make sure Python 3.10+ and Node.js 18+ are installed.

### Part 1: Backend Setup
1. Open a terminal in `backend/` folder:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install django djangorestframework djangorestframework-simplejwt django-cors-headers psycopg2-binary python-dotenv
   ```
3. Run the database creator (ensures `expenses_db` is created in local PostgreSQL, or issues a warning to default to SQLite):
   ```bash
   python create_db.py
   ```
4. Run migrations:
   ```bash
   python manage.py makemigrations expenses
   ```
   ```bash
   python manage.py migrate
   ```
5. Run unit tests to check math logic:
   ```bash
   python manage.py test expenses
   ```
6. Start Django server:
   ```bash
   python manage.py runserver 8000
   ```

### Part 2: Frontend Setup
1. Open a new terminal in `frontend/` folder:
   ```bash
   cd frontend
   ```
2. Install packages:
   ```bash
   npm install
   ```
3. Run Vite dev server:
   ```bash
   npm run dev
   ```
4. Open the browser at [http://localhost:5173/](http://localhost:5173/).

---

## Credentials & Seeding

For testing ease:
1. Go to the login screen at [http://localhost:5173/login](http://localhost:5173/login).
2. Click the green **"Setup Default Flatmates Environment"** button.
3. This creates **Aisha, Rohan, Priya, Meera, Sam, Dev** with password `Password123`, assigns their correct billing timelines, creates the `Flatmates` group, and automatically logs in as Aisha!
