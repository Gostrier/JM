from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from JENGAMART.blueprints.auth import login_required
import sqlite3
import os
from uuid import uuid4
from werkzeug.utils import secure_filename
from ..db import get_db # Import get_db from the new db.py module

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to be logged in to view this page.', 'info')
            return redirect(url_for('auth.login'))
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        if not user or not user['is_admin']:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_required
def admin_dashboard():
    conn = get_db()
    products = conn.execute('SELECT p.id, p.name, p.price, c.name as category_name, p.image_file FROM products p JOIN categories c ON p.category_id = c.id ORDER BY p.name').fetchall()
    return render_template('admin/dashboard.html', products=products)

@admin_bp.route('/add_product', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        try:
            price = float(request.form['price'])
        except ValueError:
            flash('Price must be a valid number.', 'danger')
            return redirect(url_for('admin.add_product'))
        description = request.form['description']
        category_id = request.form['category_id']
        image = request.files.get('image')

        if not all([name, price, description, category_id]):
            flash('All fields except image are required.', 'danger')
            return redirect(url_for('admin.add_product'))

        image_filename = 'placeholder.jpg'
        if image and allowed_file(image.filename):
            # Generate a unique filename
            extension = image.filename.rsplit('.', 1)[1].lower()
            unique_filename = str(uuid4()) + '.' + extension
            image_filename = unique_filename
            image.save(os.path.join(admin_bp.root_path, '..', 'static', 'images', image_filename))
        elif image and image.filename != '':
            flash('Invalid file type for image. Allowed types are png, jpg, jpeg, gif.', 'danger')
            return redirect(url_for('admin.add_product'))

        conn = get_db()
        try:
            conn.execute('INSERT INTO products (name, price, description, category_id, image_file) VALUES (?, ?, ?, ?, ?)',
                         (name, price, description, category_id, image_filename))
            conn.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except sqlite3.IntegrityError:
            conn.rollback()
            flash('A product with this name already exists.', 'danger')
            return redirect(url_for('admin.add_product'))
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'Database error: {e}', 'danger')
            return redirect(url_for('admin.add_product'))
    
    conn = get_db()
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    return render_template('admin/add_product.html', categories=categories)

@admin_bp.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if product is None:
        flash('Product not found.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        try:
            price = float(request.form['price'])
        except ValueError:
            flash('Price must be a valid number.', 'danger')
            return redirect(url_for('admin.edit_product', product_id=product_id))
        description = request.form['description']
        category_id = request.form['category_id']
        image = request.files.get('image')

        # Check if product name already exists for another product
        existing_product = conn.execute('SELECT id FROM products WHERE name = ? AND id != ?', (name, product_id)).fetchone()
        if existing_product:
            flash('A product with this name already exists.', 'danger')
            return redirect(url_for('admin.edit_product', product_id=product_id))

        image_filename = product['image_file'] # Keep existing image if no new image uploaded
        if image and allowed_file(image.filename):
            # Generate a unique filename
            extension = image.filename.rsplit('.', 1)[1].lower()
            unique_filename = str(uuid4()) + '.' + extension
            image_filename = unique_filename
            # Save new image
            image.save(os.path.join(admin_bp.root_path, '..', 'static', 'images', image_filename))
            # Delete old image if it's not the placeholder
            if product['image_file'] and product['image_file'] != 'placeholder.jpg':
                try:
                    os.remove(os.path.join(admin_bp.root_path, '..', 'static', 'images', product['image_file']))
                except OSError as e:
                    print(f"Error deleting old image: {e}") # Log error but don't stop execution

        try:
            conn.execute('UPDATE products SET name = ?, price = ?, description = ?, category_id = ?, image_file = ? WHERE id = ?',
                         (name, price, description, category_id, image_filename, product_id))
            conn.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'Database error: {e}', 'danger')
            return redirect(url_for('admin.edit_product', product_id=product_id))
    
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    return render_template('admin/edit_product.html', product=product, categories=categories)

@admin_bp.route('/delete_product/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if product is None:
        flash('Product not found.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        # Delete image file if it's not the placeholder
        if product['image_file'] and product['image_file'] != 'placeholder.jpg':
            try:
                os.remove(os.path.join(admin_bp.root_path, '..', 'static', 'images', product['image_file']))
            except OSError as e:
                print(f"Error deleting image: {e}")
        flash('Product deleted successfully!', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Database error: {e}', 'danger')
    
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/bulk-updates')
@admin_required
def bulk_updates():
    return render_template('admin/bulk_updates.html')

@admin_bp.route('/bulk-update-featured', methods=['POST'])
@admin_required
def bulk_update_featured():
    featured_status = request.form.get('featured_status')
    if featured_status not in ['0', '1']:
        flash('Invalid featured status value.', 'danger')
        return redirect(url_for('admin.bulk_updates'))

    conn = get_db()
    try:
        conn.execute('UPDATE products SET featured = ?', (int(featured_status),))
        conn.commit()
        flash('Featured status for all products has been updated.', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Database error: {e}', 'danger')
    
    return redirect(url_for('admin.bulk_updates'))

@admin_bp.route('/bulk-update-prices', methods=['POST'])
@admin_required
def bulk_update_prices():
    try:
        percentage = float(request.form.get('price_update_percentage'))
    except (ValueError, TypeError):
        flash('Invalid percentage value.', 'danger')
        return redirect(url_for('admin.bulk_updates'))

    conn = get_db()
    try:
        # Fetch all products
        products = conn.execute('SELECT id, price FROM products').fetchall()
        
        # Calculate and update new prices
        for product in products:
            new_price = product['price'] * (1 + percentage / 100)
            conn.execute('UPDATE products SET price = ? WHERE id = ?', (new_price, product['id']))
        
        conn.commit()
        flash(f'Prices for all products have been updated by {percentage}%.', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Database error: {e}', 'danger')
    
    return redirect(url_for('admin.bulk_updates'))

@admin_bp.route('/make-admin', methods=['POST'])
@login_required # This should remain login_required, not admin_required as the admin_required will handle the admin check.
def make_admin():
    user_id = request.form['user_id']
    try:
        user_id = int(user_id)
    except ValueError:
        flash('Invalid User ID.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
    conn = get_db()
    # First, ensure the current user is an admin before making changes.
    current_user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if not current_user or not current_user['is_admin']:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('home'))

    user_to_promote = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if not user_to_promote:
        flash('User not found.', 'danger')
    else:
        try:
            conn.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (user_id,))
            conn.commit()
            flash(f"{user_to_promote['username']} has been made an admin.", 'success')
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'Database error: {e}', 'danger')
    
    return redirect(url_for('admin.admin_dashboard'))
