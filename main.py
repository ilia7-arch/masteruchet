
import http.server
import socketserver
import urllib.parse
import os
import psycopg2
from psycopg2.extras import DictCursor

DATABASE_URL = "postgresql://masteruchet_db_user:fLBcxcwFr5LohplltvDfpYlCZiRuSw3f@://render.com"

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)
    return conn, conn.cursor()

def init_db():
    conn, c = get_db_connection()
    c.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS clients (id SERIAL PRIMARY KEY, user_id INTEGER, name TEXT, phone TEXT, address TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, client_id INTEGER, description TEXT, status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS materials (id SERIAL PRIMARY KEY, order_id INTEGER, name TEXT, quantity REAL, price REAL)")
    conn.commit()
    conn.close()
    print("БАЗА ДАННЫХ УСПЕШНО ИНИЦИАЛИЗИРОВАНА!")

init_db()

class MasterUchetHandler(http.server.SimpleHTTPRequestHandler):
    
    def get_user_from_cookie(self):
        try:
            cookie_header = self.headers.get('Cookie', '')
            if 'user_id=' in cookie_header:
                for item in cookie_header.split(';'):
                    item = item.strip()
                    if item.startswith('user_id='):
                        val = item.replace('user_id=', '').strip()
                        if val.isdigit():
                            return int(val)
        except:
            pass
        return None

    def render_login_page(self, error=""):
        err_html = f"<p style='color:#E30613;text-align:center;'>{error}</p>" if error else ""
        html = f"""<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><style>
        body{{font-family:-apple-system;background:#F5F5F7;padding:20px;display:flex;align-items:center;justify-content:center;height:90vh;margin:0;}}
        .auth-card{{background:white;padding:25px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);width:100%;max-width:320px;}}
        input{{width:100%;padding:10px;margin:8px 0;border:1px solid #D2D2D7;border-radius:8px;box-sizing:border-box;}}
        .btn{{width:100%;background:#0071E3;color:white;padding:12px;border:none;border-radius:8px;font-weight:bold;margin-top:10px;cursor:pointer;}}
        .btn-reg{{background:#424245;}}
        </style></head><body><div class='auth-card'>
        <h2 style='text-align:center;margin-top:0;'>Мастер-Учёт 🛠️</h2>
        {err_html}
        <form method='POST'>
        <input type='text' name='username' placeholder='Логин' required>
        <input type='password' name='password' placeholder='Пароль' required>
        <button type='submit' formaction='/login' class='btn'>Войти в кабинет</button>
        <button type='submit' formaction='/register' class='btn btn-reg'>Создать новый аккаунт</button>
        </form></div></body></html>"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ""
            params = urllib.parse.parse_qs(post_data)
        except:
            self.send_response(303); self.send_header("Location", "/"); self.end_headers(); return
        
        username = params.get("username", [""]).strip()
        password = params.get("password", [""]).strip()
        
        if url.path == "/login":
            if not username or not password:
                self.render_login_page("Заполните все поля")
                return
            conn, c = get_db_connection()
            c.execute("SELECT id, password FROM users WHERE username = %s", (username,))
            user = c.fetchone()
            conn.close()
            if user and user['password'] == password:
                self.send_response(303)
                self.send_header("Set-Cookie", f"user_id={user['id']}; Path=/; HttpOnly")
                self.send_header("Location", "/")
                self.end_headers()
            else:
                self.render_login_page("Неверный логин или пароль")
                
        elif url.path == "/register":
            if not username or not password:
                self.render_login_page("Заполните все поля")
                return
            conn, c = get_db_connection()
            try:
                c.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id", (username, password))
                uid = c.fetchone()['id']
                conn.commit()
                conn.close()
                self.send_response(303)
                self.send_header("Set-Cookie", f"user_id={uid}; Path=/; HttpOnly")
                self.send_header("Location", "/")
                self.end_headers()
            except:
                try: conn.close()
                except: pass
                self.render_login_page("Такой логин уже занят")

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        user_id = self.get_user_from_cookie()
        
        if url.path == "/logout":
            self.send_response(303)
            self.send_header("Set-Cookie", "user_id=; Path=/; Max-Age=0")
            self.send_header("Location", "/")
            self.end_headers()
            return

        if not user_id:
            self.render_login_page()
            return

        if url.path in ["/", "/index.html"]:
            conn, c = get_db_connection()
            c.execute("SELECT id, name, phone, address FROM clients WHERE user_id = %s", (user_id,))
            clients = c.fetchall()
            conn.close()
            
            html = "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{font-family:-apple-system;background:#F5F5F7;padding:20px;} .card{background:white;padding:15px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:12px;} .btn{background:#0071E3;color:white;padding:10px;border-radius:8px;display:block;text-align:center;text-decoration:none;font-weight:bold;margin-top:10px;} .btn-dark{background:#212529;} .btn-del{color:#E30613;text-decoration:none;float:right;} .logout{text-align:center;margin-top:20px;display:block;color:#86868B;text-decoration:none;font-size:14px;}</style></head><body><div style='max-width:360px;margin:0 auto;'><h2>Мастер-Учёт 🛠️</h2><form action='/add_client' style='background:white;padding:15px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:20px;'><h3>Добавить объект</h3><input type='text' name='name' placeholder='ФИО' style='width:100%;padding:8px;margin:5px 0;' required><br><input type='text' name='phone' placeholder='Телефон' style='width:100%;padding:8px;margin:5px 0;'><br><textarea name='address' placeholder='Адрес' style='width:100%;padding:8px;margin:5px 0;'></textarea><br><button type='submit' style='width:100%;background:#0071E3;color:white;padding:10px;border:none;border-radius:8px;font-weight:bold;'>Добавить объект</button></form><h3>Активные объекты</h3>"
            for row in clients:
                html += f"<div class='card'><a href='/delete_client?id={row['id']}' class='btn-del' onclick='return confirm(\"Удалить объект?\")'>❌</a><b>👤 {row['name']}</b><p>📞 {row['phone']}<br>📍 {row['address']}</p><a href='/estimate?client_id={row['id']}' class='btn btn-dark'>Открыть смету</a></div>"
            html += "<a href='/logout' class='logout'>Выйти из аккаунта</a></div></body></html>"
            
            self.send_response(200); self.send_header("Content-type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(html.encode("utf-8"))
            
        elif url.path == "/add_client":
            name = q.get("name", [""]).strip()
            phone = q.get("phone", [""]).strip()
            address = q.get("address", [""]).strip()
            if name:
                conn, c = get_db_connection()
                c.execute("INSERT INTO clients (user_id, name, phone, address) VALUES (%s, %s, %s, %s)", (user_id, name, phone, address))
                conn.commit()
                conn.close()
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()

        elif url.path == "/delete_client":
            cid = q.get("id", [""])
            if cid:
                conn, c = get_db_connection()
                c.execute("DELETE FROM clients WHERE id = %s AND user_id = %s", (int(cid), user_id))
                conn.commit()
                conn.close()
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()

        elif url.path == "/estimate":
            try:
                cid = q.get("client_id", [""])
                if not cid: raise ValueError
                cid = int(cid)
            except:
                self.send_response(303); self.send_header("Location", "/"); self.end_headers(); return

            conn, c = get_db_connection()
            c.execute("SELECT id, name, address FROM clients WHERE id = %s AND user_id = %s", (cid, user_id))
            client = c.fetchone()
            if not client:
                conn.close()
                self.send_response(303); self.send_header("Location", "/"); self.end_headers(); return

            c.execute("SELECT id FROM orders WHERE client_id = %s", (cid,))
            order = c.fetchone()
            if not order:
                c.execute("INSERT INTO orders (client_id, status) VALUES (%s, 'Новый') RETURNING id", (cid,))
                conn.commit()
