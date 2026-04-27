from rest_framework import serializers
from .models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyRecord


class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ['id', 'name', 'email', 'created_at']


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'account_number', 'ifsc_code', 'account_holder_name', 'is_active', 'created_at']


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ['id', 'entry_type', 'amount_paise', 'description', 'created_at']


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            'id', 'amount_paise', 'status', 'bank_account_id',
            'idempotency_key', 'created_at', 'completed_at',
            'failed_at', 'failure_reason', 'attempt_count'
        ]