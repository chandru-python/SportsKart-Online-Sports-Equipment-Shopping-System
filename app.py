from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
import hashlib
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'sportskart_secret_key_2024'
app.jinja_env.globals.update(enumerate=enumerate)

UPLOAD_FOLDER = os.path.join('static', 'images', 'products')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

DB_PATH = 'sportskart.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            role TEXT DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            icon TEXT DEFAULT 'trophy',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            category_id INTEGER,
            image TEXT DEFAULT 'default.jpg',
            brand TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            payment_method TEXT DEFAULT 'cod',
            shipping_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    ''')

    # Seed admin
    admin_pass = hash_password('admin123')
    c.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
              ('Admin', 'admin@sportskart.com', admin_pass, 'admin'))

    # Seed categories
    categories = [
        ('Cricket', 'Bats, balls, pads, gloves and more', 'cricket'),
        ('Football', 'Boots, balls, jerseys and accessories', 'futbol'),
        ('Basketball', 'Balls, shoes, hoops and gear', 'basketball'),
        ('Tennis', 'Rackets, balls, strings and apparel', 'tennis'),
        ('Badminton', 'Rackets, shuttles and court gear', 'badminton'),
        ('Swimming', 'Swimwear, goggles, caps and training aids', 'water'),
        ('Fitness', 'Weights, machines, yoga and supplements', 'dumbbell'),
        ('Cycling', 'Bikes, helmets, accessories and apparel', 'bicycle'),
    ]
    c.executemany("INSERT OR IGNORE INTO categories (name, description, icon) VALUES (?, ?, ?)", categories)

    # Seed products
    products = [
        ('SG Scorer Bat', 'Premium English willow cricket bat', 3499, 25, 1, 'default.jpg', 'SG'),
        ('Kookaburra Ball', 'Match quality red leather ball', 599, 50, 1, 'default.jpg', 'Kookaburra'),
        ('Nike Mercurial Boots', 'Lightweight football boots for speed', 5999, 15, 2, 'default.jpg', 'Nike'),
        ('Adidas Football', 'FIFA approved match ball', 1299, 30, 2, 'default.jpg', 'Adidas'),
        ('Spalding NBA Ball', 'Official size basketball', 2499, 20, 3, 'default.jpg', 'Spalding'),
        ('Wilson Tennis Racket', 'Carbon frame for power and control', 4299, 18, 4, 'default.jpg', 'Wilson'),
        ('Yonex Badminton Racket', 'Graphite shaft for precision play', 3199, 22, 5, 'default.jpg', 'Yonex'),
        ('Speedo Goggles', 'Anti-fog UV protected swim goggles', 899, 40, 6, 'default.jpg', 'Speedo'),
        ('Decathlon Dumbbells', '5kg pair rubber coated dumbbells', 1499, 35, 7, 'default.jpg', 'Decathlon'),
        ('Trek Helmet', 'Aerodynamic cycling helmet with ventilation', 2799, 12, 8, 'default.jpg', 'Trek'),
    ]
    c.executemany("INSERT OR IGNORE INTO products (name, description, price, stock, category_id, image, brand) VALUES (?, ?, ?, ?, ?, ?, ?)", products)

    conn.commit()
    conn.close()

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            session['email'] = user['email']
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        password = hash_password(request.form['password'])
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (name, email, password, phone, address) VALUES (?, ?, ?, ?, ?)",
                         (name, email, password, phone, address))
            conn.commit()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered.', 'danger')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── CUSTOMER ────────────────────────────────────────────────────────────────

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    q = request.args.get('q', '')
    cat = request.args.get('cat', '')
    query = "SELECT p.*, c.name as cat_name FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE 1=1"
    params = []
    if q:
        query += " AND (p.name LIKE ? OR p.brand LIKE ? OR p.description LIKE ?)"
        params += [f'%{q}%', f'%{q}%', f'%{q}%']
    if cat:
        query += " AND p.category_id=?"
        params.append(cat)
    products = conn.execute(query, params).fetchall()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    cart_count = conn.execute("SELECT SUM(quantity) FROM cart WHERE user_id=?", (session['user_id'],)).fetchone()[0] or 0
    conn.close()
    return render_template('home.html', products=products, categories=categories, cart_count=cart_count, q=q, cat=cat)

@app.route('/product/<int:pid>')
def product_detail(pid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    product = conn.execute("SELECT p.*, c.name as cat_name FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.id=?", (pid,)).fetchone()
    related = conn.execute("SELECT * FROM products WHERE category_id=? AND id!=? LIMIT 4", (product['category_id'], pid)).fetchall()
    cart_count = conn.execute("SELECT SUM(quantity) FROM cart WHERE user_id=?", (session['user_id'],)).fetchone()[0] or 0
    conn.close()
    return render_template('product_detail.html', product=product, related=related, cart_count=cart_count)

# ─── CART ─────────────────────────────────────────────────────────────────────

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    items = conn.execute("""
        SELECT c.id, c.quantity, p.name, p.price, p.image, p.id as pid, p.stock
        FROM cart c JOIN products p ON c.product_id=p.id
        WHERE c.user_id=?
    """, (session['user_id'],)).fetchall()
    total = sum(i['price'] * i['quantity'] for i in items)
    cart_count = conn.execute("SELECT SUM(quantity) FROM cart WHERE user_id=?", (session['user_id'],)).fetchone()[0] or 0
    conn.close()
    return render_template('cart.html', items=items, total=total, cart_count=cart_count)

@app.route('/cart/add/<int:pid>', methods=['POST'])
def add_to_cart(pid):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Login required'})
    qty = int(request.form.get('quantity', 1))
    conn = get_db()
    existing = conn.execute("SELECT * FROM cart WHERE user_id=? AND product_id=?", (session['user_id'], pid)).fetchone()
    if existing:
        conn.execute("UPDATE cart SET quantity=quantity+? WHERE user_id=? AND product_id=?", (qty, session['user_id'], pid))
    else:
        conn.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (session['user_id'], pid, qty))
    conn.commit()
    cart_count = conn.execute("SELECT SUM(quantity) FROM cart WHERE user_id=?", (session['user_id'],)).fetchone()[0] or 0
    conn.close()
    return jsonify({'success': True, 'cart_count': int(cart_count)})

@app.route('/cart/update/<int:cart_id>', methods=['POST'])
def update_cart(cart_id):
    qty = int(request.form.get('quantity', 1))
    conn = get_db()
    if qty <= 0:
        conn.execute("DELETE FROM cart WHERE id=?", (cart_id,))
    else:
        conn.execute("UPDATE cart SET quantity=? WHERE id=?", (qty, cart_id))
    conn.commit()
    conn.close()
    return redirect(url_for('cart'))

@app.route('/cart/remove/<int:cart_id>')
def remove_from_cart(cart_id):
    conn = get_db()
    conn.execute("DELETE FROM cart WHERE id=?", (cart_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('cart'))

# ─── ORDERS ───────────────────────────────────────────────────────────────────

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    items = conn.execute("""
        SELECT c.id, c.quantity, p.name, p.price, p.image, p.id as pid
        FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=?
    """, (session['user_id'],)).fetchall()
    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart'))
    total = sum(i['price'] * i['quantity'] for i in items)
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    cart_count = conn.execute("SELECT SUM(quantity) FROM cart WHERE user_id=?", (session['user_id'],)).fetchone()[0] or 0

    if request.method == 'POST':
        address = request.form['address']
        payment = request.form['payment']
        order_id_row = conn.execute(
            "INSERT INTO orders (user_id, total_amount, status, payment_method, shipping_address) VALUES (?, ?, 'confirmed', ?, ?)",
            (session['user_id'], total, payment, address)
        )
        order_id = order_id_row.lastrowid
        for item in items:
            conn.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                         (order_id, item['pid'], item['quantity'], item['price']))
            conn.execute("UPDATE products SET stock=stock-? WHERE id=?", (item['quantity'], item['pid']))
        conn.execute("DELETE FROM cart WHERE user_id=?", (session['user_id'],))
        conn.commit()
        conn.close()
        return redirect(url_for('order_success', order_id=order_id))
    conn.close()
    return render_template('checkout.html', items=items, total=total, user=user, cart_count=cart_count)

@app.route('/order/success/<int:order_id>')
def order_success(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (order_id, session['user_id'])).fetchone()
    items = conn.execute("""
        SELECT oi.*, p.name, p.image FROM order_items oi
        JOIN products p ON oi.product_id=p.id WHERE oi.order_id=?
    """, (order_id,)).fetchall()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    cart_count = 0
    conn.close()
    return render_template('order_success.html', order=order, items=items, user=user, cart_count=cart_count)

@app.route('/my-orders')
def my_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (session['user_id'],)).fetchall()
    cart_count = conn.execute("SELECT SUM(quantity) FROM cart WHERE user_id=?", (session['user_id'],)).fetchone()[0] or 0
    conn.close()
    return render_template('my_orders.html', orders=orders, cart_count=cart_count)

@app.route('/order/<int:order_id>/bill')
def view_bill(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    items = conn.execute("""
        SELECT oi.*, p.name, p.image FROM order_items oi
        JOIN products p ON oi.product_id=p.id WHERE oi.order_id=?
    """, (order_id,)).fetchall()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('bill.html', order=order, items=items, user=user)

# ─── ADMIN ────────────────────────────────────────────────────────────────────

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db()
    total_sales = conn.execute("SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE status='confirmed'").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_customers = conn.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0]
    recent_orders = conn.execute("""
        SELECT o.*, u.name as customer FROM orders o JOIN users u ON o.user_id=u.id
        ORDER BY o.created_at DESC LIMIT 8
    """).fetchall()
    top_products = conn.execute("""
        SELECT p.name, SUM(oi.quantity) as sold FROM order_items oi
        JOIN products p ON oi.product_id=p.id GROUP BY oi.product_id ORDER BY sold DESC LIMIT 5
    """).fetchall()
    monthly_data = conn.execute("""
        SELECT strftime('%m', created_at) as month, SUM(total_amount) as revenue
        FROM orders WHERE status='confirmed' AND strftime('%Y', created_at)=strftime('%Y','now')
        GROUP BY month ORDER BY month
    """).fetchall()
    conn.close()
    return render_template('admin/dashboard.html',
        total_sales=total_sales, total_orders=total_orders,
        total_products=total_products, total_customers=total_customers,
        recent_orders=recent_orders, top_products=top_products, monthly_data=monthly_data)

@app.route('/admin/products')
@admin_required
def admin_products():
    conn = get_db()
    q = request.args.get('q', '')
    if q:
        products = conn.execute("""
            SELECT p.*, c.name as cat_name FROM products p LEFT JOIN categories c ON p.category_id=c.id
            WHERE p.name LIKE ? OR p.brand LIKE ?
        """, (f'%{q}%', f'%{q}%')).fetchall()
    else:
        products = conn.execute("SELECT p.*, c.name as cat_name FROM products p LEFT JOIN categories c ON p.category_id=c.id").fetchall()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    return render_template('admin/products.html', products=products, categories=categories, q=q)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    conn = get_db()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    if request.method == 'POST':
        name = request.form['name']
        desc = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        cat_id = request.form['category_id']
        brand = request.form['brand']
        image = 'default.jpg'
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                ts = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{ts}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename
        conn.execute("INSERT INTO products (name, description, price, stock, category_id, image, brand) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (name, desc, price, stock, cat_id, image, brand))
        conn.commit()
        conn.close()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))
    conn.close()
    return render_template('admin/add_product.html', categories=categories)

@app.route('/admin/products/edit/<int:pid>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(pid):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    if request.method == 'POST':
        name = request.form['name']
        desc = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        cat_id = request.form['category_id']
        brand = request.form['brand']
        image = product['image']
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                ts = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{ts}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename
        conn.execute("UPDATE products SET name=?, description=?, price=?, stock=?, category_id=?, image=?, brand=? WHERE id=?",
                     (name, desc, price, stock, cat_id, image, brand, pid))
        conn.commit()
        conn.close()
        flash('Product updated!', 'success')
        return redirect(url_for('admin_products'))
    conn.close()
    return render_template('admin/edit_product.html', product=product, categories=categories)

@app.route('/admin/products/delete/<int:pid>')
@admin_required
def admin_delete_product(pid):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    flash('Product deleted.', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/categories')
@admin_required
def admin_categories():
    conn = get_db()
    categories = conn.execute("SELECT c.*, COUNT(p.id) as product_count FROM categories c LEFT JOIN products p ON c.id=p.category_id GROUP BY c.id").fetchall()
    conn.close()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['POST'])
@admin_required
def admin_add_category():
    name = request.form['name']
    desc = request.form['description']
    icon = request.form.get('icon', 'trophy')
    conn = get_db()
    try:
        conn.execute("INSERT INTO categories (name, description, icon) VALUES (?, ?, ?)", (name, desc, icon))
        conn.commit()
        flash('Category added!', 'success')
    except:
        flash('Category already exists.', 'danger')
    conn.close()
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/delete/<int:cid>')
@admin_required
def admin_delete_category(cid):
    conn = get_db()
    conn.execute("DELETE FROM categories WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    flash('Category deleted.', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    conn = get_db()
    orders = conn.execute("""
        SELECT o.*, u.name as customer, u.email FROM orders o
        JOIN users u ON o.user_id=u.id ORDER BY o.created_at DESC
    """).fetchall()
    conn.close()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/update/<int:oid>', methods=['POST'])
@admin_required
def admin_update_order(oid):
    status = request.form['status']
    conn = get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))
    conn.commit()
    conn.close()
    flash('Order status updated!', 'success')
    return redirect(url_for('admin_orders'))

@app.route('/admin/customers')
@admin_required
def admin_customers():
    conn = get_db()
    customers = conn.execute("""
        SELECT u.*, COUNT(o.id) as order_count, COALESCE(SUM(o.total_amount),0) as total_spent
        FROM users u LEFT JOIN orders o ON u.id=o.user_id WHERE u.role='customer' GROUP BY u.id
    """).fetchall()
    conn.close()
    return render_template('admin/customers.html', customers=customers)

@app.route('/admin/order/<int:oid>/bill')
@admin_required
def admin_view_bill(oid):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    items = conn.execute("""
        SELECT oi.*, p.name FROM order_items oi
        JOIN products p ON oi.product_id=p.id WHERE oi.order_id=?
    """, (oid,)).fetchall()
    user = conn.execute("SELECT * FROM users WHERE id=?", (order['user_id'],)).fetchone()
    conn.close()
    return render_template('bill.html', order=order, items=items, user=user)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
