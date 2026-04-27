from django.db import models
import uuid

class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'merchants'

    def __str__(self):
        return self.name


class BankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='bank_accounts')
    account_number = models.CharField(max_length=20)
    ifsc_code = models.CharField(max_length=11)
    account_holder_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bank_accounts'

    def __str__(self):
        return f"{self.account_holder_name} - {self.ifsc_code}"


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = 'credit', 'Credit'
        DEBIT = 'debit', 'Debit'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name='ledger_entries')
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    amount_paise = models.BigIntegerField()
    description = models.CharField(max_length=500)
    payout = models.ForeignKey('Payout', null=True, blank=True, on_delete=models.PROTECT, related_name='ledger_entries')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ledger_entries'
        indexes = [
            models.Index(fields=['merchant', 'created_at']),
        ]

    def __str__(self):
        return f"{self.entry_type}: {self.amount_paise} paise - {self.description}"


class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name='payouts')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT)
    amount_paise = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    idempotency_key = models.CharField(max_length=255)
    attempt_count = models.IntegerField(default=0)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payouts'
        constraints = [
            models.UniqueConstraint(
                fields=['merchant', 'idempotency_key'],
                name='unique_merchant_idempotency_key'
            )
        ]
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['merchant', 'created_at']),
        ]

    def __str__(self):
        return f"Payout {self.id} - {self.status}"


class IdempotencyRecord(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE)
    idempotency_key = models.CharField(max_length=255)
    response_status_code = models.IntegerField()
    response_body = models.JSONField()
    payout = models.ForeignKey(Payout, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'idempotency_records'
        constraints = [
            models.UniqueConstraint(
                fields=['merchant', 'idempotency_key'],
                name='unique_idempotency_record'
            )
        ]
        indexes = [
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"IdempotencyRecord {self.idempotency_key}"