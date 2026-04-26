# EXPLAINER.md

## 1. The Ledger

```python
@staticmethod
def calculateBalance(merchant_id):
    result = LedgerEntry.objects.filter(
        merchant_id=merchant_id
    ).aggregate(
        available=Sum(
            Case(
                When(entry_type=LedgerEntry.EntryType.CREDIT, then=F("amount_paise")),
                When(entry_type=LedgerEntry.EntryType.DEBIT_RELEASE, then=F("amount_paise")),
                When(entry_type=LedgerEntry.EntryType.DEBIT_HOLD, then=Value(-1) * F("amount_paise")),
                default=Value(0),
                output_field=BigIntegerField(),
            )
        ),
        held=Sum(
            Case(
                When(entry_type=LedgerEntry.EntryType.DEBIT_HOLD, then=F("amount_paise")),
                When(entry_type=LedgerEntry.EntryType.DEBIT_CONFIRM, then=Value(-1) * F("amount_paise")),
                When(entry_type=LedgerEntry.EntryType.DEBIT_RELEASE, then=Value(-1) * F("amount_paise")),
                default=Value(0),
                output_field=BigIntegerField(),
            )
        ),
    )
    return {
        "available_balance": result["available"] or 0,
        "held_balance": result["held"] or 0,
    }
```

So basically I had 2 options to design the ledger. Option 1 was to have 2 types of entries: credits and debits, where debits would have an additional status of held/confirmed/released. Option 2 was to have 4 types: credit, debit_hold, debit_confirm, debit_release.

The main reason I chose Option 2 is because traditionally in a ledger, each entry is unique, can't be tampered, and works on an append-only basis. Going with Option 1 meant I had to find the rows first which had debit, and then update its status. 2 drawbacks I saw in this were that you had to "update" the row, and this would mean 2 operations (a filter and an update), which I felt might be slower in, let's say, a table with 1 million ledger entries. This problem would kind of mutate when I had to tackle the balance calculation as well.


## 5. The AI Audit
 
### Catch 1: CASCADE and SET_NULL on financial ledger foreign keys
 
**The bug:** AI generated the ledger model with `on_delete=models.CASCADE` on the merchant foreign key and `on_delete=models.SET_NULL` on the payout foreign key.
 
**What AI gave me:**
```python
merchant = models.ForeignKey(
    "merchants.Merchant",
    on_delete=models.CASCADE,
    related_name="ledger_entries",
)
payout = models.ForeignKey(
    "payouts.Payout",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="ledger_entries",
)
```
 
**What I caught:** CASCADE means deleting a merchant wipes out their entire financial history every credit, every debit, gone silently. In a money moving system that's catastrophic. You can never reconstruct what happened. SET_NULL on the payout FK is similarly bad if a payout gets deleted, the ledger entries that record the hold and release lose their link to what caused them. The audit trail is broken.
 
**What I replaced it with:**
```python
merchant = models.ForeignKey(
    "merchants.Merchant",
    on_delete=models.PROTECT,
    related_name="ledger_entries",
)
payout = models.ForeignKey(
    "payouts.Payout",
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name="ledger_entries",
)
```
 
PROTECT prevents deletion entirely if there are linked ledger entries. The database raises an error. A merchant or payout with financial history should never be deletable since that's a data integrity guarantee. An additional scope would be add a control variable to the merchant model that decides whether or not that merchant exists or not, or maybe a periodic cleanup after that financial year if we are talking real world (not sure if this is legal or not!).


### Catch 2: Unsafe F() multiplication in balance aggregation (less concerning, more for safety)
 
**The bug:** AI wrote the balance calculation using raw integer multiplication with an F expression.
 
**What AI gave me:**
```python
When(
    entry_type=LedgerEntry.EntryType.DEBIT_HOLD,
    then=-1 * models.F("amount_paise"),
)
```
 
**What I caught:** Multiplying a plain Python integer directly with `models.F()` can behave unpredictably. The expression isn't wrapped in Django's expression API, so the ORM may not resolve it correctly in all cases.
 
**What I replaced it with:**
```python
When(
    entry_type=LedgerEntry.EntryType.DEBIT_HOLD,
    then=Value(-1) * F("amount_paise"),
)
```
 
Wrapping `-1` in `Value()` keeps the entire expression within Django's ORM expression tree, so PostgreSQL gets a clean, predictable query every time.

### Catch 3: Unnecessary deserialization before idempotency short-circuit

**The bug:** AI extracted all request fields before checking if the idempotency key already existed.

**What AI gave me:**
```python
merchant_id = serializer.validated_data["merchant_id"]
amount_paise = serializer.validated_data["amount_paise"]
bank_account_id = serializer.validated_data["bank_account_id"]

# --- Step 2: Check idempotency key ---
existing_key = IdempotencyKey.objects.filter(
    key=idempotency_key,
    merchant_id=merchant_id,
    created_at__gte=timezone.now() - timedelta(hours=24),
).first()

if existing_key:
    return Response(existing_key.response_body, status=existing_key.response_status)
```

**What I caught:** If the idempotency key already exists, we return the cached response immediately. We only need `merchant_id` for the lookup since keys are scoped per merchant. Extracting `amount_paise` and `bank_account_id` before the check is wasted work that gets thrown away on every duplicate request.

**What I replaced it with:**
```python
merchant_id = serializer.validated_data["merchant_id"]

# --- Step 2: Check idempotency key ---
existing_key = IdempotencyKey.objects.filter(
    key=idempotency_key,
    merchant_id=merchant_id,
    created_at__gte=timezone.now() - timedelta(hours=24),
).first()

if existing_key:
    return Response(existing_key.response_body, status=existing_key.response_status)

# Only extract these after idempotency check passes
amount_paise = serializer.validated_data["amount_paise"]
bank_account_id = serializer.validated_data["bank_account_id"]
```

Not a correctness bug, but in a payment system's hot path where retries are common, every unnecessary operation before the short-circuit adds up.
