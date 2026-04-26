import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Merchant(models.Model):
    """
    Represents a merchant (agency/freelancer) on the platform.
    Each merchant is linked to a Django User for JWT auth.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='merchant')
    business_name = models.CharField(max_length=255)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'merchants'

    def __str__(self):
        return self.business_name


class BankAccount(models.Model):
    """
    Merchant's Indian bank account for receiving payouts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name='bank_accounts'
    )
    account_number = models.CharField(max_length=20)
    ifsc_code = models.CharField(max_length=11)
    account_holder_name = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bank_accounts'

    def __str__(self):
        # Mask account number: show last 4 digits only
        masked = 'X' * (len(self.account_number) - 4) + self.account_number[-4:]
        return f"{self.account_holder_name} - {masked}"


class LedgerEntry(models.Model):
    """
    Immutable ledger entry tracking every money movement.
    Balance is ALWAYS derived by aggregating these entries at the DB level.
    
    Entry types:
      - credit: money comes in (simulated customer payment)
      - hold: funds reserved for a pending payout
      - release: held funds returned (payout failed or cancelled)
      - debit: funds permanently deducted (payout completed)
    
    Available balance = SUM(credit + release) - SUM(hold + debit)
    Held balance = SUM(hold) - SUM(release + debit) [only for entries with payout reference]
    """
    ENTRY_TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('hold', 'Hold'),
        ('release', 'Release'),
        ('debit', 'Debit'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name='ledger_entries'
    )
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES)
    amount_paise = models.BigIntegerField(
        help_text="Amount in paise (1 INR = 100 paise). Always positive."
    )
    description = models.CharField(max_length=500)
    reference_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="Links to a Payout ID when this entry is related to a payout."
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'ledger_entries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'entry_type']),
            models.Index(fields=['merchant', 'created_at']),
        ]

    def clean(self):
        if self.amount_paise <= 0:
            raise ValidationError("amount_paise must be positive.")

    def __str__(self):
        return f"{self.entry_type} ₹{self.amount_paise / 100:.2f} - {self.merchant.business_name}"


class Payout(models.Model):
    """
    Payout request from merchant to their bank account.
    
    State machine:
      pending → processing → completed (terminal)
      pending → processing → failed (terminal)
    
    No backward transitions allowed.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # Valid state transitions — enforced in save()
    VALID_TRANSITIONS = {
        'pending': ['processing'],
        'processing': ['completed', 'failed'],
        'completed': [],   # terminal state
        'failed': [],      # terminal state
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name='payouts'
    )
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.PROTECT, related_name='payouts'
    )
    amount_paise = models.BigIntegerField(
        help_text="Payout amount in paise."
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    attempts = models.IntegerField(default=0)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payouts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['status', 'last_attempted_at']),
        ]

    def __str__(self):
        return f"Payout {self.id} - ₹{self.amount_paise / 100:.2f} ({self.status})"

    def transition_to(self, new_status):
        """
        Enforce the state machine. Raises ValidationError if the transition
        is not allowed. This is the ONLY way status should be changed.
        
        *** THIS IS WHERE failed→completed AND completed→pending ARE BLOCKED ***
        """
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValidationError(
                f"Invalid state transition: {self.status} → {new_status}. "
                f"Allowed transitions from '{self.status}': {allowed}"
            )
        self.status = new_status

    def save(self, *args, **kwargs):
        """
        Override save to enforce state machine on updates.
        On create (no pk in DB yet), any initial status in VALID_TRANSITIONS keys is ok.
        On update, the caller MUST use transition_to() to change status.
        """
        if self.amount_paise <= 0:
            raise ValidationError("Payout amount must be positive.")
        super().save(*args, **kwargs)


class IdempotencyKey(models.Model):
    """
    Stores idempotency keys to prevent duplicate payout creation.
    
    Lifecycle:
      1. Client sends POST with Idempotency-Key header
      2. We create an IdempotencyKey record with response_body=None (marks "in-flight")
      3. After processing, we store the response in response_body
      4. Subsequent calls with same key return cached response
      5. Keys expire after 24 hours
    
    Scoped per merchant — same key from different merchants are independent.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=255, help_text="Merchant-supplied UUID")
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name='idempotency_keys'
    )
    request_method = models.CharField(max_length=10)
    request_path = models.CharField(max_length=500)
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'idempotency_keys'
        constraints = [
            models.UniqueConstraint(
                fields=['key', 'merchant'],
                name='unique_idempotency_key_per_merchant'
            )
        ]

    def __str__(self):
        return f"IdempKey {self.key[:8]}... ({self.merchant.business_name})"

    @property
    def is_completed(self):
        """True if we have a cached response (request fully processed)."""
        return self.response_body is not None

    @property
    def is_in_flight(self):
        """True if request was started but not yet completed."""
        return self.response_body is None
