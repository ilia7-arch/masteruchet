import os
import sqlite3
import urllib.parse
from flask import Flask, request, redirect, render_template_string

app = Flask(__name__)
DB_NAME = "master.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, description TEXT, status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS materials (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, name TEXT, quantity REAL, price REAL)")
    # Добавляем индекс для мгновенной загрузки в облаке
    c.execute("CREATE INDEX IF NOT EXISTS idx_materials_order ON materials(order_id);")
    conn.commit()
    conn.close()

# Запуск инициализации базы строго один раз при старте
init_db()

@app.route("/")
@app.route("/index.html")
def index():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    clients = conn.cursor().execute("SELECT id, name, phone, address FROM clients").fetchall()
    conn.close()
    
    html = """<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><style>
    body{font-family:-apple-system;background:#F5F5F7;padding:20px;} 
    .card{background:white;padding:15px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:12px;} 
    .btn{background:#0071E3;color:white;padding:10px;border-radius:8px;display:block;text-align:center;text-decoration:none;font-weight:bold;margin-top:10px;} 
    .btn-dark{background:#212529;} 
    .btn-del{color:#E30613;text-decoration:none;float:right;}
    </style></head><body><div style='max-width:360px;margin:0 auto;'><h2>Мастер-Учёт 🛠️</h2>
    <form action='/add_client' style='background:white;padding:15px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:20px;'>
    <h3>Добавить объект</h3>
    <input type='text' name='name' placeholder='ФИО' style='width:100%;padding:8px;margin:5px 0;' required><br>
    <input type='text' name='phone' placeholder='Телефон' style='width:100%;padding:8px;margin:5px 0;'><br>
    <textarea name='address' placeholder='Адрес' style='width:100%;padding:8px;margin:5px 0;'></textarea><br>
    <button type='submit' style='width:100%;background:#0071E3;color:white;padding:10px;border:none;border-radius:8px;font-weight:bold;'>Добавить объект</button>
    </form><h3>Активные объекты</h3>"""
    
    for c in clients:
        html += f"<div class='card'><a href='/delete_client?id={c['id']}' class='btn-del' onclick='return confirm(\"Удалить?\")'>❌</a><b>👤 {c['name']}</b><p>📞 {c['phone']}<br>📍 {c['address']}</p><a href='/estimate?client_id={c['id']}' class='btn btn-dark'>Открыть смету</a></div>"
    html += "</div></body></html>"
    return html

@app.route("/estimate")
def estimate():
    cid = request.args.get("client_id")
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor().execute("SELECT id, name, address FROM clients WHERE id = ?", (cid,)).fetchone()
    o = conn.cursor().execute("SELECT id, status FROM orders WHERE client_id = ?", (cid,)).fetchone()
    if not o:
        conn.cursor().execute("INSERT INTO orders (client_id, description, status) VALUES (?, 'Заказ', 'Новая')", (cid,))
        conn.commit()
        o = conn.cursor().execute("SELECT id, status FROM orders WHERE client_id = ?", (cid,)).fetchone()
    mats = conn.cursor().execute("SELECT id, name, quantity, price FROM materials WHERE order_id = ?", (o['id'],)).fetchall()
    conn.close()
    
    tot = sum(m['quantity']*m['price'] for m in mats)
    m_html = "".join([f"<div style='background:#F5F5F7;padding:10px;border-radius:8px;margin-bottom:6px;display:flex;justify-content:space-between;'><div><b>{m['name']}</b><br><small>{m['quantity']} × {m['price']} р.</small></div><b>{m['quantity']*m['price']:.2f} р. <a href='/delete_material?id={m['id']}&client_id={cid}'>❌</a></b></div>" for m in mats])
    sts = ["Новая", "В работе", "Готово", "Оплачено"]
    opts = "".join([f"<option value='{s}' {'selected' if o['status']==s else ''}>{s}</option>" for s in sts])
    
    msg = f"🛠 MasterUchet Pro | Отчет\n📍 Объект: {c['address']}\n👤 Заказчик: {c['name']}\n📊 Статус: {o['status']}\n💰 Смета: {tot:,.2f} руб.\nПожалуйста, проверьте смету."
    wa = f"https://wa.me{urllib.parse.quote(msg)}"
    
    html = f"""<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><style>
    body{{font-family:-apple-system;background:#F5F5F7;padding:20px;}} 
    .container{{max-width:360px;margin:0 auto;background:white;padding:20px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);}} 
    .btn{{background:#212529;color:white;padding:10px;border-radius:8px;display:block;text-align:center;text-decoration:none;font-weight:bold;margin-top:10px;}} 
    .btn-steel{{background:#EAEAEF;color:black;}} 
    .btn-wa{{background:#25D366;color:white;}}
    .status-block{{border: 1px solid #000000; border-radius: 8px; padding: 10px; margin-top: 5px; background: white;}}
    </style></head><body><div class='container'><h2>Смета: {c['name']}</h2><p>📍 {c['address']}</p><a href='/' class='btn btn-steel'>⬅ Назад</a><hr>
    <form action='/update_status'>
    <input type='hidden' name='client_id' value='{cid}'>
    <input type='hidden' name='order_id' value='{o['id']}'>
    <label><b>Статус:</b></label>
    <select name='status' onchange='this.form.submit()' class='status-block' style='width:100%;padding:8px;'>{opts}</select>
    </form><hr>
    <form action='/add_material'>
    <input type='hidden' name='client_id' value='{cid}'>
    <input type='hidden' name='order_id' value='{o['id']}'>
    <input type='text' name='mat_name' placeholder='Название' style='width:100%;padding:8px;margin:5px 0;' required><br>
    <input type='text' name='qty' placeholder='Кол-во' value='1' style='width:48%;padding:8px;' required>
    <input type='text' name='price' placeholder='Цена' style='width:48%;padding:8px;float:right;' required><br>
    <button type='submit' class='btn' style='width:100%;'>Добавить в смету</button>
    </form><hr><h3>Позиции</h3>{m_html}
    <div style='display:flex;justify-content:space-between;font-weight:bold;font-size:18px;margin:15px 0;color:#2E7D32;'><span>Итого:</span><span>{tot:,.2f} руб.</span></div>
    <a href='{wa}' target='_blank' class='btn btn-wa'>💬 Открыть WhatsApp</a></div></body></html>"""
    return html

@app.route("/add_client")
def add_client():
    name = request.args.get("name")
    phone = request.args.get("phone", "")
    address = request.args.get("address", "")
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT INTO clients (name, phone, address) VALUES (?, ?, ?)", (name, phone, address))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete_client")
def delete_client():
    cid = request.args.get("id")
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("DELETE FROM clients WHERE id = ?", (cid,))
    conn.cursor().execute("DELETE FROM orders WHERE client_id = ?", (cid,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/add_material")
def add_material():
    client_id = request.args.get("client_id")
    order_id = request.args.get("order_id")
    mat_name = request.args.get("mat_name")
    qty = float(request.args.get("qty").replace(",", "."))
    price = float(request.args.get("price").replace(",", "."))
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT INTO materials (order_id, name, quantity, price) VALUES (?, ?, ?, ?)", (order_id, mat_name, qty, price))
    conn.commit()
    conn.close()
    return redirect(f"/estimate?client_id={client_id}")

@app.route("/delete_material")
def delete_material():
    mid = request.args.get("id")
    client_id = request.args.get("client_id")
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("DELETE FROM materials WHERE id = ?", (mid,))
    conn.commit()
    conn.close()
    return redirect(f"/estimate?client_id={client_id}")

@app.route("/update_status")
def update_status():
    client_id = request.args.get("client_id")
    order_id = request.args.get("order_id")
    status = request.args.get("status")
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()
    return redirect(f"/estimate?client_id={client_id}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8550)))
