from django.contrib import admin
from .models import (
    Institution,
    UserProfile,
    Asset,
    Donation,
    Receipt,
    Expense,
    Event,
    Maintenance,
    AuditLog,
)

admin.site.register(Institution)
admin.site.register(UserProfile)
admin.site.register(Asset)
admin.site.register(Donation)
admin.site.register(Receipt)
admin.site.register(Expense)
admin.site.register(Event)
admin.site.register(Maintenance)
admin.site.register(AuditLog)

# Register your models here.
