from rest_framework import serializers
from .models import Merchant, BankAccount, LedgerEntry, Payout


class BankAccountSerializer(serializers.ModelSerializer):
    masked_account = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = [
            'id', 'account_holder_name', 'masked_account',
            'ifsc_code', 'is_primary', 'created_at'
        ]

    def get_masked_account(self, obj):
        return 'X' * (len(obj.account_number) - 4) + obj.account_number[-4:]


class MerchantSerializer(serializers.ModelSerializer):
    bank_accounts = BankAccountSerializer(many=True, read_only=True)

    class Meta:
        model = Merchant
        fields = ['id', 'business_name', 'email', 'bank_accounts', 'created_at']


class LedgerEntrySerializer(serializers.ModelSerializer):
    amount_rupees = serializers.SerializerMethodField()

    class Meta:
        model = LedgerEntry
        fields = [
            'id', 'entry_type', 'amount_paise', 'amount_rupees',
            'description', 'reference_id', 'created_at'
        ]

    def get_amount_rupees(self, obj):
        return f"₹{obj.amount_paise / 100:,.2f}"


class PayoutSerializer(serializers.ModelSerializer):
    amount_rupees = serializers.SerializerMethodField()
    bank_account_detail = BankAccountSerializer(source='bank_account', read_only=True)

    class Meta:
        model = Payout
        fields = [
            'id', 'merchant', 'bank_account', 'bank_account_detail',
            'amount_paise', 'amount_rupees', 'status',
            'attempts', 'last_attempted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'merchant', 'status', 'attempts', 'last_attempted_at', 'created_at', 'updated_at']

    def get_amount_rupees(self, obj):
        return f"₹{obj.amount_paise / 100:,.2f}"


class PayoutCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a payout request.
    Validates amount and bank account ownership.
    """
    amount_paise = serializers.IntegerField(min_value=100, help_text="Amount in paise. Minimum ₹1 (100 paise).")
    bank_account_id = serializers.UUIDField()

    def validate_amount_paise(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

    def validate_bank_account_id(self, value):
        merchant = self.context.get('merchant')
        if not merchant:
            raise serializers.ValidationError("Merchant context required.")
        try:
            BankAccount.objects.get(id=value, merchant=merchant)
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError(
                "Bank account not found or does not belong to this merchant."
            )
        return value


class BalanceSerializer(serializers.Serializer):
    """Read-only serializer for merchant balance."""
    available_balance_paise = serializers.IntegerField()
    held_balance_paise = serializers.IntegerField()
    total_credits_paise = serializers.IntegerField()
    total_debits_paise = serializers.IntegerField()
    available_balance_rupees = serializers.CharField()
    held_balance_rupees = serializers.CharField()


class MerchantRegistrationSerializer(serializers.Serializer):
    """Serializer for merchant registration."""
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    business_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
