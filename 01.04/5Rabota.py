import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import hashlib
import re
from datetime import datetime
import os
import csv

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('travel.db')
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Роли
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
        ''')
        self.cursor.execute("INSERT OR IGNORE INTO roles VALUES (1, 'admin')")
        self.cursor.execute("INSERT OR IGNORE INTO roles VALUES (2, 'user')")
        
        # Пользователи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                email TEXT UNIQUE,
                phone TEXT,
                role_id INTEGER,
                dark_mode INTEGER DEFAULT 0,
                FOREIGN KEY (role_id) REFERENCES roles(id)
            )
        ''')
        
        # Админ по умолчанию
        admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (username, password, email, phone, role_id)
            VALUES ('admin', ?, 'admin@example.com', '123456', 1)
        ''', (admin_pass,))
        
        # Билеты
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destination TEXT,
                date TEXT,
                price REAL,
                user_id INTEGER
            )
        ''')
        
        # Отели
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS hotels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                city TEXT,
                price REAL,
                user_id INTEGER
            )
        ''')
        
        # Развлечения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS entertainments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                city TEXT,
                price REAL,
                user_id INTEGER
            )
        ''')
        
        # Логи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT,
                user TEXT,
                action TEXT
            )
        ''')
        
        self.conn.commit()
    
    def log(self, user, action):
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute("INSERT INTO logs (time, user, action) VALUES (?, ?, ?)", (time, user, action))
        self.conn.commit()
        
        os.makedirs('logs', exist_ok=True)
        with open(f'logs/app.log', 'a', encoding='utf-8') as f:
            f.write(f'[{time}] [{user}] [{action}]\n')

class TravelApp:
    def __init__(self):
        self.db = Database()
        self.current_user = None
        self.login_attempts = 0
        self.blocked_until = None
        
        self.root = tk.Tk()
        self.root.title('Туристическое агентство')
        self.root.geometry('1000x600')
        
        self.show_login()
        self.root.mainloop()
    
    def show_login(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        frame = tk.Frame(self.root, padx=50, pady=50)
        frame.pack(expand=True)
        
        tk.Label(frame, text='Вход в систему', font=('Arial', 20)).pack(pady=20)
        
        tk.Label(frame, text='Логин:').pack()
        self.login_entry = tk.Entry(frame, width=30)
        self.login_entry.pack(pady=5)
        
        tk.Label(frame, text='Пароль:').pack()
        self.pass_entry = tk.Entry(frame, width=30, show='*')
        self.pass_entry.pack(pady=5)
        
        tk.Button(frame, text='Войти', command=self.login, width=20).pack(pady=10)
        tk.Button(frame, text='Регистрация', command=self.show_register, width=20).pack()
    
    def login(self):
        if self.blocked_until and datetime.now() < self.blocked_until:
            remaining = (self.blocked_until - datetime.now()).seconds
            messagebox.showerror('Ошибка', f'Подождите {remaining} секунд')
            return
        
        username = self.login_entry.get()
        password = hashlib.sha256(self.pass_entry.get().encode()).hexdigest()
        
        self.db.cursor.execute('''
            SELECT u.id, u.username, u.role_id, r.name 
            FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.username = ? AND u.password = ?
        ''', (username, password))
        
        user = self.db.cursor.fetchone()
        
        if user:
            self.current_user = {'id': user[0], 'username': user[1], 'role_id': user[2], 'role': user[3]}
            self.login_attempts = 0
            self.db.log(username, 'Вход в систему')
            self.show_main()
        else:
            self.login_attempts += 1
            if self.login_attempts >= 3:
                import time
                self.blocked_until = datetime.fromtimestamp(time.time() + 30)
                messagebox.showerror('Ошибка', '3 неудачные попытки. Блокировка 30 секунд')
            else:
                messagebox.showerror('Ошибка', f'Неверный логин или пароль. Осталось попыток: {3 - self.login_attempts}')
    
    def show_register(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        frame = tk.Frame(self.root, padx=50, pady=30)
        frame.pack(expand=True)
        
        tk.Label(frame, text='Регистрация', font=('Arial', 20)).pack(pady=20)
        
        fields = [
            ('Логин:', 'login'),
            ('Пароль:', 'pass1'),
            ('Подтверждение:', 'pass2'),
            ('Email:', 'email'),
            ('Телефон:', 'phone')
        ]
        
        self.reg_entries = {}
        for label, key in fields:
            tk.Label(frame, text=label).pack()
            entry = tk.Entry(frame, width=30)
            entry.pack(pady=5)
            if 'pass' in key:
                entry.config(show='*')
            self.reg_entries[key] = entry
        
        tk.Button(frame, text='Зарегистрироваться', command=self.register, width=25).pack(pady=20)
        tk.Button(frame, text='Назад', command=self.show_login, width=25).pack()
    
    def validate_password(self, password):
        if len(password) < 8:
            return False, 'Минимум 8 символов'
        if not re.search(r'[A-Z]', password):
            return False, 'Нужна заглавная буква'
        if not re.search(r'[0-9]', password):
            return False, 'Нужна цифра'
        if not re.search(r'[!@#$%^&*]', password):
            return False, 'Нужен спецсимвол (!@#$%^&*)'
        return True, 'OK'
    
    def validate_email(self, email):
        # Стандартная валидация email
        # ПРИМЕЧАНИЕ: Требование про "admin" в домене является ошибочным
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def register(self):
        login = self.reg_entries['login'].get()
        password = self.reg_entries['pass1'].get()
        password2 = self.reg_entries['pass2'].get()
        email = self.reg_entries['email'].get()
        phone = self.reg_entries['phone'].get()
        
        if not all([login, password, email, phone]):
            messagebox.showerror('Ошибка', 'Заполните все поля')
            return
        
        if password != password2:
            messagebox.showerror('Ошибка', 'Пароли не совпадают')
            return
        
        valid, msg = self.validate_password(password)
        if not valid:
            messagebox.showerror('Ошибка', msg)
            return
        
        if not self.validate_email(email):
            messagebox.showerror('Ошибка', 'Неверный формат email')
            return
        
        self.db.cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (login, email))
        if self.db.cursor.fetchone():
            messagebox.showerror('Ошибка', 'Пользователь с таким логином или email уже существует')
            return
        
        hashed_pass = hashlib.sha256(password.encode()).hexdigest()
        self.db.cursor.execute('''
            INSERT INTO users (username, password, email, phone, role_id)
            VALUES (?, ?, ?, ?, 2)
        ''', (login, hashed_pass, email, phone))
        self.db.conn.commit()
        
        self.db.log(login, 'Регистрация')
        messagebox.showinfo('Успех', 'Регистрация выполнена!')
        self.show_login()
    
    def show_main(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        menu_file = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Меню', menu=menu_file)
        menu_file.add_command(label='Билеты', command=self.show_tickets)
        menu_file.add_command(label='Отели', command=self.show_hotels)
        menu_file.add_command(label='Развлечения', command=self.show_entertainments)
        menu_file.add_separator()
        menu_file.add_command(label='Выйти', command=self.logout)
        
        frame = tk.Frame(self.root, padx=50, pady=50)
        frame.pack(expand=True)
        
        tk.Label(frame, text=f'Добро пожаловать, {self.current_user["username"]}!', 
                font=('Arial', 18)).pack(pady=20)
        tk.Label(frame, text=f'Роль: {self.current_user["role"]}', font=('Arial', 12)).pack()
        
        self.db.cursor.execute('SELECT COUNT(*) FROM tickets')
        tickets_count = self.db.cursor.fetchone()[0]
        
        self.db.cursor.execute('SELECT COUNT(*) FROM hotels')
        hotels_count = self.db.cursor.fetchone()[0]
        
        self.db.cursor.execute('SELECT COUNT(*) FROM entertainments')
        ent_count = self.db.cursor.fetchone()[0]
        
        info = f'Статистика:\nБилетов: {tickets_count}\nОтелей: {hotels_count}\nРазвлечений: {ent_count}'
        tk.Label(frame, text=info, font=('Arial', 12), justify='left').pack(pady=20)
        
        tk.Button(frame, text='Управление билетами', command=self.show_tickets, width=25).pack(pady=5)
        tk.Button(frame, text='Управление отелями', command=self.show_hotels, width=25).pack(pady=5)
        tk.Button(frame, text='Управление развлечениями', command=self.show_entertainments, width=25).pack(pady=5)
        tk.Button(frame, text='Выйти', command=self.logout, width=25).pack(pady=20)
    
    def show_tickets(self):
        self.show_entity_window('tickets', 'Билеты', ['destination', 'date', 'price'], 
                                ['Назначение', 'Дата', 'Цена'])
    
    def show_hotels(self):
        self.show_entity_window('hotels', 'Отели', ['name', 'city', 'price'],
                                ['Название', 'Город', 'Цена'])
    
    def show_entertainments(self):
        self.show_entity_window('entertainments', 'Развлечения', ['name', 'city', 'price'],
                                ['Название', 'Город', 'Цена'])
    
    def show_entity_window(self, table, title, db_fields, display_fields):
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry('800x500')
        
        frame_list = tk.Frame(window)
        frame_list.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('id',) + tuple(db_fields)
        tree = ttk.Treeview(frame_list, columns=columns, show='headings')
        
        tree.heading('id', text='ID')
        for i, field in enumerate(display_fields):
            tree.heading(db_fields[i], text=field)
            tree.column(db_fields[i], width=150)
        
        tree.pack(fill='both', expand=True)
        
        def refresh():
            for item in tree.get_children():
                tree.delete(item)
            
            if self.current_user['role'] == 'admin':
                self.db.cursor.execute(f'SELECT * FROM {table}')
            else:
                self.db.cursor.execute(f'SELECT * FROM {table} WHERE user_id = ?', (self.current_user['id'],))
            
            for row in self.db.cursor.fetchall():
                tree.insert('', 'end', values=row)
        
        btn_frame = tk.Frame(window)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text='Добавить', 
                 command=lambda: self.add_entity(table, db_fields, display_fields, refresh)).pack(side='left', padx=5)
        tk.Button(btn_frame, text='Редактировать', 
                 command=lambda: self.edit_entity(table, db_fields, display_fields, tree, refresh)).pack(side='left', padx=5)
        tk.Button(btn_frame, text='Удалить', 
                 command=lambda: self.delete_entity(table, tree, refresh)).pack(side='left', padx=5)
        tk.Button(btn_frame, text='Экспорт в CSV', 
                 command=lambda: self.export_to_csv(table, display_fields)).pack(side='left', padx=5)
        
        refresh()
    
    def add_entity(self, table, db_fields, display_fields, refresh):
        window = tk.Toplevel()
        window.title('Добавить запись')
        
        entries = {}
        for i, (db_field, display_field) in enumerate(zip(db_fields, display_fields)):
            tk.Label(window, text=display_field).grid(row=i, column=0, padx=10, pady=5)
            entry = tk.Entry(window, width=30)
            entry.grid(row=i, column=1, padx=10, pady=5)
            entries[db_field] = entry
        
        def save():
            values = []
            for db_field in db_fields:
                val = entries[db_field].get()
                if not val:
                    messagebox.showerror('Ошибка', f'Заполните поле "{display_fields[db_fields.index(db_field)]}"')
                    return
                if db_field == 'price':
                    try:
                        val = float(val)
                    except:
                        messagebox.showerror('Ошибка', 'Цена должна быть числом')
                        return
                values.append(val)
            
            placeholders = ','.join(['?' for _ in db_fields])
            if self.current_user['role'] == 'admin':
                query = f'INSERT INTO {table} ({",".join(db_fields)}) VALUES ({placeholders})'
                self.db.cursor.execute(query, values)
            else:
                query = f'INSERT INTO {table} ({",".join(db_fields)}, user_id) VALUES ({placeholders}, ?)'
                self.db.cursor.execute(query, values + [self.current_user['id']])
            
            self.db.conn.commit()
            self.db.log(self.current_user['username'], f'Добавление в {table}')
            messagebox.showinfo('Успех', 'Запись добавлена')
            window.destroy()
            refresh()
        
        tk.Button(window, text='Сохранить', command=save).grid(row=len(db_fields), column=0, columnspan=2, pady=20)
    
    def edit_entity(self, table, db_fields, display_fields, tree, refresh):
        selected = tree.selection()
        if not selected:
            messagebox.showerror('Ошибка', 'Выберите запись')
            return
        
        item = tree.item(selected[0])
        record_id = item['values'][0]
        
        window = tk.Toplevel()
        window.title('Редактировать запись')
        
        entries = {}
        current_values = item['values'][1:]
        
        for i, (db_field, display_field, value) in enumerate(zip(db_fields, display_fields, current_values)):
            tk.Label(window, text=display_field).grid(row=i, column=0, padx=10, pady=5)
            entry = tk.Entry(window, width=30)
            entry.insert(0, str(value))
            entry.grid(row=i, column=1, padx=10, pady=5)
            entries[db_field] = entry
        
        def save():
            values = []
            for db_field in db_fields:
                val = entries[db_field].get()
                if not val:
                    messagebox.showerror('Ошибка', f'Заполните поле "{display_fields[db_fields.index(db_field)]}"')
                    return
                if db_field == 'price':
                    try:
                        val = float(val)
                    except:
                        messagebox.showerror('Ошибка', 'Цена должна быть числом')
                        return
                values.append(val)
            
            set_clause = ', '.join([f'{field} = ?' for field in db_fields])
            query = f'UPDATE {table} SET {set_clause} WHERE id = ?'
            self.db.cursor.execute(query, values + [record_id])
            self.db.conn.commit()
            self.db.log(self.current_user['username'], f'Редактирование в {table}')
            messagebox.showinfo('Успех', 'Запись обновлена')
            window.destroy()
            refresh()
        
        tk.Button(window, text='Сохранить', command=save).grid(row=len(db_fields), column=0, columnspan=2, pady=20)
    
    def delete_entity(self, table, tree, refresh):
        selected = tree.selection()
        if not selected:
            messagebox.showerror('Ошибка', 'Выберите запись')
            return
        
        item = tree.item(selected[0])
        record_id = item['values'][0]
        
        result = messagebox.askyesno('Подтверждение', 
            f'Вы действительно хотите удалить запись №{record_id}? '
            'Это действие нельзя отменить, и все ваши котики умрут от грусти.')
        
        if result:
            self.db.cursor.execute(f'DELETE FROM {table} WHERE id = ?', (record_id,))
            self.db.conn.commit()
            self.db.log(self.current_user['username'], f'Удаление из {table}')
            refresh()
    
    def export_to_csv(self, table, display_fields):
        filename = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV files', '*.csv')])
        if filename:
            if self.current_user['role'] == 'admin':
                self.db.cursor.execute(f'SELECT * FROM {table}')
            else:
                self.db.cursor.execute(f'SELECT * FROM {table} WHERE user_id = ?', (self.current_user['id'],))
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['ID'] + display_fields)
                for row in self.db.cursor.fetchall():
                    writer.writerow(row)
            
            messagebox.showinfo('Успех', f'Экспортировано в {filename}')
    
    def logout(self):
        if messagebox.askyesno('Выход', 'Вы уверены, что хотите выйти?'):
            self.db.log(self.current_user['username'], 'Выход из системы')
            self.current_user = None
            self.show_login()

if __name__ == '__main__':
    app = TravelApp()