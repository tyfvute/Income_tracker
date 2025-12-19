from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import get_db_connection, init_db
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'admin'

init_db()

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = session['user_id']

    if request.method == 'POST':
        amount = int(float(request.form['amount']))
        category = request.form['category']
        rec_type = request.form['type']

        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

        if amount and category and rec_type:

            cursor.execute(
                "INSERT INTO records (user_id, amount, category, type, date) VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, rec_type, current_time)
            )
            conn.commit()
            return redirect(url_for('index'))

    cursor.execute("SELECT * FROM records WHERE user_id = ? ORDER BY id DESC", (user_id,))
    records = cursor.fetchall()

    total_balance = 0
    for r in records:
        if r['type'] == 'income':
            total_balance += int(r['amount'])
        else:
            total_balance -= int(r['amount'])

    cursor.execute(
        "SELECT category, SUM(amount) as total FROM records WHERE user_id = ? AND type = 'expense' GROUP BY category",
        (user_id,))
    expense_stats = cursor.fetchall()
    conn.close()

    return render_template('index.html', username=session['username'], records=records, balance=total_balance,
                           stats=expense_stats)

@app.route('/delete/<int:record_id>')
def delete_record(record_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM records WHERE id = ? AND user_id = ?", (record_id, session['user_id']))

    conn.commit()
    conn.close()

    flash('Запись удалена')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash('Регистрация успешна! Теперь войдите.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Такой пользователь уже существует')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=3500)

