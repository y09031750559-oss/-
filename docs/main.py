import sqlite3
import tkinter as tk
from tkinter import messagebox

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


def load_clients():
    listbox.delete(0, tk.END)

    cursor.execute("SELECT id, name, phone, email FROM clients")
    for client in cursor.fetchall():
        listbox.insert(
            tk.END,
            f"{client[0]} | {client[1]} | {client[2]} | {client[3]}"
        )


# -----------------------------
# UI (ИНТЕРФЕЙС)
# -----------------------------
root = tk.Tk()
root.title("CRM система")
root.geometry("600x400")


# Поля ввода
tk.Label(root, text="Имя").pack()
entry_name = tk.Entry(root)
entry_name.pack()

tk.Label(root, text="Телефон").pack()
entry_phone = tk.Entry(root)
entry_phone.pack()

tk.Label(root, text="Email").pack()
entry_email = tk.Entry(root)
entry_email.pack()

tk.Button(root, text="Добавить клиента", command=add_client).pack(pady=10)


# Список клиентов
listbox = tk.Listbox(root, width=80)
listbox.pack(pady=10)


# загрузка данных при старте
load_clients()

root.mainloop()
