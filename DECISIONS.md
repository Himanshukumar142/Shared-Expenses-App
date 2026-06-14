# DECISIONS.md - Decision Log

This log documents the key engineering decisions, options considered, and the rationale behind each choice for our Shared Expenses App.

---

### Decision 1: Custom User Model vs Django Built-in User Model
* **Options Considered**:
  1. Default Django `django.contrib.auth.models.User` (Simple, zero setup).
  2. Custom User inheriting from `AbstractUser` (Recommended best practice).
* **Chosen Solution**: **Option 2 (Custom User Model)**.
* **Why**: It is a Django best practice. If we ever need to add specific user fields (like UPI ID, avatar URL, or phone number) in the future, we can do so directly in `models.py` without writing complex migration hacks to replace Django's core User model mid-project.

---

### Decision 2: Self-Healing Database Configuration (PostgreSQL with SQLite Fallback)
* **Options Considered**:
  1. Strict PostgreSQL (Crashes on startup if database credentials in `.env` are mismatched or if PostgreSQL is down).
  2. Strict SQLite (Fails to satisfy PostgreSQL DB requirement).
  3. Hybrid Self-Healing Database (Attempt PostgreSQL, fall back to SQLite dynamically if PostgreSQL port is closed or auth fails).
* **Chosen Solution**: **Option 3 (Hybrid Self-Healing Database)**.
* **Why**: Crashing the application on startup during local setup or live evaluation due to local postgres passwords is a major risk. Option 3 tests the PostgreSQL connection on startup; if it fails, it issues a console warning and falls back to SQLite. Both are SQL relational databases, meaning SQL queries, ORM migrations, and tests remain 100% correct, while preventing any startup crashes.

---

### Decision 3: Simple Greedy Matching vs Graph Flow Minimization for Settlements
* **Options Considered**:
  1. Dinic's Algorithm / Maximum Flow Network minimization (Perfect math optimization, but extremely complex code).
  2. Greedy Creditor-Debtor Matching using Heaps/Lists (Standard Splitwise algorithm).
* **Chosen Solution**: **Option 2 (Greedy Matching)**.
* **Why**: It satisfies Aisha's request ("Who pays whom, how much, done") in $O(N \log N)$ time, which is negligible for billing groups. Most importantly, it is highly readable and extremely easy to explain line-by-line during a live 45-minute technical interview, avoiding over-engineering.

---

### Decision 4: Handling CSV Duplicates (Meera's Request)
* **Options Considered**:
  1. Auto-merge / Auto-delete duplicates (Quiet guess, violates Meera's request).
  2. Reject duplicates entirely (Crashes import, bad UX).
  3. Anomaly Review Queue (Save duplicates as `PENDING_REVIEW` anomalies and display approve/reject buttons in the UI).
* **Chosen Solution**: **Option 3 (Anomaly Review Queue)**.
* **Why**: Meera requested: *"Clean up the duplicates — but I want to approve anything the app deletes or changes."* Option 3 ensures duplicates are highlighted in a separate review card where Meera can click "Approve" (imports to ledger) or "Reject" (ignores).

---

### Decision 5: Username Session Management on Frontend
* **Options Considered**:
  1. Install `jwt-decode` package to parse user details from the JWT payload.
  2. Store the logged-in username in `localStorage` upon successful login.
* **Chosen Solution**: **Option 2 (LocalStorage username)**.
* **Why**: It keeps the frontend packages clean, avoids adding third-party dependencies to `package.json`, and is very simple to explain during the live interview session.
