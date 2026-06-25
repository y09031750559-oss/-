import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

# -----------------------------
# DATABASE
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
# UI ROOT
# -----------------------------
root = tk.Tk()
root.title("CRM PRO SYSTEM")
root.geometry("1000x700")
root.configure(bg="#f2f4f8")

# -----------------------------
# STYLE
# -----------------------------
style = ttk.Style()
style.theme_use("clam")

style.configure("Treeview",
    background="#ffffff",
    fieldbackground="#ffffff",
    rowheight=28,
    font=("Arial", 10)
)

style.configure("Treeview.Heading",
    font=("Arial", 11, "bold"),
    background="#34495e",
    foreground="white"
)

# -----------------------------
# BUTTON STYLE
# -----------------------------
def make_button(parent, text, cmd, color):
    return tk.Button(
        parent,
        text=text,
        command=cmd,
        bg=color,
        fg="white",
        activebackground="#222",
        font=("Arial", 10, "bold"),
        padx=10,
        pady=5,
        border=0
    )

# -----------------------------
# FUNCTIONS
# -----------------------------
def load_clients():
    for row in tree.get_children():
        tree.delete(row)

    cursor.execute("SELECT * FROM clients")
    for c in cursor.fetchall():
        tree.insert("", tk.END, values=c)

def load_analytics():
    for row in tree_stats.get_children():
        tree_stats.delete(row)

    cursor.execute("""
        SELECT clients.name,
               COALESCE(SUM(purchases.amount), 0)
        FROM clients
        LEFT JOIN purchases ON clients.id = purchases.client_id
        GROUP BY clients.id
        ORDER BY 2 DESC
    """)

    for row in cursor.fetchall():
        tree_stats.insert("", tk.END, values=row)

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

def add_purchase():
    selected = tree.selection()
    if not selected:
        messagebox.showerror("Ошибка", "Выбери клиента")
        return

    try:
        amount = float(entry_amount.get())
    except ValueError:
        messagebox.showerror("Ошибка", "Сумма должна быть числом")
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

def show_graph():
    cursor.execute("""
        SELECT date(date), SUM(amount)
        FROM purchases
        GROUP BY date(date)
        ORDER BY date(date)
    """)

    data = cursor.fetchall()

    if not data:
        messagebox.showerror("Ошибка", "Нет данных")
        return

    dates = [x[0] for x in data]
    amounts = [x[1] for x in data]

    plt.figure(figsize=(10,5))
    plt.plot(dates, amounts, marker="o")
    plt.xticks(rotation=45)
    plt.title("Доход по дням")
    plt.xlabel("Дата")
    plt.ylabel("Сумма")
    plt.tight_layout()
    plt.show()

# -----------------------------
# TOP FORM
# -----------------------------
top = tk.Frame(root, bg="#f2f4f8")
top.pack(pady=10)

tk.Label(top, text="Имя").grid(row=0, column=0)
entry_name = tk.Entry(top)
entry_name.grid(row=0, column=1, padx=5)

tk.Label(top, text="Телефон").grid(row=0, column=2)
entry_phone = tk.Entry(top)
entry_phone.grid(row=0, column=3, padx=5)

tk.Label(top, text="Email").grid(row=0, column=4)
entry_email = tk.Entry(top)
entry_email.grid(row=0, column=5, padx=5)

make_button(top, "Добавить", add_client, "#2ecc71").grid(row=0, column=6, padx=5)
make_button(top, "Удалить", delete_client, "#e74c3c").grid(row=0, column=7, padx=5)

# -----------------------------
# MIDDLE
# -----------------------------
middle = tk.Frame(root, bg="#f2f4f8")
middle.pack(fill="both", expand=True)

left = tk.Frame(middle, bg="#f2f4f8")
left.pack(side="left", fill="both", expand=True, padx=10)

right = tk.Frame(middle, bg="#f2f4f8")
right.pack(side="right", fill="both", expand=True, padx=10)

# -----------------------------
# CLIENT TABLE
# -----------------------------
columns = ("ID", "Имя", "Телефон", "Email")
tree = ttk.Treeview(left, columns=columns, show="headings")

for c in columns:
    tree.heading(c, text=c)
    tree.column(c, width=120)

tree.pack(fill="both", expand=True)

# -----------------------------
# PURCHASES
# -----------------------------
bottom = tk.Frame(root, bg="#f2f4f8")
bottom.pack(pady=10)

tk.Label(bottom, text="Сумма покупки").pack(side="left")
entry_amount = tk.Entry(bottom, width=15)
entry_amount.pack(side="left", padx=5)

make_button(bottom, "Добавить покупку", add_purchase, "#3498db").pack(side="left", padx=5)
make_button(bottom, "График", show_graph, "#9b59b6").pack(side="left", padx=5)

# -----------------------------
# ANALYTICS
# -----------------------------
tk.Label(right, text="ТОП КЛИЕНТОВ", font=("Arial", 14)).pack()

columns2 = ("Клиент", "Сумма")
tree_stats = ttk.Treeview(right, columns=columns2, show="headings")

for c in columns2:
    tree_stats.heading(c, text=c)
    tree_stats.column(c, width=150)

tree_stats.pack(fill="both", expand=True)

# -----------------------------
# INIT
# -----------------------------
load_clients()
load_analytics()

root.mainloop()
