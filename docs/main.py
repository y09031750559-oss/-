import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

# -----------------------------
# DB
# -----------------------------
conn = sqlite3.connect("crm.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    amount REAL,
    date TEXT
)
""")

conn.commit()

# -----------------------------
# UI
# -----------------------------
root = tk.Tk()
root.title("CRM PRO")
root.geometry("1100x750")
root.configure(bg="#1e1e2f")

# -----------------------------
# COLORS
# -----------------------------
BG = "#1e1e2f"
PANEL = "#2b2b40"
ACCENT = "#4e9af1"
TEXT = "white"

# -----------------------------
# SIDEBAR
# -----------------------------
sidebar = tk.Frame(root, bg=PANEL, width=200)
sidebar.pack(side="left", fill="y")

content = tk.Frame(root, bg=BG)
content.pack(side="right", fill="both", expand=True)

tk.Label(sidebar, text="CRM PRO", bg=PANEL, fg=TEXT,
         font=("Arial", 16, "bold")).pack(pady=20)

# -----------------------------
# DB FUNCTIONS
# -----------------------------
def load_clients():
    for i in tree.get_children():
        tree.delete(i)

    cursor.execute("SELECT * FROM clients")
    for row in cursor.fetchall():
        tree.insert("", "end", values=row)

    update_kpi()
    load_analytics()

def load_analytics():
    for i in tree_stats.get_children():
        tree_stats.delete(i)

    cursor.execute("""
        SELECT clients.name,
               COALESCE(SUM(purchases.amount),0)
        FROM clients
        LEFT JOIN purchases ON clients.id = purchases.client_id
        GROUP BY clients.id
        ORDER BY 2 DESC
    """)

    for row in cursor.fetchall():
        tree_stats.insert("", "end", values=row)

def add_client():
    name = e_name.get()

    if not name:
        messagebox.showerror("Ошибка", "Имя обязательно")
        return

    cursor.execute("INSERT INTO clients(name,phone,email) VALUES(?,?,?)",
                   (name, e_phone.get(), e_email.get()))
    conn.commit()

    e_name.delete(0, tk.END)
    e_phone.delete(0, tk.END)
    e_email.delete(0, tk.END)

    load_clients()

def delete_client():
    sel = tree.selection()
    if not sel:
        return

    cid = tree.item(sel[0])["values"][0]

    cursor.execute("DELETE FROM clients WHERE id=?", (cid,))
    cursor.execute("DELETE FROM purchases WHERE client_id=?", (cid,))
    conn.commit()

    load_clients()

def add_purchase():
    sel = tree.selection()
    if not sel:
        messagebox.showerror("Ошибка", "Выбери клиента")
        return

    try:
        amount = float(e_amount.get())
    except:
        messagebox.showerror("Ошибка", "Сумма должна быть числом")
        return

    cid = tree.item(sel[0])["values"][0]
    date = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "INSERT INTO purchases(client_id,amount,date) VALUES(?,?,?)",
        (cid, amount, date)
    )
    conn.commit()

    e_amount.delete(0, tk.END)
    load_clients()

def show_graph():
    cursor.execute("""
        SELECT date, SUM(amount)
        FROM purchases
        GROUP BY date
        ORDER BY date
    """)

    data = cursor.fetchall()
    if not data:
        return

    x = [i[0] for i in data]
    y = [i[1] for i in data]

    plt.figure(figsize=(9,4))
    plt.plot(x, y, marker="o")
    plt.xticks(rotation=45)
    plt.title("Revenue")
    plt.tight_layout()
    plt.show()

# -----------------------------
# KPI CARDS
# -----------------------------
kpi_frame = tk.Frame(content, bg=BG)
kpi_frame.pack(pady=10)

kpi_clients = tk.Label(kpi_frame, text="Клиенты: 0",
                        bg=ACCENT, fg="white",
                        font=("Arial", 12, "bold"),
                        width=20)
kpi_clients.pack(side="left", padx=10)

kpi_money = tk.Label(kpi_frame, text="Доход: 0",
                     bg="#27ae60", fg="white",
                     font=("Arial", 12, "bold"),
                     width=20)
kpi_money.pack(side="left", padx=10)

def update_kpi():
    cursor.execute("SELECT COUNT(*) FROM clients")
    clients = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(amount),0) FROM purchases")
    money = cursor.fetchone()[0]

    kpi_clients.config(text=f"Клиенты: {clients}")
    kpi_money.config(text=f"Доход: {money}")

# -----------------------------
# FORM
# -----------------------------
form = tk.Frame(content, bg=BG)
form.pack(pady=10)

e_name = tk.Entry(form, width=15)
e_phone = tk.Entry(form, width=15)
e_email = tk.Entry(form, width=15)

e_name.insert(0, "Имя")
e_phone.insert(0, "Телефон")
e_email.insert(0, "Email")

e_name.grid(row=0, column=0, padx=5)
e_phone.grid(row=0, column=1, padx=5)
e_email.grid(row=0, column=2, padx=5)

tk.Button(form, text="Добавить клиента",
          bg=ACCENT, fg="white",
          command=add_client).grid(row=0, column=3, padx=5)

# -----------------------------
# TABLES
# -----------------------------
columns = ("ID", "Имя", "Телефон", "Email")
tree = ttk.Treeview(content, columns=columns, show="headings", height=8)

for c in columns:
    tree.heading(c, text=c)
    tree.column(c, width=150)

tree.pack(pady=10)

tk.Button(content, text="Удалить клиента",
          bg="red", fg="white",
          command=delete_client).pack()

# -----------------------------
# PURCHASES
# -----------------------------
p_frame = tk.Frame(content, bg=BG)
p_frame.pack(pady=10)

e_amount = tk.Entry(p_frame, width=20)
e_amount.pack(side="left", padx=5)

tk.Button(p_frame, text="Добавить покупку",
          bg="#4e9af1", fg="white",
          command=add_purchase).pack(side="left", padx=5)

tk.Button(p_frame, text="График",
          bg="#9b59b6", fg="white",
          command=show_graph).pack(side="left", padx=5)

# -----------------------------
# ANALYTICS
# -----------------------------
tk.Label(content, text="ТОП КЛИЕНТОВ",
         bg=BG, fg="white",
         font=("Arial", 14, "bold")).pack()

columns2 = ("Клиент", "Сумма")
tree_stats = ttk.Treeview(content, columns=columns2, show="headings", height=8)

for c in columns2:
    tree_stats.heading(c, text=c)
    tree_stats.column(c, width=200)

tree_stats.pack()

# -----------------------------
# START
# -----------------------------
load_clients()

root.mainloop()
