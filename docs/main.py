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
root.title("CRM PRO SEGMENTS")
root.geometry("1100x750")
root.configure(bg="#1e1e2f")

# -----------------------------
# STYLE
# -----------------------------
style = ttk.Style()
style.theme_use("clam")

style.configure("Treeview",
    background="#2b2b40",
    fieldbackground="#2b2b40",
    foreground="white",
    rowheight=28
)

style.configure("Treeview.Heading",
    background="#4e9af1",
    foreground="white",
    font=("Arial", 10, "bold")
)

# -----------------------------
# FUNCTIONS
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
               COALESCE(SUM(purchases.amount),0),
               MAX(purchases.date)
        FROM clients
        LEFT JOIN purchases ON clients.id = purchases.client_id
        GROUP BY clients.id
        ORDER BY 2 DESC
    """)

    for name, total, last_date in cursor.fetchall():

        if last_date:
            last = datetime.strptime(last_date, "%Y-%m-%d %H:%M")
            days = (datetime.now() - last).days
        else:
            days = 9999

        if days >= 90:
            status = "🔴 90+ дней (спящий клиент)"
        elif days >= 60:
            status = "🟠 60 дней"
        elif days >= 30:
            status = "🟡 30 дней"
        else:
            status = "🟢 активный"

        tree_stats.insert("", "end", values=(name, total, status))

def add_client():
    name = e_name.get()

    if not name or name == "Имя":
        messagebox.showerror("Ошибка", "Введите имя")
        return

    cursor.execute(
        "INSERT INTO clients(name,phone,email) VALUES(?,?,?)",
        (name, e_phone.get(), e_email.get())
    )
    conn.commit()

    e_name.delete(0, tk.END)
    e_phone.delete(0, tk.END)
    e_email.delete(0, tk.END)

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
        amount = float(e_amount.get())
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

    e_amount.delete(0, tk.END)
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
    plt.title("Доход по времени")
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
# UI LAYOUT
# -----------------------------
content = tk.Frame(root, bg="#1e1e2f")
content.pack(fill="both", expand=True)

# KPI
kpi_frame = tk.Frame(content, bg="#1e1e2f")
kpi_frame.pack(pady=15)

kpi_clients = tk.Label(kpi_frame, text="Клиенты: 0",
                       bg="#4e9af1", fg="white",
                       font=("Arial", 14, "bold"),
                       padx=20, pady=15)
kpi_clients.pack(side="left", padx=10)

kpi_money = tk.Label(kpi_frame, text="Доход: 0",
                     bg="#27ae60", fg="white",
                     font=("Arial", 14, "bold"),
                     padx=20, pady=15)
kpi_money.pack(side="left", padx=10)

# FORM
form = tk.Frame(content, bg="#1e1e2f")
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
          bg="#4e9af1", fg="white",
          command=add_client).grid(row=0, column=3, padx=5)

# CLIENT TABLE
columns = ("ID", "Имя", "Телефон", "Email")
tree = ttk.Treeview(content, columns=columns, show="headings", height=8)

for c in columns:
    tree.heading(c, text=c)
    tree.column(c, width=150)

tree.pack(pady=10)

tk.Button(content, text="Удалить клиента",
          bg="red", fg="white",
          command=delete_client).pack(pady=5)

# PURCHASES
p_frame = tk.Frame(content, bg="#1e1e2f")
p_frame.pack(pady=10)

e_amount = tk.Entry(p_frame, width=20)
e_amount.pack(side="left", padx=5)

tk.Button(p_frame, text="Добавить покупку",
          bg="#4e9af1", fg="white",
          command=add_purchase).pack(side="left", padx=5)

tk.Button(p_frame, text="График",
          bg="#9b59b6", fg="white",
          command=show_graph).pack(side="left", padx=5)

# ANALYTICS
tk.Label(content,
         text="ТОП КЛИЕНТОВ (сегменты)",
         bg="#1e1e2f",
         fg="white",
         font=("Arial", 14, "bold")).pack()

columns2 = ("Клиент", "Сумма", "Статус")
tree_stats = ttk.Treeview(content, columns=columns2, show="headings", height=8)

for c in columns2:
    tree_stats.heading(c, text=c)
    tree_stats.column(c, width=200)

tree_stats.pack()

# START
load_clients()
root.mainloop()
