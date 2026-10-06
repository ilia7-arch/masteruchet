import http.server, socketserver, sqlite3, urllib.parse
PORT = 8550

# Инициализируем базу строго 1 раз при старте программы, чтобы диск не тупил
def init_db():
    conn = sqlite3.connect("master.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, description TEXT, status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS materials (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, name TEXT, quantity REAL, price REAL)")
    conn.commit(); conn.close()

class MasterUchetHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(url.query)
        if url.path in ["/", "/index.html"]:
            conn = sqlite3.connect("master.db"); conn.row_factory = sqlite3.Row
            clients = conn.cursor().execute("SELECT id, name, phone, address FROM clients").fetchall(); conn.close()
            html = "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{font-family:-apple-system;background:#F5F5F7;padding:20px;} .card{background:white;padding:15px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:12px;} .btn{background:#0071E3;color:white;padding:10px;border-radius:8px;display:block;text-align:center;text-decoration:none;font-weight:bold;margin-top:10px;} .btn-dark{background:#212529;} .btn-del{color:#E30613;text-decoration:none;float:right;}</style></head><body><div style='max-width:360px;margin:0 auto;'><h2>Мастер-Учёт 🛠️</h2><form action='/add_client' style='background:white;padding:15px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:20px;'><h3>Добавить объект</h3><input type='text' name='name' placeholder='ФИО' style='width:100%;padding:8px;margin:5px 0;' required><br><input type='text' name='phone' placeholder='Телефон' style='width:100%;padding:8px;margin:5px 0;'><br><textarea name='address' placeholder='Адрес' style='width:100%;padding:8px;margin:5px 0;'></textarea><br><button type='submit' style='width:100%;background:#0071E3;color:white;padding:10px;border:none;border-radius:8px;font-weight:bold;'>Добавить объект</button></form><h3>Активные объекты</h3>"
            for c in clients:
                html += f"<div class='card'><a href='/delete_client?id={c['id']}' class='btn-del' onclick='return confirm(\"Удалить?\")'>❌</a><b>👤 {c['name']}</b><p>📞 {c['phone']}<br>📍 {c['address']}</p><a href='/estimate?client_id={c['id']}' class='btn btn-dark'>Открыть смету</a></div>"
            html += "</div></body></html>"
            self.send_response(200); self.send_header("Content-type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(html.encode("utf-8"))
            
        elif url.path == "/estimate":
            cid = q.get("client_id")[0]; conn = sqlite3.connect("master.db"); conn.row_factory = sqlite3.Row
            c = conn.cursor().execute("SELECT id, name, address FROM clients WHERE id = ?", (cid,)).fetchone()
            o = conn.cursor().execute("SELECT id, status FROM orders WHERE client_id = ?", (cid,)).fetchone()
            if not o:
                conn.cursor().execute("INSERT INTO orders (client_id, description, status) VALUES (?, 'Заказ', 'Новая')", (cid,))
                conn.commit(); o = conn.cursor().execute("SELECT id, status FROM orders WHERE client_id = ?", (cid,)).fetchone()
            mats = conn.cursor().execute("SELECT id, name, quantity, price FROM materials WHERE order_id = ?", (o['id'],)).fetchall(); conn.close()
            tot = sum(m['quantity']*m['price'] for m in mats)
            m_html = "".join([f"<div style='background:#F5F5F7;padding:10px;border-radius:8px;margin-bottom:6px;display:flex;justify-content:space-between;'><div><b>{m['name']}</b><br><small>{m['quantity']} × {m['price']} р.</small></div><b>{m['quantity']*m['price']:.2f} р. <a href='/delete_material?id={m['id']}&client_id={cid}'>❌</a></b></div>" for m in mats])
            sts = ["Новая", "В работе", "Готово", "Оплачено"]
            opts = "".join([f"<option value='{s}' {'selected' if o['status']==s else ''}>{s}</option>" for s in sts])
            msg = f"🛠 MasterUchet Pro | Отчет\n📍 Объект: {c['address']}\n👤 Заказчик: {c['name']}\n📊 Статус: {o['status']}\n💰 Смета: {tot:,.2f} руб.\nПожалуйста, проверьте смету."
            wa = f"https://wa.me{urllib.parse.quote(msg)}"
            html = f"<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{{font-family:-apple-system;background:#F5F5F7;padding:20px;}} .container{{max-width:360px;margin:0 auto;background:white;padding:20px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);}} .btn{{background:#212529;color:white;padding:10px;border-radius:8px;display:block;text-align:center;text-decoration:none;font-weight:bold;margin-top:10px;}} .btn-steel{{background:#EAEAEF;color:black;}} .btn-wa{{background:#25D366;color:white;}}</style></head><body><div class='container'><h2>Смета: {c['name']}</h2><p>📍 {c['address']}</p><a href='/' class='btn btn-steel'>⬅ Назад</a><hr><form action='/update_status'><input type='hidden' name='client_id' value='{cid}'><input type='hidden' name='order_id' value='{o['id']}'><label><b>Статус:</b></label><select name='status' onchange='this.form.submit()' style='width:100%;padding:8px;margin-top:5px;'>{opts}</select></form><hr><form action='/add_material'><input type='hidden' name='client_id' value='{cid}'><input type='hidden' name='order_id' value='{o['id']}'><input type='text' name='mat_name' placeholder='Название' style='width:100%;padding:8px;margin:5px 0;' required><br><input type='text' name='qty' placeholder='Кол-во' value='1' style='width:48%;padding:8px;' required><input type='text' name='price' placeholder='Цена' style='width:48%;padding:8px;float:right;' required><br><button type='submit' class='btn' style='width:100%;'>Добавить в смету</button></form><hr><h3>Позиции</h3>{m_html}<div style='display:flex;justify-content:space-between;font-weight:bold;font-size:18px;margin:15px 0;color:#2E7D32;'><span>Итого:</span><span>{tot:,.2f} руб.</span></div><a href='{wa}' target='_blank' class='btn btn-wa'>💬 Открыть WhatsApp</a></div></body></html>"
            self.send_response(200); self.send_header("Content-type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(html.encode("utf-8"))
            
        elif url.path == "/add_client":
            name = q.get("name")[0]; phone = q.get("phone", [""])[0]; address = q.get("address", [""])[0]
            conn = sqlite3.connect("master.db"); conn.cursor().execute("INSERT INTO clients (name, phone, address) VALUES (?, ?, ?)", (name, phone, address)); conn.commit(); conn.close()
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()
            
        elif url.path == "/delete_client":
            cid = q.get("id")[0]
            conn = sqlite3.connect("master.db"); conn.cursor().execute("DELETE FROM clients WHERE id = ?", (cid,)); conn.cursor().execute("DELETE FROM orders WHERE client_id = ?", (cid,)); conn.commit(); conn.close()
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()
            
        elif url.path == "/add_material":
            client_id = q.get("client_id")[0]; order_id = q.get("order_id")[0]; mat_name = q.get("mat_name")[0]
            qty = float(q.get("qty")[0].replace(",", ".")); price = float(q.get("price")[0].replace(",", "."))
            conn = sqlite3.connect("master.db"); conn.cursor().execute("INSERT INTO materials (order_id, name, quantity, price) VALUES (?, ?, ?, ?)", (order_id, mat_name, qty, price)); conn.commit(); conn.close()
            self.send_response(303); self.send_header("Location", f"/estimate?client_id={client_id}"); self.end_headers()
            
        elif url.path == "/delete_material":
            mid = q.get("id")[0]; client_id = q.get("client_id")[0]
            conn = sqlite3.connect("master.db"); conn.cursor().execute("DELETE FROM materials WHERE id = ?", (mid,)); conn.commit(); conn.close()
            self.send_response(303); self.send_header("Location", f"/estimate?client_id={client_id}"); self.end_headers()
            
        elif url.path == "/update_status":
            client_id = q.get("client_id")[0]; order_id = q.get("order_id")[0]; status = q.get("status")[0]
            conn = sqlite3.connect("master.db"); conn.cursor().execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id)); conn.commit(); conn.close()
            self.send_response(303); self.send_header("Location", f"/estimate?client_id={client_id}"); self.end_headers()

socketserver.TCPServer.allow_reuse_address = True
init_db() # Запускаем базу 1 раз
with socketserver.TCPServer(("0.0.0.0", PORT), MasterUchetHandler) as httpd:
    print(f"🚀 СЕРВЕР MasterUchet Pro УСПЕШНО ЗАПУЩЕН НА ПОРТУ {PORT}"); httpd.serve_forever()
