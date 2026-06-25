import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from datetime import datetime
import matplotlib.pyplot as plt

# -----------------------------
# БАЗА ДАННЫХ
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
# КЛИЕНТЫ
# -----------------------------
def add_client():
    name = entry_name.get()
    phone = entry_phone.get()
    email = entry_email.get()

    if not name:
        messagebox.showerror("Ошибка", "Имя обязательно")
        return

    cursor.execute(
        "INSERT INTO clients (name, phone, email) VALUES (?, ?, ?)",
        (name, phone, email)
    )
    conn.commit()

    entry_name.delete(0, tk.END)
    entry_phone.delete(0, tk.END)
    entry_email.delete(0, tk.END)

    load_clients()
    load_analytics()


def delete_client():
    selected = tree.selection()
    if not selected:
        messagebox.showerror("Ошибка", "Выбери клиента")
        return

    client_id = tree.item(selected[0])["values"][0]

    cursor.execute("DELETE FROM clients WHERE id=?", (client_id,))
    cursor.execute("DELETE FROM purchases WHERE client_id=?", (client_id,))
    conn.commit()

    load_clients()
    load_analytics()


def load_clients():
    for row in tree.get_children():
        tree.delete(row)

    cursor.execute("SELECT * FROM clients")
    for c in cursor.fetchall():
        tree.insert("", tk.END, values=c)


# -----------------------------
# ПОКУПКИ
# -----------------------------
def add_purchase():
    selected = tree.selection()
    if not selected:
        messagebox.showerror("Ошибка", "Выбери клиента")
        return

    amount = entry_amount.get()
    if not amount:
        messagebox.showerror("Ошибка", "Введите сумму")
        return

    client_id = tree.item(selected[0])["values"][0]
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute(
        "INSERT INTO purchases (client_id, amount, date) VALUES (?, ?, ?)",
        (client_id, amount, date)
    )
    conn.commit()

    entry_amount.delete(0, tk.END)
    load_analytics()


# -----------------------------
# АНАЛИТИКА
# -----------------------------
def load_analytics():
    for row in tree_stats.get_children():
        tree_stats.delete(row)

    cursor.execute("""
        SELECT clients.name,
               IFNULL(SUM(purchases.amount), 0)
        FROM clients
        LEFT JOIN purchases ON clients.id = purchases.client_id
        GROUP BY clients.id
        ORDER BY 2 DESC
    """)

    for row in cursor.fetchall():
        tree_stats.insert("", tk.END, values=row)


# -----------------------------
# ГРАФИК
# -----------------------------
def show_graph():
    cursor.execute("""
        SELECT date, amount
        FROM purchases
        ORDER BY date
    """)

    data = cursor.fetchall()

    if not data:
        messagebox.showerror("Ошибка", "Нет данных для графика")
        return

    dates = [x[0] for x in data]
    amounts = [x[1] for x in data]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, amounts, marker="o")
    plt.xticks(rotation=45)
    plt.title("Доход по времени")
    plt.xlabel("Дата")
    plt.ylabel("Сумма")
    plt.tight_layout()
    plt.show()


# -----------------------------
# UI
# -----------------------------
root = tk.Tk()
root.title("CRM PRO SYSTEM")
root.geometry("900x700")


# ===== ФОРМА =====
frame = tk.Frame(root)
frame.pack(pady=10)

tk.Label(frame, text="Имя").grid(row=0, column=0)
entry_name = tk.Entry(frame)
entry_name.grid(row=0, column=1)

tk.Label(frame, text="Телефон").grid(row=0, column=2)
entry_phone = tk.Entry(frame)
entry_phone.grid(row=0, column=3)

tk.Label(frame, text="Email").grid(row=0, column=4)
entry_email = tk.Entry(frame)
entry_email.grid(row=0, column=5)


tk.Button(root, text="Добавить клиента", command=add_client,
          bg="green", fg="white").pack(pady=5)

tk.Button(root, text="Удалить клиента", command=delete_client,
          bg="red", fg="white").pack(pady=5)


# ===== ТАБЛИЦА КЛИЕНТОВ =====
columns = ("ID", "Имя", "Телефон", "Email")

tree = ttk.Treeview(root, columns=columns, show="headings")

for c in columns:
    tree.heading(c, text=c)
    tree.column(c, width=150)

tree.pack(fill="x")


# ===== ПОКУПКИ =====
frame2 = tk.Frame(root)
frame2.pack(pady=10)

tk.Label(frame2, text="Сумма покупки").pack(side="left")
entry_amount = tk.Entry(frame2)
entry_amount.pack(side="left", padx=5)

tk.Button(frame2, text="Добавить покупку",
          command=add_purchase,
          bg="blue", fg="white").pack(side="left")

tk.Button(frame2, text="📊 График дохода",
          command=show_graph,
          bg="purple", fg="white").pack(side="left", padx=10)


# ===== АНАЛИТИКА =====
tk.Label(root, text="ТОП КЛИЕНТОВ", font=("Arial", 14)).pack()

columns2 = ("Клиент", "Сумма покупок")

tree_stats = ttk.Treeview(root, columns=columns2, show="headings")

for c in columns2:
    tree_stats.heading(c, text=c)
    tree_stats.column(c, width=200)

tree_stats.pack(fill="both", expand=True)


# старт
load_clients()
load_analytics()

root.mainloop()
