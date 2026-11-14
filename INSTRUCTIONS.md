# Bharathi Oil Mill — Management System
## Complete Setup & Usage Guide

---

## 📋 What This Application Does

A full-featured management system for **Bharathi Oil Mill** covering:

| Module | Features |
|---|---|
| **POS / Billing** | Service bills, oil seed processing with oil-cake buy-back, QR codes, pending bills, payment tracking |
| **Inventory** | Oil cakes, oil products, supplies; stock in/out, bulk oil cake sales |
| **Labour** | Daily attendance, wages, advances, monthly reports |
| **Machines** | Fleet view, maintenance logs, service reminders |
| **Services & Rates** | Manage all services and per-kg rates |
| **Reports** | Daily/monthly revenue, expense tracking, analytics |

---

## 🗂️ Project Structure

```
bharathi_oil_mill/
├── Home.py                  ← Main dashboard (run this)
├── database.py              ← DB connection + schema
├── requirements.txt
├── INSTRUCTIONS.md          ← This file
├── .streamlit/
│   ├── config.toml          ← UI theme
│   └── secrets.toml.example ← DB config template
├── pages/
│   ├── 01_POS.py            ← Point of Sale
│   ├── 02_Inventory.py      ← Inventory management
│   ├── 03_Labour.py         ← Labour management
│   ├── 04_Machines.py       ← Machine management
│   ├── 05_Services.py       ← Services & rates
│   └── 06_Reports.py        ← Reports & analytics
└── utils/
    ├── qr_utils.py          ← QR code generation
    └── bill_printer.py      ← HTML bill generation
```

---

## 🚀 Quick Start

### Step 1 — Install Python & Dependencies

```bash
# Python 3.9+ required
pip install -r requirements.txt
```

### Step 2 — Set Up Database

#### Option A: Local PostgreSQL (Recommended for testing)

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt install postgresql postgresql-contrib

# macOS (Homebrew)
brew install postgresql@15

# Start service
sudo systemctl start postgresql    # Linux
brew services start postgresql@15  # macOS

# Create database
psql -U postgres -c "CREATE DATABASE bharathi_oil_mill;"
```

#### Option B: Supabase (Free cloud PostgreSQL — Recommended for production)

1. Go to [https://supabase.com](https://supabase.com) and create a free account
2. Create a new project (choose a region near you)
3. Wait for project to initialize (~2 minutes)
4. Go to **Settings → Database** and copy the **Connection String (URI)**
5. Use it as your `DATABASE_URL`

### Step 3 — Configure Database Credentials

```bash
# Copy the example secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# Edit it with your credentials
nano .streamlit/secrets.toml
```

**For Supabase:**
```toml
DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@db.YOURREF.supabase.co:5432/postgres"
```

**For Local PostgreSQL:**
```toml
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "bharathi_oil_mill"
DB_USER = "postgres"
DB_PASSWORD = "your_password"
```

### Step 4 — Run the Application

```bash
streamlit run Home.py
```

The app opens at **http://localhost:8501** automatically.

> On first run, all tables and default data (services, machines, inventory items) are created automatically.

---

## 📱 Module Usage Guide

### 🏪 POS — Creating a Bill

1. Go to **POS** from the sidebar
2. **Add Services:** Select category → service → enter quantity (kg) → click **➕ Add**
3. **Oil Processing** (expand the section):
   - Select oil seed type
   - Enter input kg and processing rate
   - Enter oil cake kg returned and buy-back rate
   - System calculates: *Processing Fee − Oil Cake Value = Net (customer pays or mill pays)*
4. **Customer Info:** Optionally enter name + phone
5. **Payment:**
   - `Cash` or `UPI` → bill saved as paid
   - `Skip / Pending` → bill saved as pending; enter reminder date; customer name/phone required
6. Click **💾 Save Bill**
7. Download/print the HTML bill with embedded QR code

### 📷 QR Code — What It Contains

Each bill QR code encodes a compact JSON with:
- Bill number, date, customer name/phone
- Total amount, payment status, method
- Line items (service name, qty, amount)

To verify: scan the QR with any phone camera → shows bill details. Inside the app, go to **POS → Scan QR tab** and enter the bill number.

### ⏳ Pending Bills

- In **POS → Pending Bills tab**, all unpaid bills are listed
- Overdue bills (past reminder date) are highlighted in red
- Select payment method and click **✅ Mark Paid**

### 📦 Inventory — Oil Cake Flow

**Automatic:** When an oil processing entry is saved in POS, oil cake kg is automatically added to inventory.

**Manual adjustment:** Inventory → Add/Edit Item → Adjust Stock

**Bulk Sale:** Inventory → Bulk Oil Cake Sale → select type, qty, rate, buyer → saves sale bill + deducts stock

### 👷 Labour Management

1. Go to **Labour → Attendance tab**
2. Select work date
3. For each worker: mark present/absent, days worked (0.5 for half-day), wage paid, advance
4. Click **💾 Save Attendance**
5. View monthly summaries in **Reports tab**

> **Duplicate names:** The system uses IDs internally, so you can have multiple workers with similar names. Each record is tracked by ID.

### ⚙️ Machines

- **Fleet View:** See all machines, their status, and upcoming service dates
- **Change status:** Directly on the fleet view (Active/Maintenance/Breakdown/Inactive)
- **Log Maintenance:** Enter date, type, cost, technician, next service date
- **Service alerts** appear on the Home dashboard when service is due within 14 days

### 🛠 Services & Rates

- View all services grouped by category
- Add new services with category and rate
- Edit rates anytime — POS always uses the latest rate (editable per bill)

---

## 💰 Oil Seed Processing Logic

```
Processing Fee = Input KG × Processing Rate/kg
Oil Cake Value = Oil Cake KG × Oil Cake Rate/kg (buy-back price)
Net Amount     = Processing Fee − Oil Cake Value

If Net > 0 → Customer PAYS the difference
If Net < 0 → Mill PAYS the customer the difference
```

**Example:**
- 10 kg groundnut, processing rate ₹8/kg = ₹80 processing fee
- Returns 4 kg oil cake, buy-back ₹12/kg = ₹48 oil cake value
- Net = ₹80 − ₹48 = **₹32 (customer pays)**

---

## 🧾 Bill Types

| Type | Description |
|---|---|
| `service` | Regular milling/grinding services |
| `oil_cake_sale` | Bulk oil cake sold to buyers |

---

## 🗄️ Database Tables

| Table | Purpose |
|---|---|
| `services` | Mill service catalog with rates |
| `customers` | Customer name + phone (optional) |
| `bills` | All bills with payment status |
| `bill_items` | Line items per bill |
| `oil_processing` | Oil seed processing records |
| `inventory` | Stock items (oil cakes, products, supplies) |
| `inventory_transactions` | Stock movement log |
| `labourers` | Worker roster |
| `labour_attendance` | Daily attendance + wages |
| `machines` | Machine catalog |
| `machine_maintenance` | Maintenance log |
| `expenses` | General expense tracking |

---

## 🌐 Cloud Deployment

### Option 1: Streamlit Community Cloud (Free)

1. Push your code to a **GitHub repository** (make sure `secrets.toml` is in `.gitignore`)
2. Go to [https://share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select the repo, branch, and `Home.py` as the main file
5. In **Advanced settings → Secrets**, paste your `secrets.toml` content
6. Click **Deploy** — your app gets a public URL

### Option 2: Railway (Free tier available)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```
Add your `DATABASE_URL` as an environment variable in the Railway dashboard.

### Option 3: Render

1. Create a [Render](https://render.com) account
2. New → Web Service → connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run Home.py --server.port $PORT --server.address 0.0.0.0`
5. Add `DATABASE_URL` as an environment variable

### Option 4: Local Network (for in-shop use)

```bash
# Run accessible from other devices on the same WiFi
streamlit run Home.py --server.address 0.0.0.0 --server.port 8501
```
Access from any phone/tablet on the same network at `http://YOUR_PC_IP:8501`

---

## 🔒 Security Notes

- Never commit `secrets.toml` to Git (it's already in `.gitignore` by default)
- For production, use a strong PostgreSQL password
- Supabase automatically handles SSL encryption

---

## 🛠 Troubleshooting

| Problem | Solution |
|---|---|
| `connection refused` | Check PostgreSQL is running; verify host/port in secrets.toml |
| `password authentication failed` | Double-check DB_USER and DB_PASSWORD |
| `module not found` | Run `pip install -r requirements.txt` |
| `QR code not generating` | Ensure `qrcode[pil]` and `Pillow` are installed |
| Bill HTML not printing | Open the downloaded .html file in Chrome and use Ctrl+P |
| Supabase connection slow | Normal for free tier; first connection may take 10-15 seconds |

---

## 📞 Default Data Pre-loaded

On first run, the system creates:

**Services (19 defaults):**
- Wheat, Rice, Kambu, Kezhvaragu, Corn milling
- Chilli, Masala, Coriander grinding
- Ulunthu, Toor dhal splitting
- Groundnut, Sesame, Coconut, Ilupai, Neem, Castor oil extraction
- Oil cake grinding
- Idiyappam, Idli/Dosa wet grinding

**Inventory (9 defaults):** Groundnut/Sesame/Coconut/Ilupai/Neem oil cakes + retail oils + packing covers

**Machines (12 defaults):** 2 flour mills, 1 spice grinder, 1 dhal splitter, 6 oil rotaries, 1 oil cake grinder, 1 wet grinder

---

## 📱 Mobile Usage Tips

- The app is responsive — works on tablet/phone
- For billing at the counter: use a tablet in landscape mode
- QR code scanning: use the **Scan QR** tab, enter bill number manually (camera API not available in browser without HTTPS)
- For HTTPS (needed for camera): deploy to Streamlit Cloud or use ngrok

---

*Bharathi Oil Mill Management System · Built with Streamlit + PostgreSQL*
