from flask import Flask, render_template, request, jsonify
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR)
DB_NAME = os.path.join(BASE_DIR, "novatap.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabla con soporte para referidos y multiplicadores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 1000,
            referred_by INTEGER DEFAULT NULL,
            referral_count INTEGER DEFAULT 0,
            multiplier INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    # Lee el parámetro de referido si viene en la URL (ej: ?ref=12345)
    referrer_id = request.args.get('ref', type=int)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT points, energy, referral_count, multiplier FROM users WHERE telegram_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if not row:
        # Nuevo usuario
        bonus_points = 0
        referred_by_val = None

        # Si viene con enlace de referido y no se esta auto-invitando
        if referrer_id and referrer_id != user_id:
            cursor.execute('SELECT telegram_id FROM users WHERE telegram_id = ?', (referrer_id,))
            if cursor.fetchone():
                referred_by_val = referrer_id
                bonus_points = 5000 # Bono de bienvenida para el nuevo usuario
                
                # Premiar al usuario que invitó (+5000 puntos y +1 al contador)
                cursor.execute('''
                    UPDATE users 
                    SET points = points + 5000, referral_count = referral_count + 1 
                    WHERE telegram_id = ?
                ''', (referrer_id,))

        cursor.execute('''
            INSERT INTO users (telegram_id, points, energy, referred_by, referral_count, multiplier) 
            VALUES (?, ?, 1000, ?, 0, 1)
        ''', (user_id, bonus_points, referred_by_val))
        conn.commit()
        
        points = bonus_points
        energy = 1000
        referral_count = 0
        multiplier = 1
    else:
        points, energy, referral_count, multiplier = row
        
    conn.close()
    return jsonify({
        "points": points, 
        "energy": energy, 
        "referral_count": referral_count,
        "multiplier": multiplier
    })

@app.route('/api/tap', methods=['POST'])
def tap():
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"error": "ID invalido"}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT points, energy, multiplier FROM users WHERE telegram_id = ?', (user_id,))
    row = cursor.fetchone()

    if row:
        points, energy, multiplier = row
        if energy >= multiplier:
            new_points = points + multiplier
            new_energy = energy - multiplier
            cursor.execute('UPDATE users SET points = ?, energy = ? WHERE telegram_id = ?', 
                           (new_points, new_energy, user_id))
            conn.commit()
            conn.close()
            return jsonify({"points": new_points, "energy": new_energy, "earned": multiplier})
        else:
            conn.close()
            return jsonify({"error": "Sin energia"}), 400
            
    conn.close()
    return jsonify({"error": "Usuario no encontrado"}), 404

if __name__ == '__main__':
    print("Servidor NovaTap con Referidos activo en http://localhost:8080")
    app.run(host='127.0.0.1', port=8080, debug=False)