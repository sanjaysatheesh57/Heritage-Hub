# HeritageHub — Cultural Heritage Asset and Trust Management Information System

A web-based Management Information System (MIS) designed for cultural heritage institutions, religious trusts, and ancient temples to manage cultural assets, track financial donations and expenditures, schedule conservation maintenance and festivals, and provide statutory regulatory oversight for government authorities.

---

## 1. Project Overview

HeritageHub serves as a centralized, transparent platform addressing the administrative and statutory compliance needs of cultural heritage institutions. The system introduces structured workflows for asset documentation, financial accountability, and regulatory verification while providing devotees and the general public with transparent access to institution activities and public disclosure summaries.

---

## 2. Core Modules

1. **Asset Management Module**:
   - Comprehensive cataloging of movable and immovable cultural assets (idols, artifacts, temple jewelry, structures).
   - Documentation of physical condition, current valuation, storage/sanctum location, acquisition dates, and photographic archives.
   - Complete lifecycle tracking including addition, modification, and decommissioning.

2. **Donation & Finance Management Module**:
   - Multi-channel donation handling: Simulated online donations for devotees and on-premise cash donation recording by authorized counter staff.
   - Automated computerized receipt generation with unique serial numbering (`HH-REC-...` and `HH-CASH-...`).
   - Expenditure management with dual-step controls: expense entry, funding source linkage, and mandatory Trustee approval before funds disbursement.

3. **Event & Maintenance Management Module**:
   - Scheduling and tracking of temple festivals, cultural functions, and routine ceremonies with estimated vs. actual budget tracking.
   - Asset-linked conservation maintenance logging, progress tracking (Scheduled, In Progress, Completed), and preservation expense recording.

4. **Reporting & Dashboard Module**:
   - Executive dashboards tailored to each stakeholder role with key performance indicators (KPIs).
   - Comprehensive analytical reports: donation ledgers, expense utilization breakdowns, asset valuations, and downloadable PDF summaries.
   - Public Transparency Reports presenting aggregate financial summaries without disclosing donor private data.

---

## 3. User Roles & Access Hierarchy

The system enforces strict Role-Based Access Control (RBAC) across four primary user personas:

| Role | Primary Responsibilities & Permissions |
| :--- | :--- |
| **Trustee** | Executive institution administration. Registers the institution, manages cultural asset registers, approves/rejects expenses, manages festival arrangements, and accesses complete institutional financial reports. |
| **Staff / Authorized Personnel** | Operational counter duties. Records cash donations from visiting devotees, issues cash receipts, and logs asset conservation maintenance tasks and progress. Restricted from modifying asset details or approving expenses. |
| **Devotee / Public** | Public engagement. Browses approved cultural institutions, performs simulated online donations, downloads donation receipts, views personal contribution history, and inspects public transparency reports. |
| **Admin** | System administration & governance oversight. Verifies and approves/rejects pending institution and user registrations (Trustees and Staff), exercises comprehensive oversight over institutional assets, donations, expenses, maintenance, and audit trails, and manages user accounts and system reports across the platform. |

*Note: Technical/system administrators manage Django technical settings via the standard Django Admin portal (`/admin/`) and require an explicit `UserProfile` to access functional portals.*

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

- **Donation Inflows**: Only donations with `payment_status = "Success"` contribute to the institution's available balance. Donations in `Pending` or `Failed` status are retained for audit reconciliation but never credited to available funds.
- **Expenditure Outflows**: All recorded expenses initiate in `Pending` status (`approved_by = None`). Only upon explicit approval by an authorized Trustee does the expenditure transition to `Approved` and deduct from available funds.
- **Data Integrity**: Expenses cannot be funded by mismatched or cross-institutional donations. Negative monetary amounts are rejected at validation.

---

## 6. Security, Privacy & Data Isolation

- **Role-Based Access Control**: All functional views are protected by custom role-verification decorators (`@trustee_required`, `@staff_required`, `@admin_required`, `@devotee_required`). Unauthorized access attempts return HTTP 403 Forbidden.
- **Institution-Level Isolation (Multi-Tenancy)**: Trustees and Staff are strictly restricted to data records belonging to their assigned institution. Cross-institutional read, write, or modification attempts are blocked.
- **Receipt Confidentiality**: Online donation receipts are strictly restricted to the donor who initiated the payment.
- **Public Privacy Safeguards**: Public transparency views strictly display aggregate financial totals; zero donor names, email addresses, phone numbers, or transaction identifiers are disclosed to the public.
- **Audit Logging**: Comprehensive internal audit trails (`AuditLog`) automatically record critical lifecycle actions (registrations, approvals, donations, expense decisions, maintenance operations).

> **Academic Note**: The online payment gateway interface is a simulated checkout demonstration created for academic presentation purposes. No real monetary transactions or banking APIs are invoked.

---

## 7. Technology Stack

- **Backend Framework**: Python 3.12+ / Django 5.0
- **Database**: MySQL 8.0+ / MariaDB (connected via `mysqlclient`)
- **Frontend & UI**: HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, JavaScript
- **Document & PDF Generation**: ReportLab 5.0
- **Image Processing**: Pillow 12.0

---

## 8. Local Setup & Execution Instructions

### Prerequisites
- Python 3.12 or higher installed
- MySQL Server 8.0+ running locally on port 3306
- Git or extracted project source code

### Step 1: Clone or Open Project Directory
```bash
cd D:\Heritage_Hub\Heritagehub
```

### Step 2: Set Up Virtual Environment
Create and activate an isolated Python virtual environment:
```bash
# Windows
python -m venv env
env\Scripts\activate

# Linux / macOS
python3 -m venv env
source env/bin/activate
```

### Step 3: Install Required Dependencies
Install the pinned dependencies from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Step 4: Configure Database
1. Ensure your local MySQL server is running.
2. Create an empty database named `heritagehub`:
   ```sql
   CREATE DATABASE heritagehub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Verify connection settings in `Heritagehub/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'heritagehub',
           'USER': 'root',
           'PASSWORD': '',       # Enter your local MySQL password if set
           'HOST': '127.0.0.1',
           'PORT': '3306',
       }
   }
   ```

### Step 5: Apply Database Migrations
Run Django migrations to initialize all 19 relational database tables:
```bash
python manage.py migrate
```

### Step 6: Create Administrative Superuser (Optional)
```bash
python manage.py createsuperuser
```

### Step 7: Load Demonstration Data (Optional)
If restoring baseline demonstration accounts:
```bash
python manage.py loaddata mysql_restore.json
```

### Step 8: Run Development Server
```bash
python manage.py runserver
```
Access the application at: `http://127.0.0.1:8000/`

---

## 9. Verification & Quality Assurance

The codebase includes automated test and verification scripts:
- `python manage.py check`: Verifies Django system integrity (0 issues).
- `python manage.py makemigrations --dry-run`: Verifies database model consistency (No changes detected).

---

## 10. Submission Directory Structure

```
Heritagehub/
├── manage.py
├── requirements.txt
├── README.md
├── .gitignore
├── mysql_restore.json
├── Heritagehub/               # Project configuration package
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── HeritageHubApp/            # Main application package
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── views.py
│   ├── migrations/
│   │   └── 0001_initial.py
│   └── templates/             # 67 HTML templates
│       ├── admin_portal/
│       ├── common/
│       ├── devotee/
│       ├── staff/
│       └── trustee/
├── static/                    # CSS, JS, and image assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── media/                     # Uploaded institutional documents and photos
    └── assets/
        └── nataraja_vigraham.jpeg
```
