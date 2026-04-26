# Playto Pay — Deep Dive Explainer

This document breaks down the core architecture, technical decisions, and edge cases handled in the Playto Pay Payout Engine assignment.

## 1. Core Architecture & Tech Stack

The application is built to handle financial transactions safely, ensuring no money is lost, double-spent, or incorrectly calculated.

- **Frontend:** React + Tailwind CSS + Vite (Single Page Application)
- **Backend:** Django + Django REST Framework (DRF)
- **Database:** PostgreSQL (for ACID compliance and row-level locking)
- **Background Worker:** Celery + Redis (to handle asynchronous bank settlement simulations)

## 2. Immutable Ledger vs Static Balance

The most critical design decision in this system is **how balance is calculated**.

Instead of having a `balance` field on the `Merchant` model (which is prone to race conditions and audit nightmares), the system uses an **Immutable Ledger**.

- Every financial action (credit, payout hold, payout failure, payout release) is recorded as a `LedgerEntry`.
- The current balance is calculated on-the-fly by summing up all ledger entries for a merchant:
  `Balance = sum(amount where type=CREDIT or RELEASE) - sum(amount where type=DEBIT or HOLD)`
- **Why?** It creates a perfect audit trail. If the system crashes, no money is lost. We can always rebuild the exact balance by re-summing the ledger.

## 3. Handling Money Safely (The Paise/Cent Rule)

Floating-point numbers (like `150.55`) introduce precision errors in programming languages. E.g., `0.1 + 0.2 = 0.30000000000000004`.

- To fix this, the database stores all money as **integers** in the lowest denomination (Paise).
- ₹50,000 is stored in the database as `5000000` paise.
- The frontend converts it back to Rupees for display. The backend strictly computes using integers.

## 4. Race Conditions & Concurrency (The Double Spend Problem)

Imagine a merchant has exactly ₹10,000. They click the "Withdraw ₹10,000" button twice very fast. Two API requests hit the server at the exact same millisecond.

If we don't handle this, both requests check the balance, both see ₹10,000, and both approve the payout. The merchant just withdrew ₹20,000 from a ₹10,000 balance!

**How we solved this:**
We use Database-Level Locking (`SELECT FOR UPDATE`).
```python
with transaction.atomic():
    # This locks the merchant's ledger rows. The second request MUST wait here
    # until the first request finishes processing and updates the balance.
    LedgerEntry.objects.filter(merchant=merchant).select_for_update()
    
    balance = calculate_balance()
    if balance >= requested_amount:
        # Create payout and deduct balance
```

## 5. Idempotency (Handling Network Drops)

What happens if the merchant submits a payout, the server processes it, but the merchant's internet drops before they get the success response? The merchant might think it failed and click "Withdraw" again.

**How we solved this:**
- The frontend generates a unique `Idempotency-Key` (a UUID) for every form submission.
- The backend checks if this key already exists in the `IdempotencyKey` table.
- If it's a **new key**, the server processes the payout, saves the final JSON response in the table, and returns it.
- If it's an **existing key**, the server skips processing and simply returns the cached JSON response. The merchant safely gets their confirmation without double-charging.

## 6. Asynchronous Bank Settlement (Celery)

Real-world bank payouts are not instant. They require sending a request to a bank API (like ICICI or Razorpayx) and waiting for a webhook or status update.

- When a payout is requested, it is immediately marked as `PENDING`, and a `HOLD` ledger entry is created to reserve the funds.
- A Celery task is dispatched in the background to simulate the bank.
- The task simulates 3 scenarios:
  1. **Success (70%):** Bank accepts. Status becomes `COMPLETED`. The `HOLD` becomes a permanent `DEBIT`.
  2. **Failure (20%):** Bank rejects. Status becomes `FAILED`. A `RELEASE` ledger entry is created to give the money back to the merchant's available balance.
  3. **Stuck/Timeout (10%):** Bank doesn't respond. The system has a `celery_beat` cron job that runs every 15 seconds to find stuck payouts and retry them automatically.

## 7. Render.com Free Tier Optimizations

To deploy this complex stack completely for free:
- The React App is deployed as a Free Static Site.
- The PostgreSQL and Redis databases use Render's Free tier.
- Render's free tier doesn't allow "Background Workers". To bypass this, the Django Web Service was configured to run **both** Gunicorn (the web server) and Celery (the background worker) inside a single container using a custom `start.sh` script. This perfectly fits the free tier limitations while keeping the architecture intact.
