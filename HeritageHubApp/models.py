from django.db import models
from django.contrib.auth.models import User


class Institution(models.Model):
    INSTITUTION_TYPES = [
        ("Temple", "Temple"),
        ("Trust", "Religious Trust"),
        ("Heritage", "Cultural Heritage Institution"),
    ]

    APPROVAL_STATUS = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    name = models.CharField(max_length=200)
    institution_type = models.CharField(
        max_length=50,
        choices=INSTITUTION_TYPES
    )
    address = models.TextField()
    registration_certificate = models.FileField(
        upload_to="institution_documents/",
        blank=True,
        null=True
    )
    pan = models.CharField(max_length=20, blank=True)
    authorized_representative = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS,
        default="Pending"
    )
    registered_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("Devotee", "Devotee"),
        ("Staff", "Staff"),
        ("Trustee", "Trustee / Administrator"),
        ("Admin", "System Administrator"),
    ]
    APPROVAL_STATUS = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )
    phone = models.CharField(max_length=20, blank=True)
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS,
        default="Approved"
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Asset(models.Model):
    ASSET_TYPES = [
        ("Movable", "Movable"),
        ("Immovable", "Immovable"),
    ]

    CONDITION_CHOICES = [
        ("Excellent", "Excellent"),
        ("Good", "Good"),
        ("Needs Maintenance", "Needs Maintenance"),
        ("Damaged", "Damaged"),
    ]

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="assets"
    )
    name = models.CharField(max_length=200)
    asset_type = models.CharField(
        max_length=20,
        choices=ASSET_TYPES
    )
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    photograph = models.ImageField(
        upload_to="assets/",
        blank=True,
        null=True
    )
    current_valuation = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )
    condition = models.CharField(
        max_length=30,
        choices=CONDITION_CHOICES
    )
    location = models.CharField(max_length=200)
    date_acquired = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name


class Donation(models.Model):
    DONATION_TYPES = [
        ("Online", "Online"),
        ("Cash", "Cash"),
    ]

    PAYMENT_STATUS = [
        ("Pending", "Pending"),
        ("Success", "Success"),
        ("Failed", "Failed"),
    ]

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="donations"
    )
    donor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donations"
    )
    donor_name = models.CharField(max_length=150)
    donor_email = models.EmailField(blank=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    donation_type = models.CharField(
        max_length=20,
        choices=DONATION_TYPES
    )
    purpose = models.CharField(max_length=200)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="Pending"
    )
    transaction_id = models.CharField(
        max_length=100,
        blank=True
    )
    donation_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.donor_name} - ₹{self.amount}"


class Receipt(models.Model):
    donation = models.OneToOneField(
        Donation,
        on_delete=models.CASCADE,
        related_name="receipt"
    )
    receipt_number = models.CharField(
        max_length=50,
        unique=True
    )
    generated_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.receipt_number


class Expense(models.Model):
    EXPENSE_STATUS = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="expenses"
    )
    donation = models.ForeignKey(
        Donation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    expense_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=EXPENSE_STATUS,
        default="Pending"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_expenses"
    )

    def __str__(self):
        return f"{self.title} - ₹{self.amount}"


class Event(models.Model):
    EVENT_STATUS = [
        ("Scheduled", "Scheduled"),
        ("Ongoing", "Ongoing"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="events"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField()
    location = models.CharField(max_length=200)
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    status = models.CharField(
        max_length=20,
        choices=EVENT_STATUS,
        default="Scheduled"
    )

    def __str__(self):
        return self.name


class Maintenance(models.Model):
    MAINTENANCE_STATUS = [
        ("Scheduled", "Scheduled"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="maintenance_records"
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_history"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    scheduled_date = models.DateField()
    completion_date = models.DateField(
        blank=True,
        null=True
    )
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    status = models.CharField(
        max_length=20,
        choices=MAINTENANCE_STATUS,
        default="Scheduled"
    )

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    action = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action}"

# Create your models here.
