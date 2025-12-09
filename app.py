import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf.csrf import CSRFProtect
import difflib
# Import database functions
from JENGAMART.db import get_db, close_db
# Import blueprints
from JENGAMART.blueprints.auth import auth_bp, login_required
from JENGAMART.blueprints.admin import admin_bp, admin_required

app = Flask(__name__)
csrf = CSRFProtect(app)
app.secret_key = os.environ.get('SECRET_KEY', 'a-default-secret-key-for-development')
app.config['DATABASE'] = 'jengamart.db' # Set the database path in app config

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# Register teardown function for database
app.teardown_appcontext(close_db)

@app.context_processor
def inject_cart_count():
    cart = session.get('cart', {})
    return dict(cart_count=len(cart))

@app.route('/')
def home():
    conn = get_db()
    featured_products = conn.execute('SELECT * FROM products WHERE featured = 1').fetchall()
    return render_template('index.html', featured_products=featured_products)

import difflib

@app.route('/inventory')
@login_required
def inventory():
    search_query = request.args.get('search', '')
    category_id = request.args.get('category_id') # Get category_id from URL
    
    conn = get_db()
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()

    query = "SELECT p.id, p.name, p.price, p.image_file, c.name as category_name, c.id as category_id FROM products p JOIN categories c ON p.category_id = c.id WHERE 1=1"
    params = []

    if search_query:
        query += " AND p.name LIKE ?"
        params.append(f'%{search_query}%')
    
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)

    products = conn.execute(query, params).fetchall()

    if search_query and not products: # Only suggest if a search query was made and no products found directly
        # Get all product names for suggestion, potentially within the selected category
        suggestion_query = "SELECT name FROM products p JOIN categories c ON p.category_id = c.id WHERE 1=1"
        suggestion_params = []
        if category_id:
            suggestion_query += " AND p.category_id = ?"
            suggestion_params.append(category_id)
        
        all_product_names = [p['name'] for p in conn.execute(suggestion_query, suggestion_params).fetchall()]
        
        # Find close matches
        matches = difflib.get_close_matches(search_query, all_product_names, n=1, cutoff=0.6)
        if matches:
            suggestion = matches[0]
            # Preserve category_id in suggestion link
            flash_message = f"Did you mean: <a href='{url_for('inventory', search=suggestion, category_id=category_id if category_id else '')}'>{suggestion}</a>?"
            flash(flash_message, 'info')

    ()

    products_by_category = {}
    for category in categories:
        products_by_category[category['name']] = []
    
    for product in products:
        # If searching/filtering, we might not have all categories, so check first.
        if product['category_name'] in products_by_category:
            products_by_category[product['category_name']].append(product)
        else: # if a product from a search doesn't fit in the categories, create a new one
            products_by_category[product['category_name']] = [product]


    return render_template('inventory.html', categories=categories, products_by_category=products_by_category, 
                           search_query=search_query, selected_category_id=int(category_id) if category_id else None)

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

    conn = get_db()
    # Create a string of placeholders for the query
    placeholders = ','.join('?' for _ in cart.keys())
    product_ids = list(cart.keys())
    
    cart_products = conn.execute(f'SELECT * FROM products WHERE id IN ({placeholders})', product_ids).fetchall()
    ()

    cart_items = []
    total_price = 0
    for product in cart_products:
        # Prices are now stored as REAL, so no parsing is needed.
        price = product['price']
        cart_items.append({
            'id': product['id'],
            'name': product['name'],
            'price': price, # Use the numeric price directly
            'image_file': product['image_file'],
            'numeric_price': price
        })
        total_price += price


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
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if product is None:
        flash('Product not found.', 'danger')
        return redirect(url_for('inventory'))

    related_products = conn.execute('SELECT * FROM products WHERE category_id = ? AND id != ? LIMIT 4', 
                                    (product['category_id'], product_id)).fetchall()
    ()
    
    return render_template('product.html', product=product, related_products=related_products)













if __name__ == '__main__':
    app.run(debug=True)











