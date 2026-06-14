from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

# ==============================================================================
# USER MODEL
# ==============================================================================
class User(AbstractUser):
    """
    Why this exists: 
    We inherit from AbstractUser so that we have built-in authentication, 
    passwords hashing, and JWT support out of the box, while allowing future
    customizations if needed.
    """
    def __str__(self):
        return self.username


# ==============================================================================
# GROUP MODEL
# ==============================================================================
class Group(models.Model):
    """
    Why this exists:
    To represent different flat expenses groups or specific trips (like 'Flatmates' or 'Goa Trip').
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ==============================================================================
# GROUP MEMBER (MEMBERSHIP OVER TIME)
# ==============================================================================
class GroupMember(models.Model):
    """
    Why this exists:
    To address Sam's and Meera's requests. We track who is active in a group 
    at any given time.
    - joined_at: when the member joined.
    - left_at: when the member left (can be null if they are still active).
    An expense on date D will only split among members active on D (joined_at <= D <= left_at).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members')
    joined_at = models.DateField()
    left_at = models.DateField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'group', 'joined_at') # Prevent duplicate joins on same date

    def clean(self):
        # Validate that left_at is after joined_at
        if self.left_at and self.left_at < self.joined_at:
            raise ValidationError("Left date cannot be before joined date.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        left_str = f" to {self.left_at}" if self.left_at else " (Active)"
        return f"{self.user.username} in {self.group.name} from {self.joined_at}{left_str}"


# ==============================================================================
# EXPENSE MODEL
# ==============================================================================
class Expense(models.Model):
    """
    Why this exists:
    Stores the core expense details. To address Priya's request, we preserve
    the original currency and amount while storing the exchange_rate and 
    normalized INR amount so that we can easily calculate total balances.
    """
    SPLIT_TYPES = (
        ('equal', 'Equal'),
        ('exact', 'Exact Amount'),
        ('percentage', 'Percentage'),
        ('share', 'Share Ratio'),
    )

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Store original inputs as Priya requested
    amount = models.DecimalField(max_digits=12, decimal_places=4)
    currency = models.CharField(max_length=10, default='INR')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6, default=1.000000)
    
    # Auto-calculated field to simplify balance sums in a single currency (INR)
    normalized_amount_inr = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_expenses')
    expense_date = models.DateField()
    split_type = models.CharField(max_length=15, choices=SPLIT_TYPES, default='equal')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Convert both to Decimal to prevent float vs Decimal type errors
        from decimal import Decimal
        self.normalized_amount_inr = round(Decimal(str(self.amount)) * Decimal(str(self.exchange_rate)), 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.amount} {self.currency} (INR {self.normalized_amount_inr})"


# ==============================================================================
# EXPENSE SPLIT DETAILS
# ==============================================================================
class ExpenseSplit(models.Model):
    """
    Why this exists:
    Stores how much a specific user owes for an expense. 
    This meets Rohan's request for full traceability ("Why do I owe X?").
    We can fetch all splits for a user to explain their exact balance.
    """
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='splits')
    
    # The calculated share amount in the expense's original currency
    amount = models.DecimalField(max_digits=12, decimal_places=4)
    # The calculated share amount converted to normalized INR for balance calculations
    amount_inr = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    
    # Storing the ratio/percentage used for split verification if needed
    percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    share = models.IntegerField(blank=True, null=True) # Weight if split_type is 'share'

    def save(self, *args, **kwargs):
        # Convert both to Decimal to prevent float vs Decimal type errors
        from decimal import Decimal
        self.amount_inr = round(Decimal(str(self.amount)) * Decimal(str(self.expense.exchange_rate)), 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} owes {self.amount} {self.expense.currency} for {self.expense.title}"


# ==============================================================================
# SETTLEMENT (RECORD OF PAYMENT)
# ==============================================================================
class Settlement(models.Model):
    """
    Why this exists:
    To record payments where one user directly settles their debt with another.
    This fulfills Aisha's goal of simplified balances and recording payments.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='settlements')
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='settled_payments')
    payee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_payments')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2) # Standardized to INR
    currency = models.CharField(max_length=10, default='INR')
    settled_at = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payer.username} paid {self.payee.username} INR {self.amount}"


# ==============================================================================
# IMPORT JOB (CSV UPLOAD TRACKER)
# ==============================================================================
class ImportJob(models.Model):
    """
    Why this exists:
    To track the import status of a uploaded CSV file.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    )
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    file_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Job #{self.id} ({self.file_name}) - {self.status}"


# ==============================================================================
# IMPORT ANOMALY LOG (APPROVAL WORKFLOW)
# ==============================================================================
class ImportAnomaly(models.Model):
    """
    Why this exists:
    Fulfills Meera's request. We flag duplicate or problematic records 
    in the database and let the user approve or reject them manually.
    """
    SEVERITY_CHOICES = (
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'), # Error means the row cannot be imported automatically
    )
    STATUS_CHOICES = (
        ('pending_review', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    import_job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name='anomalies')
    row_number = models.IntegerField()
    anomaly_type = models.CharField(max_length=100)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    action_taken = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_review')
    
    # Store the row's original CSV cells as JSON so it can be re-processed/edited if approved
    row_data = models.JSONField()

    def __str__(self):
        return f"Row {self.row_number} [{self.anomaly_type}] - {self.status}"
