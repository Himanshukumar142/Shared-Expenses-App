# AI_USAGE.md - AI Collaboration Log

This log documents the collaboration between the developer and the AI coding assistant (Gemini 3.5 Flash via Antigravity IDE) to build the Shared Expenses App.

---

### AI Tools Used
* **AI Collaborator**: Gemini 3.5 Flash (High) via Antigravity IDE.
* **Operating Shell**: Windows PowerShell.

---

### Key Prompts
1. *"Build a Shared Expenses App using Django REST Framework and React... explain code in simple English and interview questions related to it..."*
2. *"Complete this project without any mistake and any skip."*
3. *"Check the user's AppData/Roaming folder for pgAdmin config database settings."*

---

### Concrete Cases of AI Errors & Corrections

We encountered and fixed three specific developer bugs during implementation:

#### Case 1: Decimal and Float Multiplication TypeError
* **The Error**: The AI generated a save hook in `models.py` containing:
  `self.normalized_amount_inr = round(self.amount * self.exchange_rate, 2)`
  Because `amount` is a `DecimalField` and `exchange_rate` defaulted to `1.000000` (treated as a Python float), Django threw:
  `TypeError: unsupported operand type(s) for *: 'decimal.Decimal' and 'float'`
* **How it was caught**: Running automated unit tests (`python manage.py test expenses`) failed during expense creation checks.
* **The Correction**: We wrapped both variables in the `Decimal` cast in both `Expense.save()` and `ExpenseSplit.save()` hooks:
  `self.normalized_amount_inr = round(Decimal(str(self.amount)) * Decimal(str(self.exchange_rate)), 2)`

#### Case 2: Missing `Q` import in `tests.py`
* **The Error**: The AI used the Django `Q` object to filter temporal memberships in `tests.py` but failed to import it.
* **How it was caught**: Running tests failed with a compilation error:
  `NameError: name 'Q' is not defined`
* **The Correction**: We modified the imports at the top of `backend/expenses/tests.py` to include:
  `from django.db.models import Q`

#### Case 3: Tailwind CSS v4 PostCSS Plugin Conflict
* **The Error**: The AI generated a standard PostCSS configuration referencing `'tailwindcss': {}`.
* **How it was caught**: Running `npm run build` failed during the CSS compilation step with an error:
  `Error: [postcss] It looks like you're trying to use tailwindcss directly as a PostCSS plugin... you'll need to install @tailwindcss/postcss and update your PostCSS configuration.`
* **The Correction**: We installed `@tailwindcss/postcss` via npm and updated `postcss.config.js` to reference `'@tailwindcss/postcss': {}`.
