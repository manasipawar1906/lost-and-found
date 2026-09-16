from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

app = Flask(__name__)
app.secret_key = "change_this_to_any_random_string"

# ---------- DATABASE CONNECTION ----------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Manasi@2024",  
        database="lost_and_found"
    )

# ---------- HOME PAGE: shows all items ----------
# ---------- HOME PAGE + SEARCH + FILTERS (all in one) ----------
@app.route('/')
def index():
    query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    category_filter = request.args.get('category', '')
    location_filter = request.args.get('location', '')
    sort = request.args.get('sort', 'newest')

    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT items.*, users.username 
        FROM items 
        JOIN users ON items.user_id = users.id 
        WHERE 1=1
    """
    params = []

    if query:
        sql += " AND (item_name LIKE %s OR description LIKE %s OR location LIKE %s)"
        like = f"%{query}%"
        params += [like, like, like]

    if status_filter:
        sql += " AND items.status = %s"
        params.append(status_filter)

    if category_filter:
        sql += " AND items.category = %s"
        params.append(category_filter)

    if location_filter:
        sql += " AND items.location = %s"
        params.append(location_filter)

    sql += " ORDER BY items.created_at " + ("ASC" if sort == "oldest" else "DESC")

    cursor.execute(sql, params)
    items = cursor.fetchall()

    # For filter dropdowns — get distinct categories and locations that actually exist
    cursor.execute("SELECT DISTINCT category FROM items WHERE category IS NOT NULL AND category != ''")
    categories = [row['category'] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT location FROM items WHERE location IS NOT NULL AND location != ''")
    locations = [row['location'] for row in cursor.fetchall()]

    cursor.close()
    db.close()

    return render_template(
        'index.html',
        items=items,
        search_query=query,
        categories=categories,
        locations=locations,
        selected_status=status_filter,
        selected_category=category_filter,
        selected_location=location_filter,
        selected_sort=sort
    )

# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, password)
            )
            db.commit()
            flash("Account created! Please log in.")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Error: {err}")
        finally:
            cursor.close()
            db.close()
    return render_template('register.html')

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Logged in successfully!")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.")
    return render_template('login.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for('index'))

# ---------- REPORT AN ITEM (lost or found) ----------
@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user_id' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        item_name = request.form['item_name']
        description = request.form['description']
        category = request.form['category']
        location = request.form['location']
        status = request.form['status']  # 'lost' or 'found'

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO items (user_id, item_name, description, category, location, status, date_reported) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (session['user_id'], item_name, description, category, location, status, date.today())
        )
        db.commit()
        cursor.close()
        db.close()
        flash("Item reported successfully!")
        return redirect(url_for('index'))

    return render_template('report.html')

# ---------- ITEM DETAIL PAGE ----------
@app.route('/item/<int:item_id>')
def item_detail(item_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT items.*, users.username, users.email FROM items JOIN users ON items.user_id = users.id WHERE items.id = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    db.close()
    return render_template('item_detail.html', item=item)

# ---------- MARK AS CLAIMED ----------
@app.route('/claim/<int:item_id>')
def claim(item_id):
    if 'user_id' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE items SET status = 'claimed' WHERE id = %s", (item_id,))
    db.commit()
    cursor.close()
    db.close()
    flash("Item marked as claimed.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)