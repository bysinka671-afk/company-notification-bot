import sqlite3
import os

class Database:
    def __init__(self, db_name='company_bot.db'):
        self.db_name = db_name
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                department TEXT DEFAULT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                department TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, full_name):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)', 
                      (user_id, username, full_name))
        conn.commit()
        conn.close()
    
    def update_department(self, user_id, department):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        is_admin = (department.upper() == "IT")
        cursor.execute('UPDATE users SET department = ?, is_admin = ? WHERE user_id = ?', 
                      (department, is_admin, user_id))
        conn.commit()
        conn.close()
    
    def get_user(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def get_users_by_department(self, department):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE department = ?', (department,))
        users = cursor.fetchall()
        conn.close()
        return [user[0] for user in users]
    
    def get_all_users(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        conn.close()
        return [user[0] for user in users]
    
    def save_post(self, admin_id, department, message):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO posts (admin_id, department, message) VALUES (?, ?, ?)', 
                      (admin_id, department, message))
        conn.commit()
        conn.close()