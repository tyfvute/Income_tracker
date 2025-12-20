from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import get_db_connection, init_db
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'admin'
init_db()


def get_balance(cursor, user_id):
    recs = cursor.execute("SELECT amount, type FROM records WHERE user_id = ?", (user_id,)).fetchall()
    return sum(r['amount'] if r['type'] == 'income' else -r['amount'] for r in recs)


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id, conn = session['user_id'], get_db_connection()
    cursor = conn.cursor()
    current_balance = get_balance(cursor, user_id)

    if request.method == 'POST':
        if 'amount' in request.form:
            try:
                amount, r_type, cat = int(round(float(request.form['amount']))), request.form['type'], request.form[
                    'category']
                if amount > 10 ** 15:
                    flash("Сумма слишком большая!", "danger")
                elif r_type == 'expense' and amount > current_balance:
                    flash(f"Недостаточно средств! Баланс: {current_balance} ₽.", "danger")
                else:
                    cursor.execute("INSERT INTO records (user_id, amount, category, type, date) VALUES (?, ?, ?, ?, ?)",
                                   (user_id, amount, cat, r_type, datetime.now().strftime("%d.%m %H:%M")))
                    conn.commit()
            except ValueError:
                flash("Введите корректное число!", "danger")
        if 'target' in request.form:
            try:
                target, desc = int(round(float(request.form['target']))), request.form['goal_text']
                cursor.execute("DELETE FROM goals WHERE user_id = ?", (user_id,))
                cursor.execute("INSERT INTO goals (user_id, target, description) VALUES (?, ?, ?)",
                               (user_id, target, desc))
                conn.commit()
            except ValueError:
                flash("Цель должна быть числом!", "danger")
        return redirect(url_for('index'))

    f_type, f_cat = request.args.get('filter_type', 'all'), request.args.get('filter_cat', 'all')
    query, params = "SELECT * FROM records WHERE user_id = ?", [user_id]
    if f_type != 'all': query += " AND type = ?"; params.append(f_type)
    if f_cat != 'all': query += " AND category = ?"; params.append(f_cat)

    records = cursor.execute(query + " ORDER BY id DESC", tuple(params)).fetchall()
    categories = cursor.execute("SELECT DISTINCT category FROM records WHERE user_id = ?", (user_id,)).fetchall()
    goal = cursor.execute("SELECT * FROM goals WHERE user_id = ?", (user_id,)).fetchone()

    exp_stats, inc_stats = {}, {}
    for r in records:
        target = exp_stats if r['type'] == 'expense' else inc_stats
        target[r['category']] = target.get(r['category'], 0) + r['amount']

    total_exp, total_inc = sum(exp_stats.values()), sum(inc_stats.values())
    conn.close()
    return render_template('index.html', balance=current_balance, records=records, exp_stats=exp_stats,
                           inc_stats=inc_stats,
                           total_exp=total_exp, total_inc=total_inc, goal=goal, categories=categories,
                           filter_type=f_type, filter_cat=f_cat)


@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id, conn = session['user_id'], get_db_connection()
    cursor = conn.cursor()
    rec = cursor.execute("SELECT * FROM records WHERE id = ? AND user_id = ?", (id, user_id)).fetchone()
    if rec:
        bal = get_balance(cursor, user_id)
        if rec['type'] == 'income' and (bal - rec['amount']) < 0:
            flash(f"Нельзя удалить доход! Баланс уйдет в минус ({bal - rec['amount']} ₽).", "danger")
        else:
            cursor.execute("DELETE FROM records WHERE id = ?", (id,))
            conn.commit()
    conn.close()
    return redirect(url_for('index'))


@app.route('/delete_goal')
def delete_goal():
    if 'user_id' in session:
        conn = get_db_connection()
        conn.execute("DELETE FROM goals WHERE user_id = ?", (session['user_id'],))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = get_db_connection().execute("SELECT * FROM users WHERE username = ? AND password = ?",
                                           (request.form['username'], request.form['password'])).fetchone()
        if user:
            session.update({'user_id': user['id'], 'username': user['username']})
            return redirect(url_for('index'))
        flash('Неверный логин или пароль', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                         (request.form['username'], request.form['password']))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Пользователь уже существует', 'danger')
        finally:
            conn.close()
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3500)
