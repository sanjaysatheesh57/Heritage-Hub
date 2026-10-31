import uuid
from decimal import Decimal
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib import messages
from datetime import datetime
import io
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.http import HttpResponse, HttpResponseForbidden

from .models import UserProfile, Institution, Donation, Receipt, AuditLog, Asset, Maintenance, Expense, Event


# ──────────────────────────────────────────────
# Access-control decorator for Devotee-only views
# ──────────────────────────────────────────────

def devotee_required(view_func):
    """Ensures the user is authenticated AND has role == 'Devotee'."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return HttpResponseForbidden(
                "<h2>403 — Forbidden</h2>"
                "<p>You do not have a role assigned. Contact the administrator.</p>"
            )
        if profile.role != "Devotee":
            return HttpResponseForbidden(
                "<h2>403 — Forbidden</h2>"
                "<p>This section is reserved for Devotee users only.</p>"
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def trustee_required(view_func):
    """Ensures the user is authenticated, has role == 'Trustee', and approval_status == 'Approved'."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return HttpResponseForbidden(
                "<h2>403 — Forbidden</h2>"
                "<p>You do not have a role assigned. Contact the administrator.</p>"
            )
        if profile.role != "Trustee":
            return HttpResponseForbidden(
                "<h2>403 — Forbidden</h2>"
                "<p>This section is reserved for Trustee users only.</p>"
            )
        if profile.approval_status != "Approved":
            return HttpResponseForbidden(
                "<h2>403 — Forbidden</h2>"
                f"<p>Your Trustee account is currently {profile.approval_status}. Access is restricted until approved by an Administrator.</p>"
            )
        return view_func(request, *args, **kwargs)
    return wrapper



def staff_required(view_func):
    """Ensures the user is authenticated, has role == 'Staff', and approval_status == 'Approved'."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return HttpResponseForbidden(
                "<h2>403 — Forbidden</h2>"
                "<p>You do not have a role assigned. Contact the administrator.</p>"
            )
        if profile.role != "Staff":
            return HttpResponseForbidden(
                "<h2>403 — Forbidden</h2>"
                "<p>This portal is exclusively reserved for Staff / Authorized Personnel.</p>"
            )
        if profile.approval_status != "Approved":
            return HttpResponseForbidden(
                "<h2>403 — Forbidden</h2>"
                f"<p>Your Staff account is currently {profile.approval_status}. Access is restricted until approved by an Administrator.</p>"
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Ensures the user is authenticated AND has role == 'Admin'."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return HttpResponseForbidden(
                "<h2>403 — Forbidden</h2>"
                "<p>You do not have a role assigned. Contact the administrator.</p>"
            )
        if profile.role != "Admin":
            return HttpResponseForbidden(
                "<h2>403 — Forbidden</h2>"
                "<p>This section is reserved for System Administrators only.</p>"
            )
        return view_func(request, *args, **kwargs)
    return wrapper


# ──────────────────────────────────────────────
# Common / public views  (preserved from Stage 1)
# ──────────────────────────────────────────────

def home_view(request):
    return render(request, "common/home.html")


def about_view(request):
    return render(request, "common/about.html")


def contact_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "")
        email = request.POST.get("email", "")
        subject = request.POST.get("subject", "")
        message = request.POST.get("message", "")
        messages.success(
            request,
            f"Thank you, {name}! Your message has been received. "
            "Our team will get back to you shortly.",
        )
        return render(request, "common/contact.html")
    return render(request, "common/contact.html")


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("login")


def login_view(request):
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            if profile.role == "Admin":
                return redirect("admin_dashboard")
            elif profile.role == "Devotee":
                return redirect("devotee_dashboard")
            elif profile.role == "Staff":
                if profile.approval_status == "Approved":
                    return redirect("staff_dashboard")
                else:
                    logout(request)
                    return render(request, "common/login.html", {
                        "error": f"Your Staff account is currently {profile.approval_status}. Access is granted only upon Administrator approval."
                    })
            elif profile.role == "Trustee":
                if profile.approval_status == "Approved":
                    return redirect("trustee_dashboard")
                else:
                    logout(request)
                    return render(request, "common/login.html", {
                        "error": f"Your Trustee account is currently {profile.approval_status}. Access is granted only upon Administrator approval."
                    })
        except UserProfile.DoesNotExist:
            if request.user.is_superuser:
                return redirect("/admin/")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            try:
                profile = UserProfile.objects.get(user=user)
            except UserProfile.DoesNotExist:
                if user.is_superuser:
                    return redirect("/admin/")
                return render(request, "common/login.html", {
                    "error": "No role has been assigned to this user."
                })

            if profile.role == "Admin":
                return redirect("admin_dashboard")
            elif profile.role == "Devotee":
                return redirect("devotee_dashboard")
            elif profile.role == "Staff":
                if profile.approval_status == "Approved":
                    return redirect("staff_dashboard")
                else:
                    logout(request)
                    return render(request, "common/login.html", {
                        "error": f"Your Staff account is currently {profile.approval_status}. Access is granted only upon Administrator approval."
                    })
            elif profile.role == "Trustee":
                if profile.approval_status == "Approved":
                    return redirect("trustee_dashboard")
                else:
                    logout(request)
                    return render(request, "common/login.html", {
                        "error": f"Your Trustee account is currently {profile.approval_status}. Access is granted only upon Administrator approval."
                    })
            else:
                logout(request)
                return render(request, "common/login.html", {
                    "error": f"Role '{profile.role}' is not recognized as a valid application role."
                })

        return render(request, "common/login.html", {
            "error": "Invalid username or password."
        })

    return render(request, "common/login.html")


def register_view(request):
    """
    Public registration portal for Devotee, Trustee, and Staff users.
    Administrative accounts cannot be registered publicly.
    """
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            if profile.role == "Admin":
                return redirect("admin_dashboard")
            elif profile.role == "Devotee":
                return redirect("devotee_dashboard")
            elif profile.role == "Staff":
                return redirect("staff_dashboard")
            elif profile.role == "Trustee":
                return redirect("trustee_dashboard")
        except UserProfile.DoesNotExist:
            if request.user.is_superuser:
                return redirect("/admin/")

    approved_institutions = Institution.objects.filter(approval_status="Approved").order_by("name")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        role = request.POST.get("role", "Devotee").strip()
        institution_id = request.POST.get("institution", "").strip()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        errors = []

        # 1. Validate role (strictly Devotee, Trustee, Staff; reject Admin and anything else)
        if role not in ["Devotee", "Trustee", "Staff"]:
            errors.append("Invalid registration role. Administrative accounts cannot be registered publicly.")

        # 2. Validate institution for Staff
        selected_institution = None
        if role == "Staff":
            if not institution_id or not institution_id.isdigit():
                errors.append("Staff registration requires selecting a valid, approved heritage institution.")
            else:
                selected_institution = Institution.objects.filter(
                    id=int(institution_id),
                    approval_status="Approved"
                ).first()
                if not selected_institution:
                    errors.append("Selected institution is not an approved institution. Staff can only register with approved institutions.")
        else:
            # Devotee and Trustee cannot be assigned an institution during public registration
            selected_institution = None

        # 3. Validate username
        if not username:
            errors.append("Username is required.")
        elif User.objects.filter(username=username).exists():
            errors.append("A user with that username already exists.")

        # 4. Validate passwords
        if not password:
            errors.append("Password is required.")
        elif not password_confirm:
            errors.append("Please confirm your password.")
        elif password != password_confirm:
            errors.append("Passwords do not match.")
        else:
            try:
                validate_password(password)
            except ValidationError as ve:
                for msg in ve.messages:
                    errors.append(msg)

        if errors:
            return render(request, "common/register.html", {
                "errors": errors,
                "approved_institutions": approved_institutions,
                "form_data": {
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": phone,
                    "role": role,
                    "institution_id": institution_id,
                },
            })

        # 5. Determine approval_status and messages based on role
        if role == "Devotee":
            approval_status = "Approved"
            success_msg = "Registration successful. You can now log in."
        elif role == "Trustee":
            approval_status = "Pending"
            success_msg = "Registration submitted. Your Trustee account is pending Administrator approval."
        elif role == "Staff":
            approval_status = "Pending"
            success_msg = "Registration submitted. Your Staff account is pending Administrator approval."

        # 6. Create Django User with hashed password
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # 7. Create UserProfile
        UserProfile.objects.create(
            user=user,
            role=role,
            phone=phone,
            institution=selected_institution,
            approval_status=approval_status,
        )

        # 8. Create AuditLog entry
        AuditLog.objects.create(
            user=user,
            action=f"{role} Registration",
            description=(
                f"New {role} account registered: {username} ({email or 'no email'}). "
                f"Initial status: {approval_status}."
                + (f" Institution: '{selected_institution.name}'." if selected_institution else "")
            ),
        )

        messages.success(request, success_msg)
        return redirect("login")

    return render(request, "common/register.html", {
        "approved_institutions": approved_institutions,
        "form_data": {"role": "Devotee"},
    })


# ──────────────────────────────────────────────
# STAFF / AUTHORIZED PERSONNEL MODULE — views
# ──────────────────────────────────────────────

@staff_required
def staff_dashboard(request):
    """
    Staff operational dashboard:
    Displays institution details, operational summary metrics (cash donations recorded,
    maintenance records), and quick links to record cash donations and maintenance.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "staff/no_institution.html", {})

    cash_donations_qs = Donation.objects.filter(institution=institution, donation_type="Cash")
    total_cash_donations_count = cash_donations_qs.count()
    total_cash_donations_amount = (
        cash_donations_qs.filter(payment_status="Success").aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    recent_donations = cash_donations_qs.select_related("receipt").order_by("-donation_date")[:5]

    maintenance_qs = Maintenance.objects.filter(institution=institution).select_related("asset")
    total_maintenance_count = maintenance_qs.count()
    recent_maintenance = maintenance_qs.order_by("-id")[:5]

    context = {
        "profile": profile,
        "institution": institution,
        "total_cash_donations_count": total_cash_donations_count,
        "total_cash_donations_amount": total_cash_donations_amount,
        "recent_donations": recent_donations,
        "total_maintenance_count": total_maintenance_count,
        "recent_maintenance": recent_maintenance,
    }
    return render(request, "staff/dashboard.html", context)


@staff_required
def staff_donation_list(request):
    """
    List all Cash donations recorded for the Staff member's institution.
    Online donations are strictly excluded from this view.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "staff/no_institution.html", {})

    donations = (
        Donation.objects.filter(institution=institution, donation_type="Cash")
        .select_related("receipt")
        .order_by("-donation_date")
    )
    total_cash_count = donations.count()
    total_cash_amount = (
        donations.filter(payment_status="Success").aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )

    context = {
        "profile": profile,
        "institution": institution,
        "donations": donations,
        "total_cash_count": total_cash_count,
        "total_cash_amount": total_cash_amount,
    }
    return render(request, "staff/donations/list.html", context)


@staff_required
def staff_donation_add(request):
    """
    Cash donation data entry:
    Allows authorized staff to record manual cash offerings received at the temple.
    Automatically assigns institution, donation_type='Cash', payment_status='Success',
    generates an internal cash reference and official receipt, and writes an AuditLog.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "staff/no_institution.html", {})

    if request.method == "POST":
        donor_name = request.POST.get("donor_name", "").strip()
        donor_email = request.POST.get("donor_email", "").strip()
        amount_raw = request.POST.get("amount", "").strip()
        purpose = request.POST.get("purpose", "").strip()

        errors = []
        if not donor_name:
            errors.append("Donor full name is required.")

        amount = None
        if not amount_raw:
            errors.append("Donation amount is required.")
        else:
            try:
                amount = Decimal(amount_raw)
                if amount <= Decimal("0.00"):
                    errors.append("Donation amount must be greater than zero.")
            except Exception:
                errors.append("Please enter a valid numeric donation amount.")

        if donor_email:
            try:
                validate_email(donor_email)
            except ValidationError:
                errors.append("Please provide a valid donor email address or leave it blank.")

        if not purpose:
            purpose = "General Temple Offering"

        if errors:
            context = {
                "profile": profile,
                "institution": institution,
                "errors": errors,
                "form_data": {
                    "donor_name": donor_name,
                    "donor_email": donor_email,
                    "amount": amount_raw,
                    "purpose": purpose,
                },
            }
            return render(request, "staff/donations/add.html", context)

        # Generate unique cash transaction reference
        cash_ref = f"CASH-{uuid.uuid4().hex[:8].upper()}"

        donation = Donation.objects.create(
            institution=institution,
            donor=None,
            donor_name=donor_name,
            donor_email=donor_email,
            amount=amount,
            donation_type="Cash",
            purpose=purpose,
            payment_status="Success",
            transaction_id=cash_ref,
        )

        receipt_number = f"HH-CASH-{timezone.now().year}-{donation.id:06d}"
        Receipt.objects.create(
            donation=donation,
            receipt_number=receipt_number,
        )

        AuditLog.objects.create(
            user=request.user,
            action="Cash Donation Recorded",
            description=(
                f"Cash donation of INR {amount:,.2f} recorded for donor '{donor_name}' "
                f"at {institution.name}. Ref: {cash_ref}, Receipt: {receipt_number}"
            ),
        )

        messages.success(
            request,
            f"Cash donation of ₹{amount:,.2f} successfully recorded. Receipt #{receipt_number} issued.",
        )
        return redirect("staff_donation_receipt", donation_id=donation.id)

    context = {
        "profile": profile,
        "institution": institution,
    }
    return render(request, "staff/donations/add.html", context)


@staff_required
def staff_donation_detail(request, donation_id):
    """
    View cash donation details. Scoped strictly to the Staff user's institution
    and donation_type == 'Cash'.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "staff/no_institution.html", {})

    donation = get_object_or_404(
        Donation.objects.select_related("institution", "receipt"),
        id=donation_id,
    )
    if donation.institution != institution or donation.donation_type != "Cash":
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to view this donation record.</p>"
        )

    context = {
        "profile": profile,
        "institution": institution,
        "donation": donation,
    }
    return render(request, "staff/donations/detail.html", context)


@staff_required
def staff_donation_receipt(request, donation_id):
    """
    View / print cash donation receipt.
    Strictly restricted to the Staff user's institution and Cash donations.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "staff/no_institution.html", {})

    donation = get_object_or_404(
        Donation.objects.select_related("institution", "receipt"),
        id=donation_id,
    )
    if donation.institution != institution or donation.donation_type != "Cash":
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to view this receipt.</p>"
        )

    receipt = getattr(donation, "receipt", None)
    if not receipt:
        receipt_number = f"HH-CASH-{timezone.now().year}-{donation.id:06d}"
        receipt = Receipt.objects.create(
            donation=donation,
            receipt_number=receipt_number,
        )

    context = {
        "profile": profile,
        "institution": institution,
        "donation": donation,
        "receipt": receipt,
    }
    return render(request, "staff/donations/receipt.html", context)


@staff_required
def staff_maintenance_list(request):
    """
    List maintenance records for the Staff member's institution with status filtering.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "staff/no_institution.html", {})

    status_filter = request.GET.get("status", "").strip()
    maintenance_qs = (
        Maintenance.objects.filter(institution=institution)
        .select_related("asset")
        .order_by("-scheduled_date", "-id")
    )
    if status_filter in ["Scheduled", "In Progress", "Completed", "Cancelled"]:
        maintenance_qs = maintenance_qs.filter(status=status_filter)

    total_count = Maintenance.objects.filter(institution=institution).count()
    scheduled_count = Maintenance.objects.filter(institution=institution, status="Scheduled").count()
    in_progress_count = Maintenance.objects.filter(institution=institution, status="In Progress").count()
    completed_count = Maintenance.objects.filter(institution=institution, status="Completed").count()
    cancelled_count = Maintenance.objects.filter(institution=institution, status="Cancelled").count()

    context = {
        "profile": profile,
        "institution": institution,
        "maintenance_list": maintenance_qs,
        "current_status": status_filter,
        "total_count": total_count,
        "scheduled_count": scheduled_count,
        "in_progress_count": in_progress_count,
        "completed_count": completed_count,
        "cancelled_count": cancelled_count,
    }
    return render(request, "staff/maintenance/list.html", context)


@staff_required
def staff_maintenance_add(request):
    """
    Create a new maintenance record.
    The asset dropdown is strictly filtered to the Staff member's institution.
    Submitted asset ID is verified server-side.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "staff/no_institution.html", {})

    assets = Asset.objects.filter(institution=institution).order_by("name")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        asset_id = request.POST.get("asset", "").strip()
        scheduled_date_raw = request.POST.get("scheduled_date", "").strip()
        completion_date_raw = request.POST.get("completion_date", "").strip()
        estimated_cost_raw = request.POST.get("estimated_cost", "").strip()
        actual_cost_raw = request.POST.get("actual_cost", "").strip()
        status = request.POST.get("status", "Scheduled").strip()

        errors = []
        if not title:
            errors.append("Maintenance title is required.")

        asset = None
        if not asset_id:
            errors.append("Please select a cultural asset.")
        else:
            try:
                asset = Asset.objects.get(id=asset_id, institution=institution)
            except Asset.DoesNotExist:
                errors.append("Selected asset is invalid or does not belong to your institution.")

        scheduled_date = None
        if not scheduled_date_raw:
            errors.append("Scheduled date is required.")
        else:
            try:
                scheduled_date = datetime.strptime(scheduled_date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Invalid scheduled date format (expected YYYY-MM-DD).")

        completion_date = None
        if completion_date_raw:
            try:
                completion_date = datetime.strptime(completion_date_raw, "%Y-%m-%d").date()
                if scheduled_date and completion_date < scheduled_date:
                    errors.append("Completion date cannot be earlier than scheduled date.")
            except ValueError:
                errors.append("Invalid completion date format (expected YYYY-MM-DD).")

        estimated_cost = Decimal("0.00")
        if estimated_cost_raw:
            try:
                estimated_cost = Decimal(estimated_cost_raw)
                if estimated_cost < Decimal("0.00"):
                    errors.append("Estimated cost cannot be negative.")
            except Exception:
                errors.append("Please enter a valid estimated cost.")

        actual_cost = Decimal("0.00")
        if actual_cost_raw:
            try:
                actual_cost = Decimal(actual_cost_raw)
                if actual_cost < Decimal("0.00"):
                    errors.append("Actual cost cannot be negative.")
            except Exception:
                errors.append("Please enter a valid actual cost.")

        valid_statuses = ["Scheduled", "In Progress", "Completed", "Cancelled"]
        if status not in valid_statuses:
            errors.append(f"Invalid status choice. Must be one of: {', '.join(valid_statuses)}")

        if errors:
            context = {
                "profile": profile,
                "institution": institution,
                "assets": assets,
                "errors": errors,
                "today": timezone.now().date().isoformat(),
                "form_data": {
                    "title": title,
                    "description": description,
                    "asset": asset_id,
                    "scheduled_date": scheduled_date_raw,
                    "completion_date": completion_date_raw,
                    "estimated_cost": estimated_cost_raw,
                    "actual_cost": actual_cost_raw,
                    "status": status,
                },
            }
            return render(request, "staff/maintenance/add.html", context)

        maint = Maintenance.objects.create(
            institution=institution,
            asset=asset,
            title=title,
            description=description,
            scheduled_date=scheduled_date,
            completion_date=completion_date,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            status=status,
        )

        AuditLog.objects.create(
            user=request.user,
            action="Maintenance Created",
            description=(
                f"Maintenance record '{title}' created for asset '{asset.name}' "
                f"at {institution.name} (Status: {status})"
            ),
        )

        messages.success(request, f"Maintenance record '{title}' created successfully.")
        return redirect("staff_maintenance_detail", maintenance_id=maint.id)

    context = {
        "profile": profile,
        "institution": institution,
        "assets": assets,
        "today": timezone.now().date().isoformat(),
    }
    return render(request, "staff/maintenance/add.html", context)


@staff_required
def staff_maintenance_detail(request, maintenance_id):
    """
    View maintenance record dossier. Scoped strictly to the Staff user's institution.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "staff/no_institution.html", {})

    maint = get_object_or_404(
        Maintenance.objects.select_related("institution", "asset"),
        id=maintenance_id,
    )
    if maint.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to view this maintenance record.</p>"
        )

    context = {
        "profile": profile,
        "institution": institution,
        "maintenance": maint,
    }
    return render(request, "staff/maintenance/detail.html", context)


@staff_required
def staff_maintenance_edit(request, maintenance_id):
    """
    Update an existing maintenance record.
    Restricted to the Staff member's institution.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "staff/no_institution.html", {})

    maint = get_object_or_404(
        Maintenance.objects.select_related("institution", "asset"),
        id=maintenance_id,
    )
    if maint.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to edit this maintenance record.</p>"
        )

    assets = Asset.objects.filter(institution=institution).order_by("name")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        asset_id = request.POST.get("asset", "").strip()
        scheduled_date_raw = request.POST.get("scheduled_date", "").strip()
        completion_date_raw = request.POST.get("completion_date", "").strip()
        estimated_cost_raw = request.POST.get("estimated_cost", "").strip()
        actual_cost_raw = request.POST.get("actual_cost", "").strip()
        status = request.POST.get("status", maint.status).strip()

        errors = []
        if not title:
            errors.append("Maintenance title is required.")

        asset = None
        if not asset_id:
            errors.append("Please select a cultural asset.")
        else:
            try:
                asset = Asset.objects.get(id=asset_id, institution=institution)
            except Asset.DoesNotExist:
                errors.append("Selected asset is invalid or does not belong to your institution.")

        scheduled_date = None
        if not scheduled_date_raw:
            errors.append("Scheduled date is required.")
        else:
            try:
                scheduled_date = datetime.strptime(scheduled_date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Invalid scheduled date format (expected YYYY-MM-DD).")

        completion_date = None
        if completion_date_raw:
            try:
                completion_date = datetime.strptime(completion_date_raw, "%Y-%m-%d").date()
                if scheduled_date and completion_date < scheduled_date:
                    errors.append("Completion date cannot be earlier than scheduled date.")
            except ValueError:
                errors.append("Invalid completion date format (expected YYYY-MM-DD).")

        estimated_cost = Decimal("0.00")
        if estimated_cost_raw:
            try:
                estimated_cost = Decimal(estimated_cost_raw)
                if estimated_cost < Decimal("0.00"):
                    errors.append("Estimated cost cannot be negative.")
            except Exception:
                errors.append("Please enter a valid estimated cost.")

        actual_cost = Decimal("0.00")
        if actual_cost_raw:
            try:
                actual_cost = Decimal(actual_cost_raw)
                if actual_cost < Decimal("0.00"):
                    errors.append("Actual cost cannot be negative.")
            except Exception:
                errors.append("Please enter a valid actual cost.")

        valid_statuses = ["Scheduled", "In Progress", "Completed", "Cancelled"]
        if status not in valid_statuses:
            errors.append(f"Invalid status choice. Must be one of: {', '.join(valid_statuses)}")

        if errors:
            context = {
                "profile": profile,
                "institution": institution,
                "maintenance": maint,
                "assets": assets,
                "errors": errors,
            }
            return render(request, "staff/maintenance/edit.html", context)

        maint.title = title
        maint.description = description
        maint.asset = asset
        maint.scheduled_date = scheduled_date
        maint.completion_date = completion_date
        maint.estimated_cost = estimated_cost
        maint.actual_cost = actual_cost
        maint.status = status
        maint.save()

        AuditLog.objects.create(
            user=request.user,
            action="Maintenance Updated",
            description=(
                f"Maintenance record #{maint.id} ('{title}') updated at {institution.name} "
                f"(Status: {status})"
            ),
        )

        messages.success(request, f"Maintenance record '{title}' updated successfully.")
        return redirect("staff_maintenance_detail", maintenance_id=maint.id)

    context = {
        "profile": profile,
        "institution": institution,
        "maintenance": maint,
        "assets": assets,
    }
    return render(request, "staff/maintenance/edit.html", context)


# ──────────────────────────────────────────────
# TRUSTEE MODULE — views
# ──────────────────────────────────────────────

@trustee_required
def trustee_dashboard(request):
    """Trustee dashboard showing their registered institution, status, asset metrics, financial overview, and event & maintenance summaries."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    total_assets = 0
    total_valuation = Decimal("0.00")
    needs_maintenance_count = 0
    recent_assets = []
    received_donations = Decimal("0.00")
    approved_expenses = Decimal("0.00")
    net_available = Decimal("0.00")
    pending_expenses_count = 0
    upcoming_events_count = 0
    total_events_count = 0
    total_event_estimated_cost = Decimal("0.00")
    total_event_actual_cost = Decimal("0.00")
    scheduled_maintenance_count = 0
    in_progress_maintenance_count = 0
    total_maintenance_count = 0
    total_maint_estimated_cost = Decimal("0.00")
    total_maint_actual_cost = Decimal("0.00")

    if institution:
        assets_qs = Asset.objects.filter(institution=institution)
        total_assets = assets_qs.count()
        total_valuation = assets_qs.aggregate(total=Sum("current_valuation"))["total"] or Decimal("0.00")
        needs_maintenance_count = assets_qs.filter(condition__in=["Needs Maintenance", "Damaged"]).count()
        recent_assets = assets_qs.order_by("-id")[:5]

        # Financial metrics
        received_donations = (
            Donation.objects.filter(institution=institution, payment_status="Success")
            .aggregate(t=Sum("amount"))["t"]
            or Decimal("0.00")
        )
        approved_expenses = (
            Expense.objects.filter(institution=institution, status="Approved")
            .aggregate(t=Sum("amount"))["t"]
            or Decimal("0.00")
        )
        net_available = received_donations - approved_expenses
        pending_expenses_count = Expense.objects.filter(
            institution=institution, status="Pending"
        ).count()

        # Event metrics
        events_qs = Event.objects.filter(institution=institution)
        upcoming_events_count = events_qs.filter(status__in=["Scheduled", "Ongoing"]).count()
        total_events_count = events_qs.count()
        total_event_estimated_cost = events_qs.aggregate(t=Sum("estimated_cost"))["t"] or Decimal("0.00")
        total_event_actual_cost = events_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

        # Maintenance metrics
        maint_qs = Maintenance.objects.filter(institution=institution)
        scheduled_maintenance_count = maint_qs.filter(status="Scheduled").count()
        in_progress_maintenance_count = maint_qs.filter(status="In Progress").count()
        total_maintenance_count = maint_qs.count()
        total_maint_estimated_cost = maint_qs.aggregate(t=Sum("estimated_cost"))["t"] or Decimal("0.00")
        total_maint_actual_cost = maint_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

    return render(request, "trustee/dashboard.html", {
        "institution": institution,
        "total_assets": total_assets,
        "total_valuation": total_valuation,
        "needs_maintenance_count": needs_maintenance_count,
        "recent_assets": recent_assets,
        "received_donations": received_donations,
        "approved_expenses": approved_expenses,
        "net_available": net_available,
        "pending_expenses_count": pending_expenses_count,
        "upcoming_events_count": upcoming_events_count,
        "total_events_count": total_events_count,
        "total_event_estimated_cost": total_event_estimated_cost,
        "total_event_actual_cost": total_event_actual_cost,
        "scheduled_maintenance_count": scheduled_maintenance_count,
        "in_progress_maintenance_count": in_progress_maintenance_count,
        "total_maintenance_count": total_maintenance_count,
        "total_maint_estimated_cost": total_maint_estimated_cost,
        "total_maint_actual_cost": total_maint_actual_cost,
    })


@trustee_required
def trustee_institution_register(request):
    """Trustee registers an institution. Always created with approval_status='Pending'."""
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        institution_type = request.POST.get("institution_type", "").strip()
        address = request.POST.get("address", "").strip()
        authorized_representative = request.POST.get("authorized_representative", "").strip()
        contact_number = request.POST.get("contact_number", "").strip()
        email = request.POST.get("email", "").strip()
        pan = request.POST.get("pan", "").strip()
        registration_certificate = request.FILES.get("registration_certificate")

        errors = []
        if not name:
            errors.append("Institution name is required.")
        if not institution_type or institution_type not in ["Temple", "Trust", "Heritage"]:
            errors.append("Please select a valid institution type.")
        if not address:
            errors.append("Official address is required.")
        if not authorized_representative:
            errors.append("Authorized representative name is required.")
        if not contact_number:
            errors.append("Contact number is required.")
        if not email:
            errors.append("Official email address is required.")

        if errors:
            return render(request, "trustee/institutions.html", {
                "errors": errors,
                "form_data": {
                    "name": name,
                    "institution_type": institution_type,
                    "address": address,
                    "authorized_representative": authorized_representative,
                    "contact_number": contact_number,
                    "email": email,
                    "pan": pan,
                },
                "default_representative": request.user.get_full_name() or request.user.username,
                "default_email": request.user.email,
                "default_phone": profile.phone,
            })

        # Create Institution — CRITICAL: approval_status is ALWAYS "Pending" server-side
        institution = Institution.objects.create(
            name=name,
            institution_type=institution_type,
            address=address,
            authorized_representative=authorized_representative,
            contact_number=contact_number,
            email=email,
            pan=pan,
            registration_certificate=registration_certificate,
            approval_status="Pending",
        )

        # Associate the Trustee with this institution
        profile.institution = institution
        profile.save()

        # AuditLog entry
        AuditLog.objects.create(
            user=request.user,
            action="Institution Registration Submitted",
            description=(
                f"Trustee '{request.user.username}' submitted registration for "
                f"'{institution.name}' ({institution.get_institution_type_display()}). Status: Pending."
            ),
        )

        messages.success(
            request,
            f"Institution '{institution.name}' registered successfully! "
            "It is currently Pending administrative review and will be activated upon approval."
        )
        return redirect("trustee_dashboard")

    return render(request, "trustee/institutions.html", {
        "default_representative": request.user.get_full_name() or request.user.username,
        "default_email": request.user.email,
        "default_phone": profile.phone,
    })


@trustee_required
def trustee_asset_list(request):
    """List all assets belonging to the Trustee's institution with metrics and filters."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution before managing assets.")
        return redirect("trustee_institution_register")

    assets_qs = Asset.objects.filter(institution=institution)
    total_assets = assets_qs.count()
    total_valuation = assets_qs.aggregate(total=Sum("current_valuation"))["total"] or Decimal("0.00")
    good_condition_count = assets_qs.filter(condition__in=["Excellent", "Good"]).count()
    needs_maintenance_count = assets_qs.filter(condition__in=["Needs Maintenance", "Damaged"]).count()

    type_filter = request.GET.get("type")
    condition_filter = request.GET.get("condition")
    current_filter = "all"

    if type_filter in ["Movable", "Immovable"]:
        assets = assets_qs.filter(asset_type=type_filter).order_by("-id")
        current_filter = type_filter
    elif condition_filter == "maintenance":
        assets = assets_qs.filter(condition__in=["Needs Maintenance", "Damaged"]).order_by("-id")
        current_filter = "maintenance"
    else:
        assets = assets_qs.order_by("-id")
        current_filter = "all"

    return render(request, "trustee/assets.html", {
        "institution": institution,
        "assets": assets,
        "total_assets": total_assets,
        "total_valuation": total_valuation,
        "good_condition_count": good_condition_count,
        "needs_maintenance_count": needs_maintenance_count,
        "current_filter": current_filter,
    })


@trustee_required
def trustee_asset_add(request):
    """Record a new asset automatically linked to the Trustee's institution."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution before cataloging assets.")
        return redirect("trustee_institution_register")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        asset_type = request.POST.get("asset_type", "").strip()
        category = request.POST.get("category", "").strip()
        current_valuation_raw = request.POST.get("current_valuation", "").strip()
        condition = request.POST.get("condition", "").strip()
        location = request.POST.get("location", "").strip()
        date_acquired = request.POST.get("date_acquired", "").strip() or None
        description = request.POST.get("description", "").strip()
        photograph = request.FILES.get("photograph")

        errors = []
        if not name:
            errors.append("Asset name is required.")
        if not asset_type or asset_type not in ["Movable", "Immovable"]:
            errors.append("Please select a valid asset classification (Movable or Immovable).")
        if not category:
            errors.append("Category is required.")
        if not current_valuation_raw:
            errors.append("Current valuation is required.")
        else:
            try:
                current_valuation = Decimal(current_valuation_raw)
                if current_valuation < 0:
                    errors.append("Valuation cannot be negative.")
            except Exception:
                errors.append("Please enter a valid numeric valuation.")

        valid_conditions = ["Excellent", "Good", "Needs Maintenance", "Damaged"]
        if not condition or condition not in valid_conditions:
            errors.append("Please select a valid physical condition.")
        if not location:
            errors.append("Location on premises is required.")

        if errors:
            return render(request, "trustee/asset_form.html", {
                "institution": institution,
                "is_edit": False,
                "asset": None,
                "errors": errors,
                "form_data": request.POST,
            })

        # Create Asset with automatic attribution to Trustee's institution
        asset = Asset.objects.create(
            institution=institution,
            name=name,
            asset_type=asset_type,
            category=category,
            description=description,
            photograph=photograph,
            current_valuation=current_valuation,
            condition=condition,
            location=location,
            date_acquired=date_acquired,
        )

        # AuditLog entry
        AuditLog.objects.create(
            user=request.user,
            action="Asset Created",
            description=(
                f"Trustee '{request.user.username}' added asset '{asset.name}' "
                f"(ID: {asset.id}, Classification: {asset.asset_type}, Valuation: ₹{asset.current_valuation}) "
                f"to institution '{institution.name}'."
            ),
        )

        messages.success(request, f"Heritage asset '{asset.name}' has been successfully cataloged.")
        return redirect("trustee_asset_detail", asset_id=asset.id)

    return render(request, "trustee/asset_form.html", {
        "institution": institution,
        "is_edit": False,
        "asset": None,
    })


@trustee_required
def trustee_asset_detail(request, asset_id):
    """View full dossier of an asset belonging to the Trustee's institution."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    asset = get_object_or_404(Asset.objects.select_related("institution"), id=asset_id)
    if asset.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to view assets belonging to another institution.</p>"
        )

    maintenance_history = asset.maintenance_history.all().order_by("-scheduled_date")
    return render(request, "trustee/asset_detail.html", {
        "asset": asset,
        "maintenance_history": maintenance_history,
    })


@trustee_required
def trustee_asset_edit(request, asset_id):
    """Edit an asset belonging to the Trustee's institution."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    asset = get_object_or_404(Asset, id=asset_id)
    if asset.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to modify assets belonging to another institution.</p>"
        )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        asset_type = request.POST.get("asset_type", "").strip()
        category = request.POST.get("category", "").strip()
        current_valuation_raw = request.POST.get("current_valuation", "").strip()
        condition = request.POST.get("condition", "").strip()
        location = request.POST.get("location", "").strip()
        date_acquired = request.POST.get("date_acquired", "").strip() or None
        description = request.POST.get("description", "").strip()
        photograph = request.FILES.get("photograph")

        errors = []
        if not name:
            errors.append("Asset name is required.")
        if not asset_type or asset_type not in ["Movable", "Immovable"]:
            errors.append("Please select a valid asset classification (Movable or Immovable).")
        if not category:
            errors.append("Category is required.")
        if not current_valuation_raw:
            errors.append("Current valuation is required.")
        else:
            try:
                current_valuation = Decimal(current_valuation_raw)
                if current_valuation < 0:
                    errors.append("Valuation cannot be negative.")
            except Exception:
                errors.append("Please enter a valid numeric valuation.")

        valid_conditions = ["Excellent", "Good", "Needs Maintenance", "Damaged"]
        if not condition or condition not in valid_conditions:
            errors.append("Please select a valid physical condition.")
        if not location:
            errors.append("Location on premises is required.")

        if errors:
            return render(request, "trustee/asset_form.html", {
                "institution": institution,
                "is_edit": True,
                "asset": asset,
                "errors": errors,
                "form_data": request.POST,
            })

        asset.name = name
        asset.asset_type = asset_type
        asset.category = category
        asset.current_valuation = current_valuation
        asset.condition = condition
        asset.location = location
        asset.date_acquired = date_acquired
        asset.description = description
        if photograph:
            asset.photograph = photograph
        asset.save()

        # AuditLog entry
        AuditLog.objects.create(
            user=request.user,
            action="Asset Updated",
            description=(
                f"Trustee '{request.user.username}' updated asset '{asset.name}' "
                f"(ID: {asset.id}, Classification: {asset.asset_type}, Valuation: ₹{asset.current_valuation}) "
                f"for institution '{institution.name}'."
            ),
        )

        messages.success(request, f"Heritage asset '{asset.name}' updated successfully.")
        return redirect("trustee_asset_detail", asset_id=asset.id)

    return render(request, "trustee/asset_form.html", {
        "institution": institution,
        "is_edit": True,
        "asset": asset,
    })


@trustee_required
def trustee_asset_delete(request, asset_id):
    """Delete an asset belonging to the Trustee's institution with confirmation."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    asset = get_object_or_404(Asset, id=asset_id)
    if asset.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to delete assets belonging to another institution.</p>"
        )

    if request.method == "POST":
        asset_name = asset.name
        asset_id_val = asset.id
        valuation = asset.current_valuation
        asset.delete()

        # AuditLog entry
        AuditLog.objects.create(
            user=request.user,
            action="Asset Deleted",
            description=(
                f"Trustee '{request.user.username}' deleted asset '{asset_name}' "
                f"(ID: {asset_id_val}, Valuation: ₹{valuation}) from institution '{institution.name}'."
            ),
        )

        messages.success(request, f"Heritage asset '{asset_name}' has been permanently removed.")
        return redirect("trustee_asset_list")

    return render(request, "trustee/asset_confirm_delete.html", {
        "institution": institution,
        "asset": asset,
    })


# ──────────────────────────────────────────────
# TRUSTEE MODULE — Donation & Finance Management
# ──────────────────────────────────────────────

@trustee_required
def trustee_finance_dashboard(request):
    """Trustee finance dashboard displaying income, expenses, and net available funds for their institution."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution before accessing finance records.")
        return redirect("trustee_institution_register")

    # Donations aggregation
    all_donations = Donation.objects.filter(institution=institution)
    total_donations_count = all_donations.count()
    successful_donations = all_donations.filter(payment_status="Success")
    successful_donations_count = successful_donations.count()
    received_donations = successful_donations.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    online_donations_qs = successful_donations.filter(donation_type="Online")
    online_donations = online_donations_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    online_donations_count = online_donations_qs.count()

    cash_donations_qs = successful_donations.filter(donation_type="Cash")
    cash_donations = cash_donations_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    cash_donations_count = cash_donations_qs.count()

    pending_donations_count = all_donations.filter(payment_status="Pending").count()
    failed_donations_count = all_donations.filter(payment_status="Failed").count()

    # Expenses aggregation
    all_expenses = Expense.objects.filter(institution=institution)
    approved_expenses_qs = all_expenses.filter(status="Approved")
    approved_expenses = approved_expenses_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    approved_expenses_count = approved_expenses_qs.count()

    pending_expenses_qs = all_expenses.filter(status="Pending")
    pending_expenses = pending_expenses_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    pending_expenses_count = pending_expenses_qs.count()

    rejected_expenses_qs = all_expenses.filter(status="Rejected")
    rejected_expenses = rejected_expenses_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    rejected_expenses_count = rejected_expenses_qs.count()

    total_expenses_recorded = approved_expenses + pending_expenses + rejected_expenses

    # Calculated Net Funds (Received Income − Approved Expenses)
    net_available = received_donations - approved_expenses

    # Recent lists
    recent_donations = all_donations.select_related("receipt").order_by("-donation_date")[:5]
    recent_expenses = all_expenses.select_related("donation", "approved_by").order_by("-expense_date", "-id")[:5]

    return render(request, "trustee/finance.html", {
        "institution": institution,
        "received_donations": received_donations,
        "online_donations": online_donations,
        "cash_donations": cash_donations,
        "online_donations_count": online_donations_count,
        "cash_donations_count": cash_donations_count,
        "total_donations_count": total_donations_count,
        "successful_donations_count": successful_donations_count,
        "pending_donations_count": pending_donations_count,
        "failed_donations_count": failed_donations_count,
        "approved_expenses": approved_expenses,
        "approved_expenses_count": approved_expenses_count,
        "pending_expenses": pending_expenses,
        "pending_expenses_count": pending_expenses_count,
        "rejected_expenses": rejected_expenses,
        "rejected_expenses_count": rejected_expenses_count,
        "total_expenses_recorded": total_expenses_recorded,
        "net_available": net_available,
        "recent_donations": recent_donations,
        "recent_expenses": recent_expenses,
    })


@trustee_required
def trustee_donation_list(request):
    """List donations belonging to the Trustee's institution with filtering."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution before accessing donation records.")
        return redirect("trustee_institution_register")

    donations_qs = Donation.objects.filter(institution=institution).select_related("receipt")

    count_all = donations_qs.count()
    count_success = donations_qs.filter(payment_status="Success").count()
    count_online = donations_qs.filter(payment_status="Success", donation_type="Online").count()
    count_cash = donations_qs.filter(payment_status="Success", donation_type="Cash").count()
    count_pending = donations_qs.filter(payment_status="Pending").count()
    count_failed = donations_qs.filter(payment_status="Failed").count()

    total_received = (
        donations_qs.filter(payment_status="Success").aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )

    type_filter = request.GET.get("type")
    status_filter = request.GET.get("status")
    current_filter = "all"

    if type_filter in ["Online", "Cash"]:
        donations = donations_qs.filter(donation_type=type_filter).order_by("-donation_date")
        current_filter = type_filter
    elif status_filter in ["Success", "Pending", "Failed"]:
        donations = donations_qs.filter(payment_status=status_filter).order_by("-donation_date")
        current_filter = status_filter
    else:
        donations = donations_qs.order_by("-donation_date")

    return render(request, "trustee/donations.html", {
        "institution": institution,
        "donations": donations,
        "current_filter": current_filter,
        "count_all": count_all,
        "count_success": count_success,
        "count_online": count_online,
        "count_cash": count_cash,
        "count_pending": count_pending,
        "count_failed": count_failed,
        "total_received": total_received,
    })


@trustee_required
def trustee_donation_detail(request, donation_id):
    """View detailed dossier for a donation belonging to the Trustee's institution."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    donation = get_object_or_404(
        Donation.objects.select_related("institution", "donor", "receipt"),
        id=donation_id,
    )
    if donation.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to view donations belonging to another institution.</p>"
        )

    linked_expenses = donation.expenses.all().order_by("-expense_date", "-id")
    return render(request, "trustee/donation_detail.html", {
        "donation": donation,
        "linked_expenses": linked_expenses,
    })


@trustee_required
def trustee_receipt_view(request, donation_id):
    """Trustee views digital receipt for a donation belonging to their institution."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    donation = get_object_or_404(
        Donation.objects.select_related("institution", "receipt"),
        id=donation_id,
    )
    if donation.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to view receipts belonging to another institution.</p>"
        )

    receipt = getattr(donation, "receipt", None)
    if not receipt:
        messages.error(request, "No official receipt exists for this donation record.")
        return redirect("trustee_donation_detail", donation_id=donation.id)

    return render(request, "trustee/receipt.html", {
        "receipt": receipt,
    })


@trustee_required
def trustee_expense_list(request):
    """List expenses belonging to the Trustee's institution with status filters."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution before accessing expense records.")
        return redirect("trustee_institution_register")

    expenses_qs = Expense.objects.filter(institution=institution).select_related("donation", "approved_by")

    count_all = expenses_qs.count()
    count_pending = expenses_qs.filter(status="Pending").count()
    count_approved = expenses_qs.filter(status="Approved").count()
    count_rejected = expenses_qs.filter(status="Rejected").count()

    approved_total = (
        expenses_qs.filter(status="Approved").aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    pending_total = (
        expenses_qs.filter(status="Pending").aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )

    status_filter = request.GET.get("status")
    current_filter = "all"
    if status_filter in ["Pending", "Approved", "Rejected"]:
        expenses = expenses_qs.filter(status=status_filter).order_by("-expense_date", "-id")
        current_filter = status_filter
    else:
        expenses = expenses_qs.order_by("-expense_date", "-id")

    return render(request, "trustee/expenses.html", {
        "institution": institution,
        "expenses": expenses,
        "current_filter": current_filter,
        "count_all": count_all,
        "count_pending": count_pending,
        "count_approved": count_approved,
        "count_rejected": count_rejected,
        "approved_total": approved_total,
        "pending_total": pending_total,
    })


@trustee_required
def trustee_expense_add(request):
    """Record an expenditure voucher for the Trustee's institution (starts as Pending)."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution before recording expenses.")
        return redirect("trustee_institution_register")

    available_donations = Donation.objects.filter(
        institution=institution, payment_status="Success"
    ).order_by("-donation_date")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "").strip()
        amount_raw = request.POST.get("amount", "").strip()
        expense_date = request.POST.get("expense_date", "").strip()
        description = request.POST.get("description", "").strip()
        donation_id = request.POST.get("donation_id", "").strip()

        errors = []
        if not title:
            errors.append("Expense title is required.")
        if not category:
            errors.append("Category is required.")
        if not amount_raw:
            errors.append("Disbursement amount is required.")
        else:
            try:
                amount = Decimal(amount_raw)
                if amount <= 0:
                    errors.append("Amount must be greater than zero.")
            except Exception:
                errors.append("Please enter a valid numeric amount.")

        if not expense_date:
            errors.append("Expense date is required.")

        selected_donation = None
        if donation_id:
            try:
                selected_donation = available_donations.get(id=int(donation_id))
            except (ValueError, Donation.DoesNotExist):
                errors.append("Selected donation funding source is invalid or belongs to another institution.")

        if errors:
            return render(request, "trustee/expense_form.html", {
                "institution": institution,
                "available_donations": available_donations,
                "errors": errors,
                "form_data": request.POST,
            })

        # Create Expense — Status is ALWAYS "Pending" on creation for major expense review
        expense = Expense.objects.create(
            institution=institution,
            donation=selected_donation,
            title=title,
            category=category,
            amount=amount,
            expense_date=expense_date,
            description=description,
            status="Pending",
            approved_by=None,
        )

        # AuditLog entry
        AuditLog.objects.create(
            user=request.user,
            action="Expense Created",
            description=(
                f"Trustee '{request.user.username}' created expense '{expense.title}' "
                f"(ID: {expense.id}, Amount: ₹{expense.amount}, Category: '{expense.category}', Status: Pending) "
                f"for institution '{institution.name}'."
            ),
        )

        messages.success(
            request,
            f"Expense '{expense.title}' recorded and submitted for Trustee review (Status: Pending)."
        )
        return redirect("trustee_expense_detail", expense_id=expense.id)

    return render(request, "trustee/expense_form.html", {
        "institution": institution,
        "available_donations": available_donations,
    })


@trustee_required
def trustee_expense_detail(request, expense_id):
    """View detailed dossier for an expense and provide authorization controls."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    expense = get_object_or_404(
        Expense.objects.select_related("institution", "donation", "approved_by"),
        id=expense_id,
    )
    if expense.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to view expenses belonging to another institution.</p>"
        )

    return render(request, "trustee/expense_detail.html", {
        "expense": expense,
    })


@trustee_required
def trustee_expense_approve(request, expense_id):
    """Trustee statutory authorization of a major expense (Pending -> Approved)."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    expense = get_object_or_404(Expense, id=expense_id)
    if expense.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to approve expenses belonging to another institution.</p>"
        )

    if request.method != "POST":
        return redirect("trustee_expense_detail", expense_id=expense_id)

    if expense.status != "Pending":
        messages.warning(request, f"Expense '{expense.title}' is already {expense.status}.")
        return redirect("trustee_expense_detail", expense_id=expense.id)

    expense.status = "Approved"
    expense.approved_by = request.user
    expense.save()

    AuditLog.objects.create(
        user=request.user,
        action="Expense Approved",
        description=(
            f"Trustee '{request.user.username}' approved major expense '{expense.title}' "
            f"(ID: {expense.id}, Amount: ₹{expense.amount}) for institution '{institution.name}'."
        ),
    )

    messages.success(request, f"Major expense '{expense.title}' has been successfully Approved.")
    return redirect("trustee_expense_detail", expense_id=expense.id)


@trustee_required
def trustee_expense_reject(request, expense_id):
    """Trustee rejection of an expenditure voucher (Pending -> Rejected)."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    expense = get_object_or_404(Expense, id=expense_id)
    if expense.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to reject expenses belonging to another institution.</p>"
        )

    if request.method != "POST":
        return redirect("trustee_expense_detail", expense_id=expense_id)

    if expense.status != "Pending":
        messages.warning(request, f"Expense '{expense.title}' is already {expense.status}.")
        return redirect("trustee_expense_detail", expense_id=expense.id)

    expense.status = "Rejected"
    expense.approved_by = None
    expense.save()

    AuditLog.objects.create(
        user=request.user,
        action="Expense Rejected",
        description=(
            f"Trustee '{request.user.username}' rejected expense '{expense.title}' "
            f"(ID: {expense.id}, Amount: ₹{expense.amount}) for institution '{institution.name}'."
        ),
    )

    messages.warning(request, f"Expense '{expense.title}' has been marked as Rejected.")
    return redirect("trustee_expense_detail", expense_id=expense.id)


# ──────────────────────────────────────────────
# TRUSTEE MODULE — Event & Maintenance Management
# ──────────────────────────────────────────────

@trustee_required
def trustee_event_list(request):
    """List events for the Trustee's institution with status filtering and cost tracking."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution before accessing event records.")
        return redirect("trustee_institution_register")

    events_qs = Event.objects.filter(institution=institution)
    count_all = events_qs.count()
    count_scheduled = events_qs.filter(status="Scheduled").count()
    count_ongoing = events_qs.filter(status="Ongoing").count()
    count_completed = events_qs.filter(status="Completed").count()
    count_cancelled = events_qs.filter(status="Cancelled").count()

    total_estimated = events_qs.aggregate(t=Sum("estimated_cost"))["t"] or Decimal("0.00")
    total_actual = events_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

    status_filter = request.GET.get("status")
    current_filter = "all"
    if status_filter in ["Scheduled", "Ongoing", "Completed", "Cancelled"]:
        events = events_qs.filter(status=status_filter).order_by("date", "-id")
        current_filter = status_filter
    else:
        events = events_qs.order_by("date", "-id")

    return render(request, "trustee/events.html", {
        "institution": institution,
        "events": events,
        "current_filter": current_filter,
        "count_all": count_all,
        "count_scheduled": count_scheduled,
        "count_ongoing": count_ongoing,
        "count_completed": count_completed,
        "count_cancelled": count_cancelled,
        "total_estimated": total_estimated,
        "total_actual": total_actual,
    })


@trustee_required
def trustee_event_add(request):
    """Create a new event or festival for the Trustee's institution."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution before scheduling events.")
        return redirect("trustee_institution_register")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        date_val = request.POST.get("date", "").strip()
        location = request.POST.get("location", "").strip()
        estimated_cost_raw = request.POST.get("estimated_cost", "0").strip()
        actual_cost_raw = request.POST.get("actual_cost", "0").strip()
        status = request.POST.get("status", "Scheduled").strip()

        errors = []
        if not name:
            errors.append("Event name is required.")
        if not date_val:
            errors.append("Event date is required.")
        if not location:
            errors.append("Location is required.")

        valid_statuses = [choice[0] for choice in Event.EVENT_STATUS]
        if status not in valid_statuses:
            status = "Scheduled"

        try:
            estimated_cost = Decimal(estimated_cost_raw) if estimated_cost_raw else Decimal("0.00")
            if estimated_cost < 0:
                errors.append("Estimated cost cannot be negative.")
        except Exception:
            errors.append("Please enter a valid numeric value for estimated cost.")
            estimated_cost = Decimal("0.00")

        try:
            actual_cost = Decimal(actual_cost_raw) if actual_cost_raw else Decimal("0.00")
            if actual_cost < 0:
                errors.append("Actual cost cannot be negative.")
        except Exception:
            errors.append("Please enter a valid numeric value for actual cost.")
            actual_cost = Decimal("0.00")

        if errors:
            return render(request, "trustee/event_form.html", {
                "institution": institution,
                "errors": errors,
                "form_data": request.POST,
                "is_edit": False,
                "event_statuses": Event.EVENT_STATUS,
            })

        event = Event.objects.create(
            institution=institution,
            name=name,
            description=description,
            date=date_val,
            location=location,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            status=status,
        )

        AuditLog.objects.create(
            user=request.user,
            action="Event Created",
            description=(
                f"Trustee '{request.user.username}' created event '{event.name}' "
                f"(ID: {event.id}, Date: {event.date}, Status: {event.status}) "
                f"for institution '{institution.name}'."
            ),
        )

        messages.success(request, f"Event '{event.name}' scheduled successfully.")
        return redirect("trustee_event_detail", event_id=event.id)

    return render(request, "trustee/event_form.html", {
        "institution": institution,
        "is_edit": False,
        "event_statuses": Event.EVENT_STATUS,
    })


@trustee_required
def trustee_event_detail(request, event_id):
    """View detailed dossier for an event."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    event = get_object_or_404(Event.objects.select_related("institution"), id=event_id)
    if event.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to view events belonging to another institution.</p>"
        )

    cost_variance = event.actual_cost - event.estimated_cost
    return render(request, "trustee/event_detail.html", {
        "event": event,
        "institution": institution,
        "cost_variance": cost_variance,
    })


@trustee_required
def trustee_event_edit(request, event_id):
    """Update an existing event."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    event = get_object_or_404(Event, id=event_id)
    if event.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to edit events belonging to another institution.</p>"
        )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        date_val = request.POST.get("date", "").strip()
        location = request.POST.get("location", "").strip()
        estimated_cost_raw = request.POST.get("estimated_cost", "0").strip()
        actual_cost_raw = request.POST.get("actual_cost", "0").strip()
        status = request.POST.get("status", "Scheduled").strip()

        errors = []
        if not name:
            errors.append("Event name is required.")
        if not date_val:
            errors.append("Event date is required.")
        if not location:
            errors.append("Location is required.")

        valid_statuses = [choice[0] for choice in Event.EVENT_STATUS]
        if status not in valid_statuses:
            status = event.status

        try:
            estimated_cost = Decimal(estimated_cost_raw) if estimated_cost_raw else Decimal("0.00")
            if estimated_cost < 0:
                errors.append("Estimated cost cannot be negative.")
        except Exception:
            errors.append("Please enter a valid numeric value for estimated cost.")
            estimated_cost = event.estimated_cost

        try:
            actual_cost = Decimal(actual_cost_raw) if actual_cost_raw else Decimal("0.00")
            if actual_cost < 0:
                errors.append("Actual cost cannot be negative.")
        except Exception:
            errors.append("Please enter a valid numeric value for actual cost.")
            actual_cost = event.actual_cost

        if errors:
            return render(request, "trustee/event_form.html", {
                "institution": institution,
                "event": event,
                "errors": errors,
                "form_data": request.POST,
                "is_edit": True,
                "event_statuses": Event.EVENT_STATUS,
            })

        event.name = name
        event.description = description
        event.date = date_val
        event.location = location
        event.estimated_cost = estimated_cost
        event.actual_cost = actual_cost
        event.status = status
        event.save()

        AuditLog.objects.create(
            user=request.user,
            action="Event Updated",
            description=(
                f"Trustee '{request.user.username}' updated event '{event.name}' "
                f"(ID: {event.id}, Date: {event.date}, Status: {event.status}) "
                f"for institution '{institution.name}'."
            ),
        )

        messages.success(request, f"Event '{event.name}' updated successfully.")
        return redirect("trustee_event_detail", event_id=event.id)

    return render(request, "trustee/event_form.html", {
        "institution": institution,
        "event": event,
        "is_edit": True,
        "event_statuses": Event.EVENT_STATUS,
    })


@trustee_required
def trustee_event_delete(request, event_id):
    """Delete an event (POST + CSRF confirmation)."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    event = get_object_or_404(Event, id=event_id)
    if event.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to delete events belonging to another institution.</p>"
        )

    if request.method != "POST":
        return redirect("trustee_event_detail", event_id=event_id)

    event_name = event.name
    event_id_val = event.id
    event.delete()

    AuditLog.objects.create(
        user=request.user,
        action="Event Deleted",
        description=(
            f"Trustee '{request.user.username}' deleted event '{event_name}' "
            f"(ID: {event_id_val}) from institution '{institution.name}'."
        ),
    )

    messages.success(request, f"Event '{event_name}' deleted successfully.")
    return redirect("trustee_event_list")


@trustee_required
def trustee_maintenance_list(request):
    """List maintenance activities for the Trustee's institution with status filtering."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution before accessing maintenance records.")
        return redirect("trustee_institution_register")

    maint_qs = Maintenance.objects.filter(institution=institution).select_related("asset")
    count_all = maint_qs.count()
    count_scheduled = maint_qs.filter(status="Scheduled").count()
    count_in_progress = maint_qs.filter(status="In Progress").count()
    count_completed = maint_qs.filter(status="Completed").count()
    count_cancelled = maint_qs.filter(status="Cancelled").count()

    total_estimated = maint_qs.aggregate(t=Sum("estimated_cost"))["t"] or Decimal("0.00")
    total_actual = maint_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

    status_filter = request.GET.get("status")
    current_filter = "all"
    if status_filter in ["Scheduled", "In Progress", "Completed", "Cancelled"]:
        maintenance_records = maint_qs.filter(status=status_filter).order_by("scheduled_date", "-id")
        current_filter = status_filter
    else:
        maintenance_records = maint_qs.order_by("scheduled_date", "-id")

    return render(request, "trustee/maintenance.html", {
        "institution": institution,
        "maintenance_records": maintenance_records,
        "current_filter": current_filter,
        "count_all": count_all,
        "count_scheduled": count_scheduled,
        "count_in_progress": count_in_progress,
        "count_completed": count_completed,
        "count_cancelled": count_cancelled,
        "total_estimated": total_estimated,
        "total_actual": total_actual,
    })


@trustee_required
def trustee_maintenance_add(request):
    """Schedule a new maintenance or conservation work for an asset."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution before scheduling maintenance.")
        return redirect("trustee_institution_register")

    assets = Asset.objects.filter(institution=institution).order_by("name")
    preselected_asset_id = request.GET.get("asset_id")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        asset_id = request.POST.get("asset_id", "").strip()
        scheduled_date = request.POST.get("scheduled_date", "").strip()
        completion_date = request.POST.get("completion_date", "").strip() or None
        estimated_cost_raw = request.POST.get("estimated_cost", "0").strip()
        actual_cost_raw = request.POST.get("actual_cost", "0").strip()
        status = request.POST.get("status", "Scheduled").strip()

        errors = []
        if not title:
            errors.append("Maintenance title is required.")
        if not scheduled_date:
            errors.append("Scheduled date is required.")

        selected_asset = None
        if asset_id:
            try:
                selected_asset = assets.get(id=int(asset_id))
            except (ValueError, Asset.DoesNotExist):
                errors.append("Selected asset is invalid or does not belong to your institution.")

        valid_statuses = [choice[0] for choice in Maintenance.MAINTENANCE_STATUS]
        if status not in valid_statuses:
            status = "Scheduled"

        try:
            estimated_cost = Decimal(estimated_cost_raw) if estimated_cost_raw else Decimal("0.00")
            if estimated_cost < 0:
                errors.append("Estimated cost cannot be negative.")
        except Exception:
            errors.append("Please enter a valid numeric value for estimated cost.")
            estimated_cost = Decimal("0.00")

        try:
            actual_cost = Decimal(actual_cost_raw) if actual_cost_raw else Decimal("0.00")
            if actual_cost < 0:
                errors.append("Actual cost cannot be negative.")
        except Exception:
            errors.append("Please enter a valid numeric value for actual cost.")
            actual_cost = Decimal("0.00")

        if errors:
            return render(request, "trustee/maintenance_form.html", {
                "institution": institution,
                "assets": assets,
                "errors": errors,
                "form_data": request.POST,
                "is_edit": False,
                "maintenance_statuses": Maintenance.MAINTENANCE_STATUS,
            })

        maintenance = Maintenance.objects.create(
            institution=institution,
            asset=selected_asset,
            title=title,
            description=description,
            scheduled_date=scheduled_date,
            completion_date=completion_date,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            status=status,
        )

        AuditLog.objects.create(
            user=request.user,
            action="Maintenance Created",
            description=(
                f"Trustee '{request.user.username}' created maintenance record '{maintenance.title}' "
                f"(ID: {maintenance.id}, Scheduled: {maintenance.scheduled_date}, Status: {maintenance.status}) "
                f"for institution '{institution.name}'."
            ),
        )

        messages.success(request, f"Maintenance work '{maintenance.title}' scheduled successfully.")
        return redirect("trustee_maintenance_detail", maintenance_id=maintenance.id)

    return render(request, "trustee/maintenance_form.html", {
        "institution": institution,
        "assets": assets,
        "preselected_asset_id": preselected_asset_id,
        "is_edit": False,
        "maintenance_statuses": Maintenance.MAINTENANCE_STATUS,
    })


@trustee_required
def trustee_maintenance_detail(request, maintenance_id):
    """View detailed dossier for a maintenance record and linked asset."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    maintenance = get_object_or_404(
        Maintenance.objects.select_related("institution", "asset"),
        id=maintenance_id
    )
    if maintenance.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to view maintenance records belonging to another institution.</p>"
        )

    cost_variance = maintenance.actual_cost - maintenance.estimated_cost
    return render(request, "trustee/maintenance_detail.html", {
        "maintenance": maintenance,
        "institution": institution,
        "cost_variance": cost_variance,
    })


@trustee_required
def trustee_maintenance_edit(request, maintenance_id):
    """Update an existing maintenance record."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    maintenance = get_object_or_404(Maintenance, id=maintenance_id)
    if maintenance.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to edit maintenance records belonging to another institution.</p>"
        )

    assets = Asset.objects.filter(institution=institution).order_by("name")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        asset_id = request.POST.get("asset_id", "").strip()
        scheduled_date = request.POST.get("scheduled_date", "").strip()
        completion_date = request.POST.get("completion_date", "").strip() or None
        estimated_cost_raw = request.POST.get("estimated_cost", "0").strip()
        actual_cost_raw = request.POST.get("actual_cost", "0").strip()
        status = request.POST.get("status", "Scheduled").strip()

        errors = []
        if not title:
            errors.append("Maintenance title is required.")
        if not scheduled_date:
            errors.append("Scheduled date is required.")

        selected_asset = None
        if asset_id:
            try:
                selected_asset = assets.get(id=int(asset_id))
            except (ValueError, Asset.DoesNotExist):
                errors.append("Selected asset is invalid or does not belong to your institution.")

        valid_statuses = [choice[0] for choice in Maintenance.MAINTENANCE_STATUS]
        if status not in valid_statuses:
            status = maintenance.status

        try:
            estimated_cost = Decimal(estimated_cost_raw) if estimated_cost_raw else Decimal("0.00")
            if estimated_cost < 0:
                errors.append("Estimated cost cannot be negative.")
        except Exception:
            errors.append("Please enter a valid numeric value for estimated cost.")
            estimated_cost = maintenance.estimated_cost

        try:
            actual_cost = Decimal(actual_cost_raw) if actual_cost_raw else Decimal("0.00")
            if actual_cost < 0:
                errors.append("Actual cost cannot be negative.")
        except Exception:
            errors.append("Please enter a valid numeric value for actual cost.")
            actual_cost = maintenance.actual_cost

        if errors:
            return render(request, "trustee/maintenance_form.html", {
                "institution": institution,
                "maintenance": maintenance,
                "assets": assets,
                "errors": errors,
                "form_data": request.POST,
                "is_edit": True,
                "maintenance_statuses": Maintenance.MAINTENANCE_STATUS,
            })

        maintenance.title = title
        maintenance.description = description
        maintenance.asset = selected_asset
        maintenance.scheduled_date = scheduled_date
        maintenance.completion_date = completion_date
        maintenance.estimated_cost = estimated_cost
        maintenance.actual_cost = actual_cost
        maintenance.status = status
        maintenance.save()

        AuditLog.objects.create(
            user=request.user,
            action="Maintenance Updated",
            description=(
                f"Trustee '{request.user.username}' updated maintenance record '{maintenance.title}' "
                f"(ID: {maintenance.id}, Status: {maintenance.status}) "
                f"for institution '{institution.name}'."
            ),
        )

        messages.success(request, f"Maintenance work '{maintenance.title}' updated successfully.")
        return redirect("trustee_maintenance_detail", maintenance_id=maintenance.id)

    return render(request, "trustee/maintenance_form.html", {
        "institution": institution,
        "maintenance": maintenance,
        "assets": assets,
        "is_edit": True,
        "maintenance_statuses": Maintenance.MAINTENANCE_STATUS,
    })


@trustee_required
def trustee_maintenance_delete(request, maintenance_id):
    """Delete a maintenance record (POST + CSRF confirmation)."""
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        messages.warning(request, "Please register your institution first.")
        return redirect("trustee_institution_register")

    maintenance = get_object_or_404(Maintenance, id=maintenance_id)
    if maintenance.institution != institution:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to delete maintenance records belonging to another institution.</p>"
        )

    if request.method != "POST":
        return redirect("trustee_maintenance_detail", maintenance_id=maintenance_id)

    m_title = maintenance.title
    m_id_val = maintenance.id
    maintenance.delete()

    AuditLog.objects.create(
        user=request.user,
        action="Maintenance Deleted",
        description=(
            f"Trustee '{request.user.username}' deleted maintenance record '{m_title}' "
            f"(ID: {m_id_val}) from institution '{institution.name}'."
        ),
    )

    messages.success(request, f"Maintenance work '{m_title}' deleted successfully.")
    return redirect("trustee_maintenance_list")


# ──────────────────────────────────────────────
# TRUSTEE STAFF MONITORING — views
# ──────────────────────────────────────────────

@trustee_required
def trustee_staff_list(request):
    """
    Trustee Staff Monitoring page.
    Allows an approved Trustee to view operational Staff members belonging to
    their own affiliated institution in a strictly read-only view.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution

    if not institution:
        return render(request, "trustee/staff_list.html", {
            "profile": profile,
            "institution": None,
            "staff_members": [],
            "total_staff": 0,
            "approved_count": 0,
            "pending_count": 0,
            "rejected_count": 0,
            "search_query": "",
            "current_status": "",
        })

    # Restrict staff query strictly to Trustee's own institution
    staff_qs = (
        UserProfile.objects.filter(
            role="Staff",
            institution=institution,
        )
        .select_related("user", "institution")
        .order_by("-id")
    )

    # Metrics before filters
    total_staff = staff_qs.count()
    approved_count = staff_qs.filter(approval_status="Approved").count()
    pending_count = staff_qs.filter(approval_status="Pending").count()
    rejected_count = staff_qs.filter(approval_status="Rejected").count()

    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if search_query:
        staff_qs = staff_qs.filter(
            Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(phone__icontains=search_query)
        )

    if status_filter in ["Approved", "Pending", "Rejected"]:
        staff_qs = staff_qs.filter(approval_status=status_filter)

    return render(request, "trustee/staff_list.html", {
        "profile": profile,
        "institution": institution,
        "staff_members": staff_qs,
        "total_staff": total_staff,
        "approved_count": approved_count,
        "pending_count": pending_count,
        "rejected_count": rejected_count,
        "search_query": search_query,
        "current_status": status_filter,
    })


# ──────────────────────────────────────────────
# DEVOTEE MODULE — views
# ──────────────────────────────────────────────

@devotee_required
def devotee_dashboard(request):
    """Devotee landing page with donation stats and recent activity."""
    user_donations = Donation.objects.filter(donor=request.user)
    successful_donations = user_donations.filter(payment_status="Success")
    total_donations = successful_donations.count()
    total_amount = successful_donations.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    recent_donations = (
        user_donations
        .select_related("institution", "receipt")
        .order_by("-donation_date")[:5]
    )
    return render(request, "devotee/dashboard.html", {
        "total_donations": total_donations,
        "total_amount": total_amount,
        "recent_donations": recent_donations,
    })


@devotee_required
def devotee_donate(request):
    """GET: display donation form. POST: store data in session → redirect to payment."""
    institutions = Institution.objects.filter(approval_status="Approved")

    if request.method == "POST":
        institution_id = request.POST.get("institution")
        donor_name = request.POST.get("donor_name", "").strip()
        donor_email = request.POST.get("donor_email", "").strip()
        amount = request.POST.get("amount", "").strip()
        purpose = request.POST.get("purpose", "").strip()

        # Basic server-side validation
        errors = []
        if not institution_id:
            errors.append("Please select an institution.")
        else:
            if not Institution.objects.filter(id=institution_id, approval_status="Approved").exists():
                errors.append("Selected institution is not approved.")
        if not donor_name:
            errors.append("Donor name is required.")
        if not amount:
            errors.append("Amount is required.")
        else:
            try:
                amt = Decimal(amount)
                if amt < 1:
                    errors.append("Minimum donation amount is ₹1.")
            except Exception:
                errors.append("Invalid amount.")
        if not purpose:
            errors.append("Purpose is required.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "devotee/donate.html", {"institutions": institutions})

        # Store in session for the payment page
        request.session["donation_data"] = {
            "institution_id": int(institution_id),
            "donor_name": donor_name,
            "donor_email": donor_email,
            "amount": amount,
            "purpose": purpose,
        }
        return redirect("devotee_payment")

    return render(request, "devotee/donate.html", {"institutions": institutions})


@devotee_required
def devotee_payment(request):
    """GET: mock checkout UI.  POST: create Donation + Receipt + AuditLog."""
    donation_data = request.session.get("donation_data")
    if not donation_data:
        messages.warning(request, "No donation data found. Please fill in the donation form first.")
        return redirect("devotee_donate")

    # Resolve institution name for display
    try:
        institution = Institution.objects.get(
            id=donation_data["institution_id"],
            approval_status="Approved",
        )
    except Institution.DoesNotExist:
        messages.error(request, "The selected institution is no longer available.")
        return redirect("devotee_donate")

    if request.method == "POST":
        payment_method = request.POST.get("payment_method", "Mock UPI")
        transaction_id = f"HH-TXN-{uuid.uuid4().hex[:12].upper()}"

        # 1. Create Donation
        donation = Donation.objects.create(
            institution=institution,
            donor=request.user,
            donor_name=donation_data["donor_name"],
            donor_email=donation_data["donor_email"],
            amount=Decimal(donation_data["amount"]),
            donation_type="Online",
            purpose=donation_data["purpose"],
            payment_status="Success",
            transaction_id=transaction_id,
        )

        # 2. Create Receipt
        receipt_number = f"HH-REC-{donation.id:06d}"
        receipt = Receipt.objects.create(
            donation=donation,
            receipt_number=receipt_number,
        )

        # 3. Audit log — successful donation
        AuditLog.objects.create(
            user=request.user,
            action="Successful online donation",
            description=(
                f"Donor: {donation.donor_name}, Amount: ₹{donation.amount}, "
                f"Institution: {institution.name}, "
                f"Transaction ID: {transaction_id}, "
                f"Payment Method: {payment_method}"
            ),
        )

        # 4. Audit log — receipt generation
        AuditLog.objects.create(
            user=request.user,
            action="Receipt generation",
            description=(
                f"Receipt {receipt_number} generated for donation of "
                f"₹{donation.amount} to {institution.name}."
            ),
        )

        # 5. Clear session
        del request.session["donation_data"]

        messages.success(request, "Payment successful! Your receipt has been generated.")
        return redirect("devotee_receipt", receipt_id=receipt.id)

    # GET — render mock payment page
    context = {
        "donation_data": {
            "institution_name": institution.name,
            "donor_name": donation_data["donor_name"],
            "donor_email": donation_data["donor_email"],
            "amount": donation_data["amount"],
            "purpose": donation_data["purpose"],
        }
    }
    return render(request, "devotee/payment.html", context)


@devotee_required
def devotee_receipt(request, receipt_id):
    """Display a single receipt — only if it belongs to the current user."""
    receipt = get_object_or_404(
        Receipt.objects.select_related("donation", "donation__institution"),
        id=receipt_id,
    )
    if receipt.donation.donor != request.user:
        return HttpResponseForbidden(
            "<h2>403 — Forbidden</h2>"
            "<p>You are not authorized to view this receipt.</p>"
        )
    return render(request, "devotee/receipt.html", {"receipt": receipt})


@devotee_required
def devotee_donation_history(request):
    """List all donations made by the current user."""
    donations = (
        Donation.objects.filter(donor=request.user)
        .select_related("institution", "receipt")
        .order_by("-donation_date")
    )
    return render(request, "devotee/donation_history.html", {"donations": donations})


@devotee_required
def devotee_profile(request):
    """Show the Devotee's User + UserProfile information."""
    profile = get_object_or_404(UserProfile, user=request.user)
    return render(request, "devotee/profile.html", {"profile": profile})


# ──────────────────────────────────────────────
# Public Transparency Reports (Open Public Access)
# ──────────────────────────────────────────────

def public_transparency_reports(request):
    """
    Public Transparency Portal:
    Provides selected financial, asset, and maintenance disclosures for approved institutions.
    Strictly excludes sensitive personal donor data, credentials, and internal audit logs.
    """
    approved_institutions = Institution.objects.filter(approval_status="Approved").order_by("name")

    selected_inst_id = request.GET.get("institution")
    selected_institution = None

    if selected_inst_id:
        try:
            selected_institution = approved_institutions.filter(id=int(selected_inst_id)).first()
        except (ValueError, TypeError):
            selected_institution = None

    if not selected_institution and approved_institutions.exists():
        selected_institution = approved_institutions.first()

    context = {
        "approved_institutions": approved_institutions,
        "selected_institution": selected_institution,
        "total_donations": Decimal("0.00"),
        "online_donations": Decimal("0.00"),
        "cash_donations": Decimal("0.00"),
        "donations_count": 0,
        "approved_expenses": Decimal("0.00"),
        "available_funds": Decimal("0.00"),
        "total_assets": 0,
        "total_valuation": Decimal("0.00"),
        "condition_summary": [
            {"condition": "Excellent", "count": 0},
            {"condition": "Good", "count": 0},
            {"condition": "Needs Maintenance", "count": 0},
            {"condition": "Damaged", "count": 0},
        ],
        "total_maintenance": 0,
        "completed_maintenance": 0,
        "scheduled_maintenance": 0,
        "maintenance_expenditure": Decimal("0.00"),
    }

    if selected_institution:
        # Financial disclosures (successful donations only)
        donations_qs = Donation.objects.filter(institution=selected_institution, payment_status="Success")
        total_donations = donations_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
        online_donations = donations_qs.filter(donation_type="Online").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
        cash_donations = donations_qs.filter(donation_type="Cash").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
        donations_count = donations_qs.count()

        approved_expenses = (
            Expense.objects.filter(institution=selected_institution, status="Approved")
            .aggregate(t=Sum("amount"))["t"]
            or Decimal("0.00")
        )
        available_funds = total_donations - approved_expenses

        # Asset disclosures
        assets_qs = Asset.objects.filter(institution=selected_institution)
        total_assets = assets_qs.count()
        total_valuation = assets_qs.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00")
        condition_summary = [
            {"condition": "Excellent", "count": assets_qs.filter(condition="Excellent").count()},
            {"condition": "Good", "count": assets_qs.filter(condition="Good").count()},
            {"condition": "Needs Maintenance", "count": assets_qs.filter(condition="Needs Maintenance").count()},
            {"condition": "Damaged", "count": assets_qs.filter(condition="Damaged").count()},
        ]

        # Maintenance disclosures
        maint_qs = Maintenance.objects.filter(institution=selected_institution)
        total_maint = maint_qs.count()
        completed_maint = maint_qs.filter(status="Completed").count()
        scheduled_maint = maint_qs.filter(status="Scheduled").count()
        maintenance_expenditure = maint_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

        context.update({
            "total_donations": total_donations,
            "online_donations": online_donations,
            "cash_donations": cash_donations,
            "donations_count": donations_count,
            "approved_expenses": approved_expenses,
            "available_funds": available_funds,
            "total_assets": total_assets,
            "total_valuation": total_valuation,
            "condition_summary": condition_summary,
            "total_maintenance": total_maint,
            "completed_maintenance": completed_maint,
            "scheduled_maintenance": scheduled_maint,
            "maintenance_expenditure": maintenance_expenditure,
        })

    return render(request, "common/transparency_reports.html", context)


# ──────────────────────────────────────────────
# Trustee Reporting & Executive Dashboards
# ──────────────────────────────────────────────

@trustee_required
def trustee_reports_overview(request):
    """
    Main Trustee Reports & Analytics Overview Dashboard:
    Computes key executive governance metrics across Donations, Expenses, Available Funds,
    Assets, Events, and Maintenance for the Trustee's registered institution.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "trustee/reports/no_institution.html", {})

    # 1. Financial KPIs
    donations_qs = Donation.objects.filter(institution=institution, payment_status="Success")
    total_donations = donations_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    total_donations_count = donations_qs.count()

    approved_expenses = (
        Expense.objects.filter(institution=institution, status="Approved")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    pending_expenses = (
        Expense.objects.filter(institution=institution, status="Pending")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    pending_expenses_count = Expense.objects.filter(institution=institution, status="Pending").count()
    available_funds = total_donations - approved_expenses

    # 2. Asset KPIs
    assets_qs = Asset.objects.filter(institution=institution)
    total_assets = assets_qs.count()
    total_valuation = assets_qs.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00")
    needs_maintenance_count = assets_qs.filter(condition__in=["Needs Maintenance", "Damaged"]).count()

    # 3. Event KPIs
    events_qs = Event.objects.filter(institution=institution)
    upcoming_events_count = events_qs.filter(status__in=["Scheduled", "Ongoing"]).count()
    total_events_count = events_qs.count()
    total_event_cost = events_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

    # 4. Maintenance KPIs
    maint_qs = Maintenance.objects.filter(institution=institution)
    total_maintenance_count = maint_qs.count()
    scheduled_maint_count = maint_qs.filter(status="Scheduled").count()
    in_progress_maint_count = maint_qs.filter(status="In Progress").count()
    completed_maint_count = maint_qs.filter(status="Completed").count()
    total_maint_cost = maint_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

    context = {
        "institution": institution,
        "active_report": "overview",
        "total_donations": total_donations,
        "total_donations_count": total_donations_count,
        "approved_expenses": approved_expenses,
        "pending_expenses": pending_expenses,
        "pending_expenses_count": pending_expenses_count,
        "available_funds": available_funds,
        "total_assets": total_assets,
        "total_valuation": total_valuation,
        "needs_maintenance_count": needs_maintenance_count,
        "upcoming_events_count": upcoming_events_count,
        "total_events_count": total_events_count,
        "total_event_cost": total_event_cost,
        "total_maintenance_count": total_maintenance_count,
        "scheduled_maint_count": scheduled_maint_count,
        "in_progress_maint_count": in_progress_maint_count,
        "completed_maint_count": completed_maint_count,
        "total_maint_cost": total_maint_cost,
    }
    return render(request, "trustee/reports/overview.html", context)


@trustee_required
def trustee_reports_donations(request):
    """
    Donation Trends & Analysis Report:
    Monthly donation progression, online vs cash breakdown, and full institutional donation ledger.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "trustee/reports/no_institution.html", {})

    all_donations_qs = Donation.objects.filter(institution=institution).order_by("-donation_date")
    successful_donations_qs = all_donations_qs.filter(payment_status="Success")

    total_successful = successful_donations_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    online_total = (
        successful_donations_qs.filter(donation_type="Online")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    cash_total = (
        successful_donations_qs.filter(donation_type="Cash")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )

    successful_count = successful_donations_qs.count()
    online_count = successful_donations_qs.filter(donation_type="Online").count()
    cash_count = successful_donations_qs.filter(donation_type="Cash").count()

    # Monthly aggregation for trend display
    chronological_donations = successful_donations_qs.order_by("donation_date")
    month_map = {}
    for d in chronological_donations:
        m_key = d.donation_date.strftime("%b %Y")
        month_map[m_key] = month_map.get(m_key, Decimal("0.00")) + d.amount

    monthly_labels = list(month_map.keys())
    monthly_values = [float(v) for v in month_map.values()]
    monthly_trends = [{"month": k, "amount": v} for k, v in month_map.items()]

    context = {
        "institution": institution,
        "active_report": "donations",
        "total_successful": total_successful,
        "online_total": online_total,
        "cash_total": cash_total,
        "successful_count": successful_count,
        "online_count": online_count,
        "cash_count": cash_count,
        "monthly_labels": monthly_labels,
        "monthly_values": monthly_values,
        "monthly_trends": monthly_trends,
        "donations": all_donations_qs[:100],
    }
    return render(request, "trustee/reports/donations.html", context)


@trustee_required
def trustee_reports_finance(request):
    """
    Fund Utilization & Expenditure Report:
    Received vs Utilized vs Available funds, utilization percentage, expense category breakdown,
    and institutional expense audit ledger.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "trustee/reports/no_institution.html", {})

    received_funds = (
        Donation.objects.filter(institution=institution, payment_status="Success")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    utilized_funds = (
        Expense.objects.filter(institution=institution, status="Approved")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    available_funds = received_funds - utilized_funds

    pending_expenses = (
        Expense.objects.filter(institution=institution, status="Pending")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    pending_count = Expense.objects.filter(institution=institution, status="Pending").count()

    rejected_expenses = (
        Expense.objects.filter(institution=institution, status="Rejected")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    rejected_count = Expense.objects.filter(institution=institution, status="Rejected").count()

    utilization_pct = round(float(utilized_funds / received_funds * 100), 1) if received_funds > 0 else 0.0

    category_summary = list(
        Expense.objects.filter(institution=institution, status="Approved")
        .values("category")
        .annotate(total_amount=Sum("amount"), count=Count("id"))
        .order_by("-total_amount")
    )

    expenses = (
        Expense.objects.filter(institution=institution)
        .select_related("approved_by", "donation")
        .order_by("-expense_date")
    )

    context = {
        "institution": institution,
        "active_report": "finance",
        "received_funds": received_funds,
        "utilized_funds": utilized_funds,
        "available_funds": available_funds,
        "pending_expenses": pending_expenses,
        "pending_count": pending_count,
        "rejected_expenses": rejected_expenses,
        "rejected_count": rejected_count,
        "utilization_pct": utilization_pct,
        "category_summary": category_summary,
        "expenses": expenses[:100],
    }
    return render(request, "trustee/reports/finance.html", context)


@trustee_required
def trustee_reports_assets(request):
    """
    Asset Valuation & Condition Audit Report:
    Movable vs Immovable distribution, condition health breakdown, and complete institutional asset inventory.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "trustee/reports/no_institution.html", {})

    assets_qs = Asset.objects.filter(institution=institution)
    total_assets = assets_qs.count()
    total_valuation = assets_qs.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00")

    movable_qs = assets_qs.filter(asset_type="Movable")
    movable_count = movable_qs.count()
    movable_valuation = movable_qs.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00")

    immovable_qs = assets_qs.filter(asset_type="Immovable")
    immovable_count = immovable_qs.count()
    immovable_valuation = immovable_qs.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00")

    conditions = ["Excellent", "Good", "Needs Maintenance", "Damaged"]
    condition_summary = []
    for cond in conditions:
        c_qs = assets_qs.filter(condition=cond)
        condition_summary.append({
            "condition": cond,
            "count": c_qs.count(),
            "valuation": c_qs.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00"),
        })

    assets = assets_qs.order_by("-current_valuation")

    context = {
        "institution": institution,
        "active_report": "assets",
        "total_assets": total_assets,
        "total_valuation": total_valuation,
        "movable_count": movable_count,
        "movable_valuation": movable_valuation,
        "immovable_count": immovable_count,
        "immovable_valuation": immovable_valuation,
        "condition_summary": condition_summary,
        "assets": assets,
    }
    return render(request, "trustee/reports/assets.html", context)


@trustee_required
def trustee_reports_maintenance(request):
    """
    Maintenance Activities & Conservation Report:
    Scheduled vs in-progress vs completed works, actual vs estimated costs, and linked asset conservation history.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "trustee/reports/no_institution.html", {})

    maint_qs = Maintenance.objects.filter(institution=institution)
    total_maintenance = maint_qs.count()

    scheduled_count = maint_qs.filter(status="Scheduled").count()
    in_progress_count = maint_qs.filter(status="In Progress").count()
    completed_count = maint_qs.filter(status="Completed").count()
    cancelled_count = maint_qs.filter(status="Cancelled").count()

    total_actual_cost = maint_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")
    total_estimated_cost = maint_qs.aggregate(t=Sum("estimated_cost"))["t"] or Decimal("0.00")

    maintenance_records = maint_qs.select_related("asset").order_by("-scheduled_date")

    context = {
        "institution": institution,
        "active_report": "maintenance",
        "total_maintenance": total_maintenance,
        "scheduled_count": scheduled_count,
        "in_progress_count": in_progress_count,
        "completed_count": completed_count,
        "cancelled_count": cancelled_count,
        "total_actual_cost": total_actual_cost,
        "total_estimated_cost": total_estimated_cost,
        "maintenance_records": maintenance_records,
    }
    return render(request, "trustee/reports/maintenance.html", context)


@trustee_required
def trustee_reports_summary(request):
    """
    Consolidated Institutional Report:
    Comprehensive printable report with complete Institution, Financial, Asset, Event,
    and Maintenance summaries, and direct link to generate official PDF.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return render(request, "trustee/reports/no_institution.html", {})

    # Financial
    donations_qs = Donation.objects.filter(institution=institution, payment_status="Success")
    received_funds = donations_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    donations_count = donations_qs.count()

    approved_expenses = (
        Expense.objects.filter(institution=institution, status="Approved")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    pending_expenses = (
        Expense.objects.filter(institution=institution, status="Pending")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    available_funds = received_funds - approved_expenses

    # Assets
    assets_qs = Asset.objects.filter(institution=institution)
    total_assets = assets_qs.count()
    movable_count = assets_qs.filter(asset_type="Movable").count()
    immovable_count = assets_qs.filter(asset_type="Immovable").count()
    total_valuation = assets_qs.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00")

    # Events
    events_qs = Event.objects.filter(institution=institution)
    total_events = events_qs.count()
    scheduled_events = events_qs.filter(status="Scheduled").count()
    ongoing_events = events_qs.filter(status="Ongoing").count()
    completed_events = events_qs.filter(status="Completed").count()
    cancelled_events = events_qs.filter(status="Cancelled").count()
    event_estimated_cost = events_qs.aggregate(t=Sum("estimated_cost"))["t"] or Decimal("0.00")
    event_actual_cost = events_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

    # Maintenance
    maint_qs = Maintenance.objects.filter(institution=institution)
    total_maintenance = maint_qs.count()
    scheduled_maint = maint_qs.filter(status="Scheduled").count()
    in_progress_maint = maint_qs.filter(status="In Progress").count()
    completed_maint = maint_qs.filter(status="Completed").count()
    cancelled_maint = maint_qs.filter(status="Cancelled").count()
    maint_estimated_cost = maint_qs.aggregate(t=Sum("estimated_cost"))["t"] or Decimal("0.00")
    maint_actual_cost = maint_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

    now = timezone.now()
    generated_by = request.user.get_full_name() or request.user.username

    context = {
        "institution": institution,
        "active_report": "summary",
        "generated_date": now,
        "generated_by": generated_by,
        # Financial
        "received_funds": received_funds,
        "donations_count": donations_count,
        "approved_expenses": approved_expenses,
        "pending_expenses": pending_expenses,
        "available_funds": available_funds,
        # Assets
        "total_assets": total_assets,
        "movable_count": movable_count,
        "immovable_count": immovable_count,
        "total_valuation": total_valuation,
        # Events
        "total_events": total_events,
        "scheduled_events": scheduled_events,
        "ongoing_events": ongoing_events,
        "completed_events": completed_events,
        "cancelled_events": cancelled_events,
        "event_estimated_cost": event_estimated_cost,
        "event_actual_cost": event_actual_cost,
        "recent_events": events_qs.order_by("-date")[:5],
        # Maintenance
        "total_maintenance": total_maintenance,
        "scheduled_maint": scheduled_maint,
        "in_progress_maint": in_progress_maint,
        "completed_maint": completed_maint,
        "cancelled_maint": cancelled_maint,
        "maint_estimated_cost": maint_estimated_cost,
        "maint_actual_cost": maint_actual_cost,
        "recent_maintenance": maint_qs.select_related("asset").order_by("-scheduled_date")[:5],
    }
    return render(request, "trustee/reports/summary.html", context)


@trustee_required
def trustee_reports_summary_pdf(request):
    """
    Generate and stream an official PDF Consolidated Report using ReportLab.
    Strictly scoped to the Trustee's registered institution.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    institution = profile.institution
    if not institution:
        return HttpResponseForbidden("<h2>403 — Forbidden</h2><p>No institution assigned to this trustee account.</p>")

    # Financial
    donations_qs = Donation.objects.filter(institution=institution, payment_status="Success")
    received_funds = donations_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    donations_count = donations_qs.count()
    approved_expenses = (
        Expense.objects.filter(institution=institution, status="Approved")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    pending_expenses = (
        Expense.objects.filter(institution=institution, status="Pending")
        .aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    available_funds = received_funds - approved_expenses

    # Assets
    assets_qs = Asset.objects.filter(institution=institution)
    total_assets = assets_qs.count()
    movable_count = assets_qs.filter(asset_type="Movable").count()
    immovable_count = assets_qs.filter(asset_type="Immovable").count()
    total_valuation = assets_qs.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00")

    # Events
    events_qs = Event.objects.filter(institution=institution)
    total_events = events_qs.count()
    scheduled_events = events_qs.filter(status="Scheduled").count()
    completed_events = events_qs.filter(status="Completed").count()
    event_actual_cost = events_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

    # Maintenance
    maint_qs = Maintenance.objects.filter(institution=institution)
    total_maintenance = maint_qs.count()
    scheduled_maint = maint_qs.filter(status="Scheduled").count()
    completed_maint = maint_qs.filter(status="Completed").count()
    maint_actual_cost = maint_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

    now = timezone.now()
    generated_by = request.user.get_full_name() or request.user.username

    # Build PDF with ReportLab
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()

    primary_color = colors.HexColor('#9A3412')
    gold_color = colors.HexColor('#D97706')
    dark_color = colors.HexColor('#1C1917')
    border_color = colors.HexColor('#E7E5E4')
    header_bg = colors.HexColor('#FBFBF9')

    title_style = ParagraphStyle(
        'RepTitle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=primary_color, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        'RepSub', parent=styles['Normal'], fontSize=9, leading=12, textColor=dark_color, spaceAfter=8
    )
    section_style = ParagraphStyle(
        'RepSection', parent=styles['Heading2'], fontSize=11, leading=14, textColor=primary_color, spaceBefore=8, spaceAfter=4
    )
    body_style = ParagraphStyle('RepBody', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=dark_color)

    story = [
        Paragraph("HeritageHub — Cultural Heritage Asset & Trust MIS", title_style),
        Paragraph(f"Consolidated Institutional Governance & Audit Report: <b>{institution.name}</b>", sub_style),
        Paragraph(f"Generated on {now.strftime('%d %b %Y, %I:%M %p')} | Prepared by Trustee: {generated_by}", body_style),
        HRFlowable(width="100%", thickness=2, color=gold_color, spaceBefore=6, spaceAfter=8),
    ]

    # Institution Profile Table
    inst_data = [
        [Paragraph("<b>Institution Name</b>", body_style), Paragraph(str(institution.name), body_style),
         Paragraph("<b>Type</b>", body_style), Paragraph(str(institution.get_institution_type_display()), body_style)],
        [Paragraph("<b>Representative</b>", body_style), Paragraph(str(institution.authorized_representative), body_style),
         Paragraph("<b>Contact</b>", body_style), Paragraph(str(institution.contact_number), body_style)],
        [Paragraph("<b>Address</b>", body_style), Paragraph(str(institution.address), body_style),
         Paragraph("<b>Email</b>", body_style), Paragraph(str(institution.email), body_style)],
    ]
    t_inst = Table(inst_data, colWidths=[110, 160, 80, 190])
    t_inst.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), header_bg),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_inst)
    story.append(Spacer(1, 8))

    # Financial Summary Table
    story.append(Paragraph("1. Financial Summary & Fund Utilization", section_style))
    fin_data = [
        ["Financial Metric", "Amount (INR)", "Status / Notes"],
        ["Total Received Donations", f"INR {received_funds:,.2f}", f"{donations_count} verified transaction(s)"],
        ["Approved Expenditures", f"INR {approved_expenses:,.2f}", "Authorized disbursements"],
        ["Net Available Funds", f"INR {available_funds:,.2f}", "Disbursement balance"],
        ["Pending Clearances", f"INR {pending_expenses:,.2f}", "Reserved awaiting trustee action"],
    ]
    t_fin = Table(fin_data, colWidths=[200, 140, 200])
    t_fin.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, header_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_fin)
    story.append(Spacer(1, 8))

    # Asset Summary Table
    story.append(Paragraph("2. Asset Valuation & Inventory", section_style))
    asset_data = [
        ["Asset Classification", "Count", "Current Valuation (INR)"],
        ["Movable Assets", str(movable_count), "Included in total"],
        ["Immovable Assets", str(immovable_count), "Included in total"],
        ["Total Registered Assets", str(total_assets), f"INR {total_valuation:,.2f}"],
    ]
    t_asset = Table(asset_data, colWidths=[200, 140, 200])
    t_asset.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, header_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_asset)
    story.append(Spacer(1, 8))

    # Operations Table
    story.append(Paragraph("3. Cultural Events & Maintenance Works", section_style))
    ops_data = [
        ["Operational Category", "Total Count", "Completed", "Expenditure (INR)"],
        ["Events & Festivals", str(total_events), str(completed_events), f"INR {event_actual_cost:,.2f}"],
        ["Maintenance Works", str(total_maintenance), str(completed_maint), f"INR {maint_actual_cost:,.2f}"],
    ]
    t_ops = Table(ops_data, colWidths=[200, 100, 100, 140])
    t_ops.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, header_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_ops)
    story.append(Spacer(1, 12))

    cert_text = "This document is an official computer-generated governance report from HeritageHub MIS. All figures reflect authoritative database records as of the generation timestamp."
    story.append(Paragraph(cert_text, ParagraphStyle('Cert', parent=styles['Italic'], fontSize=8, leading=10, textColor=colors.HexColor('#78716C'))))

    doc.build(story)

    response = HttpResponse(buf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="HeritageHub_Consolidated_Report_{institution.id}.pdf"'
    return response


# ──────────────────────────────────────────────
# SYSTEM ADMINISTRATOR — Application Admin Portal Views
# (Full system-wide business administration, user & institution approvals, cross-institutional monitoring)
# ──────────────────────────────────────────────

@admin_required
def admin_dashboard(request):
    """
    Central administrative dashboard providing macro KPI metrics, pending action
    alerts (Trustees, Staff, Institutions), and system monitoring summaries.
    """
    all_institutions = Institution.objects.all().order_by("-registered_date")
    total_institutions = all_institutions.count()
    approved_inst_count = all_institutions.filter(approval_status="Approved").count()
    pending_inst_count = all_institutions.filter(approval_status="Pending").count()
    rejected_inst_count = all_institutions.filter(approval_status="Rejected").count()

    all_profiles = UserProfile.objects.select_related("user", "institution").all()
    total_users = all_profiles.count()
    trustee_count = all_profiles.filter(role="Trustee").count()
    staff_count = all_profiles.filter(role="Staff").count()
    devotee_count = all_profiles.filter(role="Devotee").count()

    pending_users_qs = all_profiles.filter(role__in=["Trustee", "Staff"], approval_status="Pending")
    pending_users_count = pending_users_qs.count()
    pending_users = pending_users_qs.order_by("-id")[:5]

    successful_donations = Donation.objects.filter(payment_status="Success")
    total_donations_sum = successful_donations.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    successful_donations_count = successful_donations.count()

    approved_expenses = Expense.objects.filter(status="Approved")
    total_expenses_sum = approved_expenses.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    expenses_count = Expense.objects.count()

    total_assets_count = Asset.objects.count()
    total_assets_valuation = Asset.objects.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00")

    total_maintenance_count = Maintenance.objects.count()
    active_maintenance_count = Maintenance.objects.filter(status__in=["Scheduled", "In Progress"]).count()
    completed_maintenance_count = Maintenance.objects.filter(status="Completed").count()

    total_events_count = Event.objects.count()
    upcoming_events_count = Event.objects.filter(status__in=["Scheduled", "Ongoing"]).count()

    total_audit_logs_count = AuditLog.objects.count()
    recent_audit_logs = AuditLog.objects.select_related("user").order_by("-timestamp")[:8]

    context = {
        "total_institutions": total_institutions,
        "approved_inst_count": approved_inst_count,
        "pending_inst_count": pending_inst_count,
        "rejected_inst_count": rejected_inst_count,
        "total_users": total_users,
        "trustee_count": trustee_count,
        "staff_count": staff_count,
        "devotee_count": devotee_count,
        "pending_users_count": pending_users_count,
        "pending_users": pending_users,
        "total_donations_sum": total_donations_sum,
        "successful_donations_count": successful_donations_count,
        "total_expenses_sum": total_expenses_sum,
        "expenses_count": expenses_count,
        "total_assets_count": total_assets_count,
        "total_assets_valuation": total_assets_valuation,
        "total_maintenance_count": total_maintenance_count,
        "active_maintenance_count": active_maintenance_count,
        "completed_maintenance_count": completed_maintenance_count,
        "total_events_count": total_events_count,
        "upcoming_events_count": upcoming_events_count,
        "total_audit_logs_count": total_audit_logs_count,
        "recent_audit_logs": recent_audit_logs,
    }
    return render(request, "admin_portal/dashboard.html", context)


@admin_required
def admin_user_approval_list(request):
    """
    Dedicated management queue for reviewing and verifying pending Trustee and Staff registrations.
    """
    status_filter = request.GET.get("status", "Pending").strip()
    role_filter = request.GET.get("role", "").strip()
    search_query = request.GET.get("q", "").strip()

    base_qs = UserProfile.objects.filter(role__in=["Trustee", "Staff"]).select_related("user", "institution").order_by("-id")

    pending_count = base_qs.filter(approval_status="Pending").count()
    approved_count = base_qs.filter(approval_status="Approved").count()
    rejected_count = base_qs.filter(approval_status="Rejected").count()
    total_count = base_qs.count()

    profiles = base_qs
    if status_filter in ["Pending", "Approved", "Rejected"]:
        profiles = profiles.filter(approval_status=status_filter)

    if role_filter in ["Trustee", "Staff"]:
        profiles = profiles.filter(role=role_filter)

    if search_query:
        profiles = profiles.filter(
            Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(institution__name__icontains=search_query)
        )

    context = {
        "profiles": profiles,
        "current_status": status_filter,
        "current_role": role_filter,
        "search_query": search_query,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "total_count": total_count,
    }
    return render(request, "admin_portal/user_approvals.html", context)


@admin_required
def admin_user_approve(request, user_id):
    """Approve a Trustee or Staff registration request (POST only)."""
    if request.method != "POST":
        messages.warning(request, "Invalid request method. User approval must be submitted via POST.")
        return redirect("admin_user_approval_list")

    target_profile = get_object_or_404(
        UserProfile.objects.select_related("user", "institution"),
        user_id=user_id,
        role__in=["Trustee", "Staff"],
    )

    # 1. Prevent Administrator from modifying their own account
    if target_profile.user_id == request.user.id:
        messages.error(request, "Administrators cannot modify the approval status of their own account.")
        return redirect("admin_user_approval_list")

    # 2. Prevent approving Staff without an approved institution
    if target_profile.role == "Staff":
        if not target_profile.institution or target_profile.institution.approval_status != "Approved":
            inst_name = target_profile.institution.name if target_profile.institution else "None"
            inst_status = target_profile.institution.approval_status if target_profile.institution else "Not Associated"
            messages.error(
                request,
                f"Cannot approve Staff member '{target_profile.user.username}' because the affiliated "
                f"institution '{inst_name}' is currently {inst_status}. The institution must be approved before staff can be approved."
            )
            return redirect("admin_user_approval_list")

    if target_profile.approval_status == "Approved":
        messages.info(request, f"User '{target_profile.user.username}' is already Approved.")
        return redirect("admin_user_approval_list")

    old_status = target_profile.approval_status
    target_profile.approval_status = "Approved"
    target_profile.save()

    AuditLog.objects.create(
        user=request.user,
        action=f"{target_profile.role} Registration Approved",
        description=(
            f"System Administrator '{request.user.username}' approved {target_profile.role} "
            f"account for '{target_profile.user.username}' (Profile ID: {target_profile.id}, User ID: {target_profile.user.id}). "
            f"Status changed from '{old_status}' to 'Approved'."
            + (f" Affiliated Institution: '{target_profile.institution.name}'." if target_profile.institution else "")
        ),
    )

    messages.success(
        request,
        f"{target_profile.role} account for '{target_profile.user.username}' has been approved successfully."
    )
    return redirect("admin_user_approval_list")


@admin_required
def admin_user_reject(request, user_id):
    """Reject a Trustee or Staff registration request (POST only)."""
    if request.method != "POST":
        messages.warning(request, "Invalid request method. User rejection must be submitted via POST.")
        return redirect("admin_user_approval_list")

    target_profile = get_object_or_404(
        UserProfile.objects.select_related("user", "institution"),
        user_id=user_id,
        role__in=["Trustee", "Staff"],
    )

    # Prevent Administrator from modifying their own account
    if target_profile.user_id == request.user.id:
        messages.error(request, "Administrators cannot modify the approval status of their own account.")
        return redirect("admin_user_approval_list")

    if target_profile.approval_status == "Rejected":
        messages.info(request, f"User '{target_profile.user.username}' is already Rejected.")
        return redirect("admin_user_approval_list")

    old_status = target_profile.approval_status
    target_profile.approval_status = "Rejected"
    target_profile.save()

    AuditLog.objects.create(
        user=request.user,
        action=f"{target_profile.role} Registration Rejected",
        description=(
            f"System Administrator '{request.user.username}' marked {target_profile.role} "
            f"account for '{target_profile.user.username}' (Profile ID: {target_profile.id}, User ID: {target_profile.user.id}) as Rejected. "
            f"Status changed from '{old_status}' to 'Rejected'."
            + (f" Affiliated Institution: '{target_profile.institution.name}'." if target_profile.institution else "")
        ),
    )

    messages.warning(
        request,
        f"{target_profile.role} account for '{target_profile.user.username}' has been marked as Rejected."
    )
    return redirect("admin_user_approval_list")


@admin_required
def admin_user_list(request):
    """
    Cross-institutional directory of all user accounts with search and filtering by role and status.
    """
    search_query = request.GET.get("q", "").strip()
    selected_role = request.GET.get("role", "").strip()
    selected_status = request.GET.get("status", "").strip()

    users_qs = User.objects.select_related("userprofile", "userprofile__institution").order_by("-id")

    if search_query:
        users_qs = users_qs.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if selected_role in ["Admin", "Trustee", "Staff", "Devotee"]:
        users_qs = users_qs.filter(userprofile__role=selected_role)

    if selected_status in ["Approved", "Pending", "Rejected"]:
        users_qs = users_qs.filter(userprofile__approval_status=selected_status)

    total_count = users_qs.count()

    context = {
        "users": users_qs,
        "total_count": total_count,
        "search_query": search_query,
        "selected_role": selected_role,
        "selected_status": selected_status,
    }
    return render(request, "admin_portal/users.html", context)


@admin_required
def admin_institution_list(request):
    """Lists institutions with status filtering and action controls for Admin review."""
    status_filter = request.GET.get("status", "all").strip()

    all_institutions = Institution.objects.all().order_by("-registered_date")
    total_count = all_institutions.count()
    pending_count = all_institutions.filter(approval_status="Pending").count()
    approved_count = all_institutions.filter(approval_status="Approved").count()
    rejected_count = all_institutions.filter(approval_status="Rejected").count()

    if status_filter in ["Pending", "Approved", "Rejected"]:
        institutions = all_institutions.filter(approval_status=status_filter)
    else:
        institutions = all_institutions

    context = {
        "institutions": institutions,
        "total_count": total_count,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "current_filter": status_filter,
    }
    return render(request, "admin_portal/institutions.html", context)


@admin_required
def admin_institution_detail(request, institution_id):
    """Inspection dossier for a heritage institution."""
    institution = get_object_or_404(Institution, id=institution_id)

    trustees = UserProfile.objects.filter(institution=institution, role="Trustee").select_related("user")
    staff_members = UserProfile.objects.filter(institution=institution, role="Staff").select_related("user")

    inst_assets = Asset.objects.filter(institution=institution)
    assets_count = inst_assets.count()
    total_valuation = inst_assets.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00")

    inst_donations = Donation.objects.filter(institution=institution, payment_status="Success")
    donations_count = inst_donations.count()
    donations_total = inst_donations.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    inst_expenses = Expense.objects.filter(institution=institution, status="Approved")
    expenses_count = inst_expenses.count()
    expenses_total = inst_expenses.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    context = {
        "institution": institution,
        "trustees": trustees,
        "staff_members": staff_members,
        "assets_count": assets_count,
        "total_valuation": total_valuation,
        "donations_count": donations_count,
        "donations_total": donations_total,
        "expenses_count": expenses_count,
        "expenses_total": expenses_total,
    }
    return render(request, "admin_portal/institution_detail.html", context)


@admin_required
def admin_institution_approve(request, institution_id):
    """System Administrator verifies and approves a pending institution (POST only)."""
    institution = get_object_or_404(Institution, id=institution_id)
    if request.method != "POST":
        messages.warning(request, "Invalid request method for institution approval. Action must be submitted via POST.")
        return redirect("admin_institution_list")

    if institution.approval_status != "Pending":
        messages.error(
            request,
            f"Cannot approve '{institution.name}'. Only institutions with 'Pending' status can be verified (current status: '{institution.approval_status}')."
        )
        return redirect("admin_institution_list")

    old_status = institution.approval_status
    institution.approval_status = "Approved"
    institution.save()

    AuditLog.objects.create(
        user=request.user,
        action="Institution Approved",
        description=(
            f"System Administrator '{request.user.username}' approved "
            f"institution '{institution.name}' (ID: {institution.id}). Status changed from '{old_status}' to 'Approved'."
        ),
    )

    messages.success(
        request,
        f"Institution '{institution.name}' has been verified and approved by the System Administrator. It is now active on the public portal."
    )
    return redirect("admin_institution_list")


@admin_required
def admin_institution_reject(request, institution_id):
    """System Administrator rejects an institution application (POST only)."""
    institution = get_object_or_404(Institution, id=institution_id)
    if request.method != "POST":
        messages.warning(request, "Invalid request method for institution rejection. Action must be submitted via POST.")
        return redirect("admin_institution_list")

    if institution.approval_status != "Pending":
        messages.error(
            request,
            f"Cannot reject '{institution.name}'. Only institutions with 'Pending' status can be rejected (current status: '{institution.approval_status}')."
        )
        return redirect("admin_institution_list")

    old_status = institution.approval_status
    institution.approval_status = "Rejected"
    institution.save()

    AuditLog.objects.create(
        user=request.user,
        action="Institution Rejected",
        description=(
            f"System Administrator '{request.user.username}' rejected "
            f"institution '{institution.name}' (ID: {institution.id}). Status changed from '{old_status}' to 'Rejected'."
        ),
    )

    messages.warning(
        request,
        f"Institution '{institution.name}' application has been marked as Rejected by the System Administrator."
    )
    return redirect("admin_institution_list")


@admin_required
def admin_asset_list(request):
    """Cross-institutional cultural asset monitoring with filters."""
    institutions = Institution.objects.filter(approval_status="Approved").order_by("name")
    assets = Asset.objects.select_related("institution").order_by("-id")

    institution_id = request.GET.get("institution", "").strip()
    if institution_id.isdigit():
        assets = assets.filter(institution_id=int(institution_id))

    condition = request.GET.get("condition", "").strip()
    if condition in ["Excellent", "Good", "Needs Maintenance", "Damaged"]:
        assets = assets.filter(condition=condition)

    asset_type = request.GET.get("asset_type", "").strip()
    if asset_type in ["Movable", "Immovable"]:
        assets = assets.filter(asset_type=asset_type)

    total_assets = assets.count()
    total_valuation = assets.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00")

    context = {
        "assets": assets,
        "institutions": institutions,
        "selected_institution": int(institution_id) if institution_id.isdigit() else "",
        "selected_condition": condition,
        "selected_type": asset_type,
        "total_assets": total_assets,
        "total_valuation": total_valuation,
    }
    return render(request, "admin_portal/assets.html", context)


@admin_required
def admin_asset_detail(request, asset_id):
    """Read-only inspection dossier for a specific cultural heritage asset."""
    asset = get_object_or_404(Asset.objects.select_related("institution"), id=asset_id)
    maintenance_records = Maintenance.objects.filter(asset=asset).order_by("-scheduled_date")

    context = {
        "asset": asset,
        "maintenance_records": maintenance_records,
    }
    return render(request, "admin_portal/asset_detail.html", context)


@admin_required
def admin_donation_list(request):
    """Cross-institutional donations & receipts monitoring with financial aggregates."""
    institutions = Institution.objects.filter(approval_status="Approved").order_by("name")
    donations = Donation.objects.select_related("institution", "receipt").order_by("-donation_date")

    institution_id = request.GET.get("institution", "").strip()
    if institution_id.isdigit():
        donations = donations.filter(institution_id=int(institution_id))

    donation_type = request.GET.get("type", "").strip()
    if donation_type in ["Online", "Cash"]:
        donations = donations.filter(donation_type=donation_type)

    status = request.GET.get("status", "").strip()
    if status in ["Success", "Pending", "Failed"]:
        donations = donations.filter(payment_status=status)

    total_count = donations.count()
    successful_donations = donations.filter(payment_status="Success")
    successful_total = successful_donations.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    successful_count = successful_donations.count()
    online_total = successful_donations.filter(donation_type="Online").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    cash_total = successful_donations.filter(donation_type="Cash").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    context = {
        "donations": donations,
        "institutions": institutions,
        "selected_institution": int(institution_id) if institution_id.isdigit() else "",
        "selected_type": donation_type,
        "selected_status": status,
        "total_count": total_count,
        "successful_count": successful_count,
        "successful_total": successful_total,
        "online_total": online_total,
        "cash_total": cash_total,
    }
    return render(request, "admin_portal/donations.html", context)


@admin_required
def admin_expense_list(request):
    """Cross-institutional expense & voucher monitoring."""
    institutions = Institution.objects.filter(approval_status="Approved").order_by("name")
    expenses = Expense.objects.select_related("institution").order_by("-expense_date", "-id")

    institution_id = request.GET.get("institution", "").strip()
    if institution_id.isdigit():
        expenses = expenses.filter(institution_id=int(institution_id))

    category = request.GET.get("category", "").strip()
    if category:
        expenses = expenses.filter(category=category)

    status = request.GET.get("status", "").strip()
    if status in ["Approved", "Pending", "Rejected"]:
        expenses = expenses.filter(status=status)

    total_count = expenses.count()
    total_expenses_sum = expenses.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    approved_expenses_total = expenses.filter(status="Approved").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    approved_count = expenses.filter(status="Approved").count()
    pending_expenses_total = expenses.filter(status="Pending").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    pending_count = expenses.filter(status="Pending").count()

    context = {
        "expenses": expenses,
        "institutions": institutions,
        "categories": [(c, c) for c in Expense.objects.exclude(category="").values_list('category', flat=True).distinct()],
        "selected_institution": int(institution_id) if institution_id.isdigit() else "",
        "selected_category": category,
        "selected_status": status,
        "total_count": total_count,
        "total_expenses_sum": total_expenses_sum,
        "approved_expenses_total": approved_expenses_total,
        "approved_count": approved_count,
        "pending_expenses_total": pending_expenses_total,
        "pending_count": pending_count,
    }
    return render(request, "admin_portal/expenses.html", context)


@admin_required
def admin_event_list(request):
    """Cross-institutional heritage & religious event monitoring."""
    institutions = Institution.objects.filter(approval_status="Approved").order_by("name")
    events = Event.objects.select_related("institution").order_by("-date", "-id")

    institution_id = request.GET.get("institution", "").strip()
    if institution_id.isdigit():
        events = events.filter(institution_id=int(institution_id))

    status = request.GET.get("status", "").strip()
    if status in ["Scheduled", "Ongoing", "Completed", "Cancelled"]:
        events = events.filter(status=status)

    total_events = events.count()
    total_budget = events.aggregate(t=Sum("estimated_cost"))["t"] or Decimal("0.00")
    total_actual = events.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

    context = {
        "events": events,
        "institutions": institutions,
        "selected_institution": int(institution_id) if institution_id.isdigit() else "",
        "selected_status": status,
        "total_events": total_events,
        "total_budget": total_budget,
        "total_actual": total_actual,
    }
    return render(request, "admin_portal/events.html", context)


@admin_required
def admin_maintenance_list(request):
    """Cross-institutional conservation & maintenance projects oversight."""
    institutions = Institution.objects.filter(approval_status="Approved").order_by("name")
    maintenance_qs = Maintenance.objects.select_related("institution", "asset").order_by("-scheduled_date", "-id")

    institution_id = request.GET.get("institution", "").strip()
    if institution_id.isdigit():
        maintenance_qs = maintenance_qs.filter(institution_id=int(institution_id))

    status = request.GET.get("status", "").strip()
    if status in ["Scheduled", "In Progress", "Completed", "Cancelled"]:
        maintenance_qs = maintenance_qs.filter(status=status)

    total_works = maintenance_qs.count()
    completed_works = maintenance_qs.filter(status="Completed").count()
    in_progress_works = maintenance_qs.filter(status="In Progress").count()
    total_actual_spend = maintenance_qs.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")

    context = {
        "maintenance_list": maintenance_qs,
        "institutions": institutions,
        "selected_institution": int(institution_id) if institution_id.isdigit() else "",
        "selected_status": status,
        "total_works": total_works,
        "completed_works": completed_works,
        "in_progress_works": in_progress_works,
        "total_actual_spend": total_actual_spend,
    }
    return render(request, "admin_portal/maintenance.html", context)


@admin_required
def admin_maintenance_detail(request, maintenance_id):
    """Detailed inspection dossier for a specific maintenance work project."""
    maintenance = get_object_or_404(Maintenance.objects.select_related("institution", "asset"), id=maintenance_id)
    return render(request, "admin_portal/maintenance_detail.html", {"maintenance": maintenance})


@admin_required
def admin_audit_log_list(request):
    """
    System Audit Trail & Audit Log Viewer for administrative, operational, and financial events.
    """
    users = User.objects.order_by("username")
    logs = AuditLog.objects.select_related("user").order_by("-timestamp")

    search_query = request.GET.get("q", "").strip()
    if search_query:
        logs = logs.filter(
            Q(action__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    user_id = request.GET.get("user_id", "").strip()
    if user_id.isdigit():
        logs = logs.filter(user_id=int(user_id))

    total_count = logs.count()
    logs = logs[:200]

    context = {
        "logs": logs,
        "users": users,
        "total_count": total_count,
        "search_query": search_query,
        "selected_user_id": int(user_id) if user_id.isdigit() else "",
    }
    return render(request, "admin_portal/audit_logs.html", context)


@admin_required
def admin_reports_overview(request):
    """
    System-wide governance report and institutional comparative analytics.
    """
    approved_institutions = Institution.objects.filter(approval_status="Approved").order_by("name")

    total_approved_institutions = approved_institutions.count()
    total_assets = Asset.objects.filter(institution__approval_status="Approved").count()
    total_valuation = (
        Asset.objects.filter(institution__approval_status="Approved").aggregate(t=Sum("current_valuation"))["t"]
        or Decimal("0.00")
    )
    total_donations_collected = (
        Donation.objects.filter(institution__approval_status="Approved", payment_status="Success").aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    total_expenses_approved = (
        Expense.objects.filter(institution__approval_status="Approved", status="Approved").aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    total_maintenance_spend = (
        Maintenance.objects.filter(institution__approval_status="Approved").aggregate(t=Sum("actual_cost"))["t"]
        or Decimal("0.00")
    )

    institution_summaries = []
    for inst in approved_institutions:
        inst_assets = Asset.objects.filter(institution=inst)
        inst_donations = Donation.objects.filter(institution=inst, payment_status="Success")
        inst_expenses = Expense.objects.filter(institution=inst, status="Approved")
        inst_maint = Maintenance.objects.filter(institution=inst)

        d_total = inst_donations.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
        e_total = inst_expenses.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
        m_total = inst_maint.aggregate(t=Sum("actual_cost"))["t"] or Decimal("0.00")
        net_balance = d_total - (e_total + m_total)

        institution_summaries.append({
            "institution": inst,
            "asset_count": inst_assets.count(),
            "total_valuation": inst_assets.aggregate(t=Sum("current_valuation"))["t"] or Decimal("0.00"),
            "donations_total": d_total,
            "expenses_total": e_total,
            "maintenance_count": inst_maint.count(),
            "maintenance_spend": m_total,
            "net_balance": net_balance,
        })

    context = {
        "approved_institutions": approved_institutions,
        "total_approved_institutions": total_approved_institutions,
        "total_assets": total_assets,
        "total_valuation": total_valuation,
        "total_donations_collected": total_donations_collected,
        "total_expenses_approved": total_expenses_approved,
        "total_maintenance_spend": total_maintenance_spend,
        "institution_summaries": institution_summaries,
    }
    return render(request, "admin_portal/reports.html", context)