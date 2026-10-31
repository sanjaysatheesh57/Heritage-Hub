# HeritageHub — Cultural Heritage Asset and Trust Management Information System

A comprehensive, web-based Management Information System (MIS) engineered for cultural heritage institutions, religious trusts, and historic temples. HeritageHub streamlines cultural asset documentation, governs multi-channel financial donations and expenditures, schedules conservation maintenance and festival events, and provides statutory governance oversight and public transparency disclosures.

---

## 1. Project Overview

HeritageHub provides a unified, transparent platform that addresses the operational, fiduciary, and statutory compliance needs of cultural heritage institutions. The platform replaces fragmented, manual ledgers with structured digital workflows for:

- **Cultural Asset Documentation**: Cataloging priceless movable and immovable artifacts with valuations, physical condition tracking, and photographic archives.
- **Fiduciary Accountability**: Dual-step expenditure authorization, multi-channel donation recording (simulated online offerings & on-premise cash receipts), and real-time available fund calculations.
- **Conservation & Festival Lifecycle**: Tracking asset-specific conservation works and scheduling religious and cultural events.
- **Multi-Role Governance & Oversight**: Strict Role-Based Access Control (RBAC) ensuring dedicated portals for System Administrators, Institution Trustees, Counter Staff, Devotees, and the General Public.

---

## 2. Core Portals & Functional Modules

### 1. Administrative Oversight Portal (`/admin-portal/`)
- **Institutional Governance**: Reviews and approves/rejects new institution registration applications with certificate verification.
- **User Account Approvals**: Authorizes pending Trustee and Staff accounts before granting functional system access.
- **Cross-Institutional Analytics**: Real-time aggregated oversight over total institutions, cultural assets, donation inflows, and conservation expenditures.
- **Comprehensive Audit Trail**: Real-time log inspector (`AuditLog`) monitoring all critical system mutations.
- **System Reports**: Cross-institutional comparative analytics and operational summaries.

### 2. Trustee Management Portal (`/trustee/`)
- **Institution Registration & Profile**: Registers institution details, PAN, contact information, and registration documentation.
- **Cultural Asset Dossiers**: Complete asset management (movable/immovable), condition classification, location tracking, valuation updates, and photographic archives.
- **Financial Governance**: Two-phase expenditure management where trustees review, approve, or reject expense vouchers linked to institutional funds.
- **Event Scheduling**: Manages temple festivals, ceremonies, and cultural programs with estimated vs. actual expenditure tracking.
- **Conservation Maintenance**: Logs, schedules, and monitors conservation and restoration operations on heritage assets.
- **Staff Oversight**: Monitors assigned counter and operational personnel.
- **Financial Reports & PDF Export**: Detailed donation and expense ledgers, balance statements, and formal downloadable PDF financial statements via ReportLab.

### 3. Staff Counter Portal (`/staff/`)
- **Counter Cash Donations**: Records walk-in devotee cash offerings with instant automated cash receipt generation (`HH-CASH-...`).
- **Donation History & Receipt Lookup**: Searchable ledger of on-premise donations with printable computerized receipts.
- **Conservation Maintenance Tracking**: Logs physical maintenance progress (Scheduled, In Progress, Completed), updates actual costs, and inspects linked cultural asset dossiers with uploaded photographs for visual identification.

### 4. Devotee & Civic Portal (`/devotee/`)
- **Civic Registration & Secure Authentication**: Instant self-service account registration.
- **Online Offerings (Simulated Payment Gateway)**: Secure multi-step donation workflow supporting UPI, Debit/Credit Card, and NetBanking simulation without charging real payment instruments.
- **Automated Computerized Receipts**: Instant generation of unique digital receipts (`HH-REC-...`) with printable, tamper-evident layouts.
- **Personal Donation History**: Comprehensive tracking of all personal offerings and contributions.
- **Devotee Profile Management**: Personal contact and profile information maintenance.

### 5. Public Transparency Portal (`/reports/` & Common Pages)
- **Public Institutional Registry**: Information on registered and approved heritage institutions.
- **Public Transparency Reports**: Aggregated financial transparency summaries presenting total donations collected and approved conservation spend per institution, safeguarding donor privacy with zero personally identifiable information (PII) disclosure.

---

## 3. User Roles & Access Control Hierarchy

The system strictly enforces Role-Based Access Control (RBAC) across four authenticated user roles plus unauthenticated public visitors:

| Role | Access Level | Primary Responsibilities & Functional Scope |
| :--- | :--- | :--- |
| **Admin** | System-Wide | Verifies institution applications, approves Trustee and Staff user accounts, exercises cross-institutional oversight across all assets, donations, expenses, and audit trails. Uses a dedicated, fully customized Admin Portal. |
| **Trustee** | Institution-Level | Executive authority for an approved institution. Manages asset registers, approves/rejects expenditure requests, schedules events, monitors maintenance, and accesses institutional financial reports and PDF exports. |
| **Staff** | Institution-Level | Operational counter staff. Logs on-premise cash donations, issues counter receipts, logs asset maintenance progress, and inspects linked asset photographs. Cannot approve expenses or alter asset valuations. |
| **Devotee** | User-Level | General public and donors. Browses approved institutions, makes simulated online donations, downloads receipts, and reviews personal donation history. |
| **Public** | Unauthenticated | Explores the public portal, reads institution information, submits contact inquiries, and views public transparency reports. |

### Access Control & Governance Safeguards
- **Custom RBAC Decorators**: Functional views are guarded by `@admin_required`, `@trustee_required`, `@staff_required`, and `@devotee_required` decorators, returning HTTP 403 Forbidden on unauthorized role attempts.
- **Approval Gate**: Newly registered Trustee and Staff accounts are created in `Pending` approval status and locked out of functional dashboards until verified and approved by a System Administrator.
- **Multi-Tenant Isolation**: Trustee and Staff queries are strictly partitioned by `request.user.userprofile.institution`. Cross-institutional access or data tampering is blocked at the database query level.
- **Dedicated Admin Experience**: All administrative functions are performed via the tailored `/admin-portal/` interface. Technical Django admin links (`/admin/`) are omitted from public and role-facing navigation for clean UI isolation.

---

## 4. Main Institutional Workflow

```
Trustee Submits Institution Registration
                   │
                   ▼
       Status: "Pending" Verification
                   │
                   ▼
     System Administrator Reviews
      (Inspects documents, PAN, contact)
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
    [Approved]          [Rejected]
         │                   │
         ▼                   ▼
 Institution Active   Application Closed
 - Assets unlocked    (Reason logged in
 - Donations active    audit trail)
 - Events active
```

---

## 5. Core Financial Logic & Fund Governance

The system strictly enforces the statutory financial availability formula:

$$\text{Available Funds} = \sum(\text{Successful Donations}) - \sum(\text{Approved Expenses})$$

### 1. Inflow Governance
- **Successful Online Donations**: Completed via the simulated payment checkout. Stored with `payment_status = "Success"`, generating an official `HH-REC-{id:06d}` receipt.
- **Counter Cash Donations**: Recorded directly by authorized Staff. Stored with `donation_type = "Cash"` and `payment_status = "Success"`, generating an `HH-CASH-{id:06d}` receipt.
- **Pending/Failed Protection**: Stalled checkouts remain in `request.session` or marked `Pending`/`Failed` and never increment available institutional balances.

### 2. Outflow Governance
- **Two-Step Approval**: Recorded expenses are initialized as `Pending`. Only upon explicit review and authorization by an assigned Trustee does the record transition to `Approved` and deduct from available funds.
- **Audit Linking**: Each expenditure can be tied to specific donation allocations or operational budgets, ensuring full traceability.

---

## 6. Security, Session & Architectural Design

- **Browser-Close Session Termination**: Configured with `SESSION_EXPIRE_AT_BROWSER_CLOSE = True` in `settings.py`. When counter or administration staff close their browser, the session cookie is discarded, preventing unauthorized resumption on shared workstations.
- **Session-Backed Checkout**: Devotee donation forms store in-flight checkout details in encrypted session memory, committing records to the relational database only upon successful payment simulation.
- **Visual Asset Verification for Staff**: Maintenance records dynamically link and display the asset's uploaded photograph (`maintenance.asset.photograph`), enabling maintenance personnel to inspect physical artifacts under conservation accurately.
- **CSRF Defense**: All POST-method forms across all 72 templates implement standard `{% csrf_token %}` verification.
- **Immutable Audit Trail**: User authentications, approvals, status transitions, and financial operations are written to the `AuditLog` table.
- **Public Data Privacy**: Public transparency views render aggregated numerical metrics; donor identities, contact information, and transaction hashes remain strictly confidential.

> **Academic Note**: The payment gateway interface is a simulated demonstration environment created for academic evaluation. No external banking APIs or live payment gateways are connected.

---

## 7. Technology Stack

- **Backend Framework**: Python 3.12+ / Django 5.0
- **Database Engine**: MySQL 8.0+ / MariaDB (connected via `mysqlclient 2.2.1`)
- **Frontend Architecture**: HTML5, CSS3, Bootstrap 5.3.2, Bootstrap Icons 1.11.2, Vanilla JavaScript
- **Design System**: HeritageHub Master Theme (Terracotta `#9a3412`, Temple Gold `#d97706`, Ivory/Parchment `#fbfbf9`)
- **Document & PDF Generation**: ReportLab 5.0.0
- **Image Processing**: Pillow 12.0.0

---

## 8. Local Setup & Execution Guide

### Prerequisites
- Python 3.12 or higher installed
- MySQL Server 8.0+ running locally on port 3306
- Git or extracted project source directory

### Step 1: Navigate to Project Directory
```bash
cd D:\Heritage_Hub\Heritagehub
```

### Step 2: Initialize & Activate Virtual Environment
```bash
# Windows (PowerShell / Command Prompt)
python -m venv env
env\Scripts\activate

# Linux / macOS
python3 -m venv env
source env/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure MySQL Database
1. Launch your MySQL command-line client or administration interface.
2. Create the UTF-8 database:
   ```sql
   CREATE DATABASE heritagehub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Verify connection credentials in `Heritagehub/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'heritagehub',
           'USER': 'root',
           'PASSWORD': '',       # Enter your local MySQL root password if applicable
           'HOST': '127.0.0.1',
           'PORT': '3306',
       }
   }
   ```

### Step 5: Apply Database Migrations
Initialize the schema (9 custom domain models + Django system tables):
```bash
python manage.py migrate
```

### Step 6: Create Administrative Superuser (Optional)
```bash
python manage.py createsuperuser
```

### Step 7: Load Demonstration Seed Data (Optional)
Restore baseline sample institutions, assets, users, and demonstration records:
```bash
python manage.py loaddata mysql_restore.json
```

### Step 8: Launch the Development Server
```bash
python manage.py runserver
```
Open your web browser and navigate to: `http://127.0.0.1:8000/`

---

## 9. Verification & Quality Assurance

To ensure project integrity, execute the standard Django health checks:
```bash
# Verify system configuration and template routing
python manage.py check

# Confirm database model synchronization
python manage.py makemigrations --dry-run
```
Expected output: `System check identified no issues (0 silenced).` and `No changes detected`.

---

## 10. Complete Project Directory Structure

```
Heritagehub/
├── manage.py                          # Django management CLI
├── requirements.txt                   # Pinned project dependencies
├── README.md                          # Project documentation
├── .gitignore                         # Version control exclusions
├── mysql_restore.json                 # Baseline seed demonstration dataset
├── Heritagehub/                       # Django project configuration package
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py                    # Settings, database, and session configuration
│   ├── urls.py                        # Master URL routing table
│   └── wsgi.py
├── HeritageHubApp/                    # Core application package
│   ├── admin.py                       # Django technical admin registrations
│   ├── apps.py                        # Application configuration
│   ├── models.py                      # 9 Relational Domain Models
│   ├── tests.py                       # Application unit tests
│   ├── views.py                       # Role-based views and business logic
│   ├── migrations/
│   │   └── 0001_initial.py            # Initial database schema migration
│   └── templates/                     # 72 Modular HTML Templates (all extend base.html)
│       ├── admin_portal/              # 14 templates (System oversight, approvals, reports)
│       ├── common/                    # 7 templates (base layout, home, about, contact, login, register, transparency)
│       ├── devotee/                   # 6 templates (dashboard, donation checkout, receipt, history, profile)
│       ├── staff/                     # 16 templates (counter dashboard, cash donations, maintenance works & asset views)
│       └── trustee/                   # 29 templates (dossiers, assets, finance, expenses, events, maintenance, reports)
├── static/                            # Static web assets
│   ├── css/
│   │   └── style.css                  # Master design system & CSS variables
│   └── js/
│       └── main.js
└── media/                             # Dynamic user-uploaded media files
    ├── assets/                        # Cultural asset photographs
    └── institution_documents/         # Registration certificates & deeds
```
