# 👟 HYPECULTURE

> **Your Ultimate Sneaker Marketplace — built with Python, Streamlit, and MySQL**

HYPECULTURE is a full-featured **web application** that simulates an end-to-end sneaker marketplace.  
Inspired by platforms like **StockX** and **Amazon**, it lets **customers**, **sellers**, and **admins** interact seamlessly — browsing, selling, and managing shoe inventory through a clean **Streamlit** interface.

Built as a **database-driven project**, it showcases relational schema design, SQL transactions, and multi-role user management in a single, intuitive app.

---

## 🧭 Table of Contents

- [✨ Core Features](#-core-features)
  - [👤 Customer](#-customer)
  - [💼 Seller](#-seller)
  - [👑 Admin](#-admin)
- [🧠 Architecture Overview](#-architecture-overview)
- [📁 Project Structure](#-project-structure)
- [🚀 How to Run](#-how-to-run)
- [🧩 Roles Summary](#-roles-summary)
- [📸 Preview (Optional)](#-preview-optional)

---

## ✨ Core Features

### 👤 Customer
- 🔐 Register & log in securely  
- 🧭 Browse shoes by category (e.g. Sneakers, Boots, etc.)  
- 💰 Compare sellers sorted by **cheapest price first**  
- 🛒 Add, edit, and remove items from a persistent shopping cart  
- 💳 Complete checkout with full shipping details  
- 📦 Track and view detailed **order history**  
- 🚪 Logout button conveniently placed at the **top-right corner**

---

### 💼 Seller
- 🧾 Manage your own inventory listings  
- ➕ Add new listings for existing catalog products  
- ✏️ Update stock or price instantly  
- ❌ Remove listings when out of stock  
- 📊 View a summary of all your current listings  

---

### 👑 Admin
- 🧍 View all registered users, products, and orders  
- ➕ Add **new products** to the master catalog  
- 👥 Add or remove **users** (customers or sellers)  
- 📦 Monitor orders and system-wide activity  
- 🛠️ Maintain complete marketplace control  

---

## 🧠 Architecture Overview

| Layer | Technology | Description |
|-------|-------------|-------------|
| **Frontend (UI)** | Streamlit | Interactive, browser-based web interface |
| **Backend** | MySQL | Centralized relational database for all entities |
| **Connector** | `mysql-connector-python` | Secure database connectivity |
| **Language** | Python 3.12+ | Core application and logic |

---

## 📁 Project Structure

```bash
HYPECULTURE-main/
├── app.py                 # Main Streamlit entry point
├── customer_view.py       # Customer dashboard & shopping flow
├── admin_seller_views.py  # Admin + Seller dashboards
├── db_connector.py        # MySQL connector setup
├── hypeculture.sql        # Database schema + seed data
├── SETUP.md               # Step-by-step setup instructions
├── README.md              # This file
└── .venv/                 # Optional: virtual environment
