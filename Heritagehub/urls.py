from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from HeritageHubApp import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("about/", views.about_view, name="about"),
    path("contact/", views.contact_view, name="contact"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),

    path("admin/", admin.site.urls),

    # Devotee module
    path("devotee/dashboard/", views.devotee_dashboard, name="devotee_dashboard"),
    path("devotee/donate/", views.devotee_donate, name="devotee_donate"),
    path("devotee/payment/", views.devotee_payment, name="devotee_payment"),
    path(
        "devotee/receipt/<int:receipt_id>/",
        views.devotee_receipt,
        name="devotee_receipt",
    ),
    path(
        "devotee/donation-history/",
        views.devotee_donation_history,
        name="devotee_donation_history",
    ),
    path("devotee/profile/", views.devotee_profile, name="devotee_profile"),

    # Trustee module
    path("trustee/dashboard/", views.trustee_dashboard, name="trustee_dashboard"),
    path(
        "trustee/institution/register/",
        views.trustee_institution_register,
        name="trustee_institution_register",
    ),
    path("trustee/assets/", views.trustee_asset_list, name="trustee_asset_list"),
    path("trustee/assets/add/", views.trustee_asset_add, name="trustee_asset_add"),
    path(
        "trustee/assets/<int:asset_id>/",
        views.trustee_asset_detail,
        name="trustee_asset_detail",
    ),
    path(
        "trustee/assets/<int:asset_id>/edit/",
        views.trustee_asset_edit,
        name="trustee_asset_edit",
    ),
    path(
        "trustee/assets/<int:asset_id>/delete/",
        views.trustee_asset_delete,
        name="trustee_asset_delete",
    ),
    path(
        "trustee/finance/",
        views.trustee_finance_dashboard,
        name="trustee_finance_dashboard",
    ),
    path(
        "trustee/donations/",
        views.trustee_donation_list,
        name="trustee_donation_list",
    ),
    path(
        "trustee/donations/<int:donation_id>/",
        views.trustee_donation_detail,
        name="trustee_donation_detail",
    ),
    path(
        "trustee/donations/<int:donation_id>/receipt/",
        views.trustee_receipt_view,
        name="trustee_receipt_view",
    ),
    path(
        "trustee/expenses/",
        views.trustee_expense_list,
        name="trustee_expense_list",
    ),
    path(
        "trustee/expenses/add/",
        views.trustee_expense_add,
        name="trustee_expense_add",
    ),
    path(
        "trustee/expenses/<int:expense_id>/",
        views.trustee_expense_detail,
        name="trustee_expense_detail",
    ),
    path(
        "trustee/expenses/<int:expense_id>/approve/",
        views.trustee_expense_approve,
        name="trustee_expense_approve",
    ),
    path(
        "trustee/expenses/<int:expense_id>/reject/",
        views.trustee_expense_reject,
        name="trustee_expense_reject",
    ),

    # Trustee Event Management
    path("trustee/events/", views.trustee_event_list, name="trustee_event_list"),
    path("trustee/events/add/", views.trustee_event_add, name="trustee_event_add"),
    path(
        "trustee/events/<int:event_id>/",
        views.trustee_event_detail,
        name="trustee_event_detail",
    ),
    path(
        "trustee/events/<int:event_id>/edit/",
        views.trustee_event_edit,
        name="trustee_event_edit",
    ),
    path(
        "trustee/events/<int:event_id>/delete/",
        views.trustee_event_delete,
        name="trustee_event_delete",
    ),

    # Trustee Maintenance Management
    path(
        "trustee/maintenance/",
        views.trustee_maintenance_list,
        name="trustee_maintenance_list",
    ),
    path(
        "trustee/maintenance/add/",
        views.trustee_maintenance_add,
        name="trustee_maintenance_add",
    ),
    path(
        "trustee/maintenance/<int:maintenance_id>/",
        views.trustee_maintenance_detail,
        name="trustee_maintenance_detail",
    ),
    path(
        "trustee/maintenance/<int:maintenance_id>/edit/",
        views.trustee_maintenance_edit,
        name="trustee_maintenance_edit",
    ),
    path(
        "trustee/maintenance/<int:maintenance_id>/delete/",
        views.trustee_maintenance_delete,
        name="trustee_maintenance_delete",
    ),

    # Trustee Staff Monitoring
    path("trustee/staff/", views.trustee_staff_list, name="trustee_staff_list"),

    # Reporting & Executive Dashboards
    path("reports/", views.public_transparency_reports, name="public_transparency_reports"),
    path("trustee/reports/", views.trustee_reports_overview, name="trustee_reports"),
    path("trustee/reports/overview/", views.trustee_reports_overview, name="trustee_reports_overview"),
    path("trustee/reports/donations/", views.trustee_reports_donations, name="trustee_reports_donations"),
    path("trustee/reports/finance/", views.trustee_reports_finance, name="trustee_reports_finance"),
    path("trustee/reports/assets/", views.trustee_reports_assets, name="trustee_reports_assets"),
    path("trustee/reports/maintenance/", views.trustee_reports_maintenance, name="trustee_reports_maintenance"),
    path("trustee/reports/summary/", views.trustee_reports_summary, name="trustee_reports_summary"),
    path("trustee/reports/summary/pdf/", views.trustee_reports_summary_pdf, name="trustee_reports_summary_pdf"),


    # Staff / Authorized Personnel module
    path("staff/dashboard/", views.staff_dashboard, name="staff_dashboard"),
    path("staff/donations/", views.staff_donation_list, name="staff_donation_list"),
    path("staff/donations/add/", views.staff_donation_add, name="staff_donation_add"),
    path("staff/donations/<int:donation_id>/", views.staff_donation_detail, name="staff_donation_detail"),
    path("staff/donations/<int:donation_id>/receipt/", views.staff_donation_receipt, name="staff_donation_receipt"),
    path("staff/maintenance/", views.staff_maintenance_list, name="staff_maintenance_list"),
    path("staff/maintenance/add/", views.staff_maintenance_add, name="staff_maintenance_add"),
    path("staff/maintenance/<int:maintenance_id>/", views.staff_maintenance_detail, name="staff_maintenance_detail"),
    path("staff/maintenance/<int:maintenance_id>/edit/", views.staff_maintenance_edit, name="staff_maintenance_edit"),

    # Application Admin Portal (Business Administration & Cross-Institutional Oversight)
    path("admin-portal/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-portal/approvals/", views.admin_user_approval_list, name="admin_user_approval_list"),
    path("admin-portal/users/", views.admin_user_list, name="admin_user_list"),
    path("admin-portal/users/<int:user_id>/approve/", views.admin_user_approve, name="admin_user_approve"),
    path("admin-portal/users/<int:user_id>/reject/", views.admin_user_reject, name="admin_user_reject"),
    path("admin-portal/institutions/", views.admin_institution_list, name="admin_institution_list"),
    path("admin-portal/institutions/<int:institution_id>/", views.admin_institution_detail, name="admin_institution_detail"),
    path("admin-portal/institutions/<int:institution_id>/approve/", views.admin_institution_approve, name="admin_institution_approve"),
    path("admin-portal/institutions/<int:institution_id>/reject/", views.admin_institution_reject, name="admin_institution_reject"),
    path("admin-portal/assets/", views.admin_asset_list, name="admin_asset_list"),
    path("admin-portal/assets/<int:asset_id>/", views.admin_asset_detail, name="admin_asset_detail"),
    path("admin-portal/donations/", views.admin_donation_list, name="admin_donation_list"),
    path("admin-portal/expenses/", views.admin_expense_list, name="admin_expense_list"),
    path("admin-portal/events/", views.admin_event_list, name="admin_event_list"),
    path("admin-portal/maintenance/", views.admin_maintenance_list, name="admin_maintenance_list"),
    path("admin-portal/maintenance/<int:maintenance_id>/", views.admin_maintenance_detail, name="admin_maintenance_detail"),
    path("admin-portal/audit-logs/", views.admin_audit_log_list, name="admin_audit_log_list"),
    path("admin-portal/reports/", views.admin_reports_overview, name="admin_reports_overview"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)