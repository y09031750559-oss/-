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
# APP
# -----------------------------
root = tk.Tk()
root.title("CRM SAFE VERSION")
root.geometry("900x650")

# -----------------------------
# FUNCTIONS
# -----------------------------
def load_clients():
    for i in tree.get_children():
        tree.delete(i)

    cursor.execute("SELECT * FROM clients")
    for row in cursor.fetchall():
        tree.insert("", "end", values=row)

    load_analytics()
    update_kpi()

def load_analytics():
    for i in tree_stats.get_children():
        tree_stats.delete(i)

    cursor.execute("""
        SELECT clients.name,
               COALESCE(SUM(purchases.amount),0),
               MAX(purchases.date)
        FROM clients
        LEFT JOIN purchases ON clients.id = purchases.client_id
        GROUP BY clients.id
    """)

    for name, total, last_date in cursor.fetchall():

        status = "🟢 активный"

        if last_date:
            try:
                last = datetime.strptime(last_date, "%Y-%m-%d %H:%M")
                days = (datetime.now() - last).days

                if days >= 90:
                    status = "🔴 90+ дней"
                elif days >= 60:
                    status = "🟠 60 дней"
                elif days >= 30:
                    status = "🟡 30 дней"
            except:
                status = "🟡 нет данных"

        tree_stats.insert("", "end", values=(name, total, status))

def add_client():
    name = entry_name.get()

    if not name:
        messagebox.showerror("Ошибка", "Введите имя")
        return

    cursor.execute(
        "INSERT INTO clients(name,phone,email) VALUES(?,?,?)",
        (name, entry_phone.get(), entry_email.get())
    )
    conn.commit()

    entry_name.delete(0, tk.END)
    entry_phone.delete(0, tk.END)
    entry_email.delete(0, tk.END)

    load_clients()

def delete_client():
    sel = tree.selection()
    if not sel:
        messagebox.showerror("Ошибка", "Выбери клиента")
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
        amount = float(entry_amount.get())
    except:
        messagebox.showerror("Ошибка", "Сумма должна быть числом")
        return

    cid = tree.item(sel[0])["values"][0]
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute(
        "INSERT INTO purchases(client_id,amount,date) VALUES(?,?,?)",
        (cid, amount, date)
    )
    conn.commit()

    entry_amount.delete(0, tk.END)
    load_clients()

def show_graph():
    cursor.execute("""
        SELECT date, SUM(amount)
        FROM purchases
        GROUP BY date(date)
        ORDER BY date
    """)

    data = cursor.fetchall()

    if not data:
        messagebox.showerror("Ошибка", "Нет данных")
        return

    x = [i[0] for i in data]
    y = [i[1] for i in data]

    plt.figure(figsize=(9,4))
    plt.plot(x, y, marker="o")
    plt.xticks(rotation=45)
    plt.title("Доход")
    plt.tight_layout()
    plt.show()

def update_kpi():
    cursor.execute("SELECT COUNT(*) FROM clients")
    clients = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(amount),0) FROM purchases")
    money = cursor.fetchone()[0]

    kpi_clients.config(text=f"Клиенты: {clients}")
    kpi_money.config(text=f"Доход: {money}")

# -----------------------------
# UI
# -----------------------------
frame = tk.Frame(root)
frame.pack(pady=10)

entry_name = tk.Entry(frame)
entry_phone = tk.Entry(frame)
entry_email = tk.Entry(frame)

entry_name.insert(0, "Имя")
entry_phone.insert(0, "Телефон")
entry_email.insert(0, "Email")

entry_name.grid(row=0, column=0)
entry_phone.grid(row=0, column=1)
entry_email.grid(row=0, column=2)

tk.Button(frame, text="Добавить клиента", command=add_client).grid(row=0, column=3)

# -----------------------------
# CLIENT TABLE
# -----------------------------
columns = ("ID", "Имя", "Телефон", "Email")
tree = ttk.Treeview(root, columns=columns, show="headings")

for c in columns:
    tree.heading(c, text=c)
    tree.column(c, width=150)

tree.pack()

tk.Button(root, text="Удалить клиента", command=delete_client).pack(pady=5)

# -----------------------------
# PURCHASES
# -----------------------------
bottom = tk.Frame(root)
bottom.pack(pady=10)

entry_amount = tk.Entry(bottom)
entry_amount.pack(side="left")

tk.Button(bottom, text="Добавить покупку", command=add_purchase).pack(side="left")
tk.Button(bottom, text="График", command=show_graph).pack(side="left")

# -----------------------------
# ANALYTICS
# -----------------------------
tk.Label(root, text="ТОП КЛИЕНТОВ").pack()

columns2 = ("Клиент", "Сумма", "Статус")
tree_stats = ttk.Treeview(root, columns=columns2, show="headings")

for c in columns2:
    tree_stats.heading(c, text=c)
    tree_stats.column(c, width=200)

tree_stats.pack()

# -----------------------------
# KPI
# -----------------------------
kpi_frame = tk.Frame(root)
kpi_frame.pack(pady=10)

kpi_clients = tk.Label(kpi_frame, text="Клиенты: 0")
kpi_clients.pack(side="left", padx=10)

kpi_money = tk.Label(kpi_frame, text="Доход: 0")
kpi_money.pack(side="left", padx=10)

# -----------------------------
# START
# -----------------------------
load_clients()
root.mainloop()
