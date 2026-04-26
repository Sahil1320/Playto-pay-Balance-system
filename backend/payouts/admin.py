from django.contrib import admin
from .models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyKey


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'email', 'created_at']
    search_fields = ['business_name', 'email']
    readonly_fields = ['id', 'created_at']


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['account_holder_name', 'merchant', 'ifsc_code', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['account_holder_name', 'merchant__business_name']


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'entry_type', 'amount_paise', 'description', 'created_at']
    list_filter = ['entry_type', 'merchant']
    search_fields = ['description']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ['id', 'merchant', 'amount_paise', 'status', 'attempts', 'created_at']
    list_filter = ['status', 'merchant']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ['key', 'merchant', 'response_status', 'created_at']
    list_filter = ['merchant']
    readonly_fields = ['id', 'created_at']
