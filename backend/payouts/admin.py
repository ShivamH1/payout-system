from django.contrib import admin
from .models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyRecord

@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'created_at']
    search_fields = ['name', 'email']

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['account_holder_name', 'ifsc_code', 'merchant', 'is_active']
    list_filter = ['is_active']

@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'entry_type', 'amount_paise', 'description', 'created_at']
    list_filter = ['entry_type']
    search_fields = ['description']

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ['id', 'merchant', 'amount_paise', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['id']

@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'idempotency_key', 'response_status_code', 'expires_at']
    list_filter = ['expires_at']