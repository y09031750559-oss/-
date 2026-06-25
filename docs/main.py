import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

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

conn.commit()


# -----------------------------
# ФУНКЦИИ
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


def delete_client():
    selected_item = tree.selection()

    if not selected_item:
        messagebox.showerror("Ошибка", "Выбери клиента")
        return

    item = tree.item(selected_item[0])
    client_id = item["values"][0]

    cursor.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()

    load_clients()


def load_clients():
    for row in tree.get_children():
        tree.delete(row)

    cursor.execute("SELECT id, name, phone, email FROM clients")
    for client in cursor.fetchall():
        tree.insert("", tk.END, values=client)


def search_client():
    query = entry_search.get()

    for row in tree.get_children():
        tree.delete(row)

    cursor.execute(
        "SELECT id, name, phone, email FROM clients WHERE name LIKE ?",
        ('%' + query + '%',)
    )

    for client in cursor.fetchall():
        tree.insert("", tk.END, values=client)


def show_all():
    entry_search.delete(0, tk.END)
    load_clients()


# -----------------------------
# UI
# -----------------------------
root = tk.Tk()
root.title("CRM система")
root.geometry("800x550")


# ===== ФОРМА =====
frame_form = tk.Frame(root)
frame_form.pack(pady=10)

tk.Label(frame_form, text="Имя").grid(row=0, column=0)
entry_name = tk.Entry(frame_form)
entry_name.grid(row=0, column=1, padx=5)

tk.Label(frame_form, text="Телефон").grid(row=0, column=2)
entry_phone = tk.Entry(frame_form)
entry_phone.grid(row=0, column=3, padx=5)

tk.Label(frame_form, text="Email").grid(row=0, column=4)
entry_email = tk.Entry(frame_form)
entry_email.grid(row=0, column=5, padx=5)


tk.Button(root, text="Добавить клиента", command=add_client,
          bg="green", fg="white").pack(pady=5)

tk.Button(root, text="Удалить выбранного клиента", command=delete_client,
          bg="red", fg="white").pack(pady=5)


# ===== ПОИСК =====
frame_search = tk.Frame(root)
frame_search.pack(pady=10)

tk.Label(frame_search, text="Поиск по имени").pack(side="left")

entry_search = tk.Entry(frame_search)
entry_search.pack(side="left", padx=5)

tk.Button(frame_search, text="Найти", command=search_client).pack(side="left", padx=5)
tk.Button(frame_search, text="Показать всех", command=show_all).pack(side="left", padx=5)


# ===== ТАБЛИЦА =====
frame_table = tk.Frame(root)
frame_table.pack(fill="both", expand=True)

columns = ("ID", "Имя", "Телефон", "Email")

tree = ttk.Treeview(frame_table, columns=columns, show="headings")

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=150)

scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side="right", fill="y")
tree.pack(fill="both", expand=True)


load_clients()

root.mainloop()
