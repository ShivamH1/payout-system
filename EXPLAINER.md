# EXPLAINER.md

## 1. The Ledger

**Balance calculation query:**

```python
result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
    total_credits=Coalesce(Sum('amount_paise', filter=Q(entry_type='credit')), Value(0)),
    total_debits=Coalesce(Sum('amount_paise', filter=Q(entry_type='debit')), Value(0)),
)
# available = (credits - debits) - held_in_pending_payouts
```

**Why this model:**
We treat the ledger as an immutable, append-only log. Every movement of money is a new row. We never "update" a balance column because a single column is a point-of-failure for auditability. By deriving the balance from the sum of all transactions, we ensure the system is self-documenting. If a merchant disputes their balance, we don't just show them a number; we show them the math.

## 2. The Lock

**Exact code:**

```python
with transaction.atomic():
    # Lock the merchant row to prevent concurrent payout requests
    merchant = Merchant.objects.select_for_update().get(id=merchant_id)
    
    # Calculate balance *after* acquiring the lock
    balance = get_merchant_balance(merchant_id)
    
    if balance['available_paise'] < amount_paise:
        raise InsufficientBalanceError(...)
```

**Database primitive:**
This relies on **`SELECT ... FOR UPDATE`**. It places an exclusive row-level lock on the Merchant record in PostgreSQL. Any other request trying to run `select_for_update()` on the same merchant ID will block at the database level until the first transaction commits or rolls back. This prevents the "double-spend" race condition where two requests see the same balance and both try to withdraw it.

## 3. The Idempotency

**How it knows it has seen a key:**
We check the `IdempotencyRecord` table before doing any work. It's indexed by `(merchant_id, idempotency_key)`. If a record exists, we immediately return the cached response body and status code.

**In-flight race:**
If request A and B arrive at the same millisecond:
1. Both see no `IdempotencyRecord`.
2. Both attempt to process the payout.
3. The `Payout` model has a `UniqueConstraint(fields=['merchant', 'idempotency_key'])`.
4. One request will successfully `Payout.objects.create()`.
5. The other will hit a `django.db.utils.IntegrityError` at the database level.
6. The second request fails safely, while the first completes and stores its result in `IdempotencyRecord` for future retries.

## 4. The State Machine

**Where failed-to-completed is blocked:**

In `payouts/services.py`:
```python
LEGAL_TRANSITIONS = {
    Payout.Status.PENDING: [Payout.Status.PROCESSING],
    Payout.Status.PROCESSING: [Payout.Status.COMPLETED, Payout.Status.FAILED],
}

def transition_payout(payout, new_status):
    allowed = LEGAL_TRANSITIONS.get(payout.status, [])
    if new_status not in allowed:
        raise InvalidStateTransitionError(f"Cannot transition from {payout.status} to {new_status}")
```
Since `Payout.Status.FAILED` is not a key in `LEGAL_TRANSITIONS` (or it would have an empty list), and it certainly isn't an allowed destination from `FAILED`, any attempt to move a failed payout to completed will throw an exception and roll back the transaction.

## 5. The AI Audit

**Example: Wrong Aggregation (NoneType Leak)**

**What AI gave:**
The AI suggested a simple aggregation to find the total credits:
```python
total_credits = LedgerEntry.objects.filter(
    merchant=m, entry_type='credit'
).aggregate(Sum('amount'))['amount__sum']

available = total_credits - held_funds
```

**What I caught:**
In Django, `Sum()` on an empty queryset returns `None`, not `0`. If a new merchant signs up and has 0 credits, `total_credits` becomes `None`. The next line `None - held_funds` throws a `TypeError`, crashing the API instead of returning a "0 balance" error.

**What I replaced it with:**
Wrapped the aggregation in `Coalesce` to force a default of 0 at the database level:
```python
total_credits = LedgerEntry.objects.filter(
    merchant=m, entry_type='credit'
).aggregate(
    res=Coalesce(Sum('amount'), Value(0))
)['res']
```
This ensures we are always doing math with integers, making the balance calculation robust even for brand new accounts.
