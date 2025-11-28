from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import difflib
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'dev'

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect('jengamart.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to be logged in to view this page.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_cart_count():
    cart = session.get('cart', {})
    return dict(cart_count=len(cart))

@app.route('/')
def home():
    conn = get_db_connection()
    featured_products = conn.execute('SELECT * FROM products WHERE featured = 1').fetchall()
    conn.close()
    return render_template('index.html', featured_products=featured_products)

import difflib

@app.route('/inventory')
@login_required
def inventory():
    search_query = request.args.get('search', '')
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()

    if search_query:
        products = conn.execute("SELECT p.id, p.name, p.price, p.image_file, c.name as category_name FROM products p JOIN categories c ON p.category_id = c.id WHERE p.name LIKE ?", (f'%{search_query}%',)).fetchall()
        if not products:
            # Get all product names
            all_product_names = [p['name'] for p in conn.execute('SELECT name FROM products').fetchall()]
            # Find close matches
            matches = difflib.get_close_matches(search_query, all_product_names, n=1, cutoff=0.6)
            if matches:
                suggestion = matches[0]
                flash(f"Did you mean: <a href='{url_for('inventory', search=suggestion)}'>{suggestion}</a>?", 'info')

    else:
        products = conn.execute('SELECT p.id, p.name, p.price, p.image_file, c.name as category_name FROM products p JOIN categories c ON p.category_id = c.id').fetchall()
    
    conn.close()

    products_by_category = {}
    for category in categories:
        products_by_category[category['name']] = []
    
    for product in products:
        # If searching, we might not have all categories, so check first.
        if product['category_name'] in products_by_category:
            products_by_category[product['category_name']].append(product)
        else: # if a product from a search doesn't fit in the categories, create a new one
            products_by_category[product['category_name']] = [product]


    return render_template('inventory.html', categories=categories, products_by_category=products_by_category, search_query=search_query)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    cart = session.get('cart', {})
    # For simplicity, we add one item at a time. A real implementation would handle quantity.
    cart[str(product_id)] = 1
    session['cart'] = cart
    flash('Product added to cart!', 'success')
    return redirect(url_for('inventory'))

@app.route('/remove_from_cart/<int:product_id>')
@login_required
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if str(product_id) in cart:
        cart.pop(str(product_id))
        session['cart'] = cart
        flash('Product removed from cart.', 'info')
    return redirect(url_for('cart'))

@app.route('/cart')
@login_required
def cart():
    cart = session.get('cart', {})
    if not cart:
        return render_template('cart.html', cart_items=[], total_price=0)

    conn = get_db_connection()
    # Create a string of placeholders for the query
    placeholders = ','.join('?' for _ in cart.keys())
    product_ids = list(cart.keys())
    
    cart_products = conn.execute(f'SELECT * FROM products WHERE id IN ({placeholders})', product_ids).fetchall()
    conn.close()

    cart_items = []
    total_price = 0
    for product in cart_products:
        # This is a simplification. Prices like "450-520 KSh" can't be summed directly.
        # We'll take the first number for calculation.
        try:
            price_str = product['price'].split(' ')[0].split('-')[0].replace(',', '')
            price = float(price_str)
            cart_items.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'image_file': product['image_file'],
                'numeric_price': price
            })
            total_price += price
        except (ValueError, IndexError):
            # Handle cases where price is not a simple number
            cart_items.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'image_file': product['image_file'],
                'numeric_price': 0 # Or handle as a special case
            })


    return render_template('cart.html', cart_items=cart_items, total_price=total_price)



@app.route('/checkout')
@login_required
def checkout():
    return render_template('checkout.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/policies')
def policies():
    return render_template('policies.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/product/<int:product_id>')
def product(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if product is None:
        flash('Product not found.', 'danger')
        return redirect(url_for('inventory'))

    related_products = conn.execute('SELECT * FROM products WHERE category_id = ? AND id != ? LIMIT 4', 
                                    (product['category_id'], product_id)).fetchall()
    conn.close()
    
    return render_template('product.html', product=product, related_products=related_products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        conn = get_db_connection()
        user_by_username = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        user_by_email = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user_by_username:
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        if user_by_email:
            flash('Email address already registered.', 'danger')
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)

        conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                     (username, email, password_hash))
        conn.commit()
        conn.close()

        flash('You have successfully registered! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)