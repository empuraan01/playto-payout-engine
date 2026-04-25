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