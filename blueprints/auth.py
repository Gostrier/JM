from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
from ..db import get_db # Import get_db from the new db.py module

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to be logged in to view this page.', 'info')
            return redirect(url_for('auth.login')) # Note: changed to auth.login
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))

        conn = get_db()
        user_by_username = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        user_by_email = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user_by_username:
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.register'))
        if user_by_email:
            flash('Email address already registered.', 'danger')
            return redirect(url_for('auth.register'))

        password_hash = generate_password_hash(password)

        try:
            conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                         (username, email, password_hash))
            conn.commit()
            flash('You have successfully registered! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except sqlite3.IntegrityError:
            conn.rollback()
            flash('An account with this email or username already exists.', 'danger')
            return redirect(url_for('auth.register'))
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'Database error: {e}', 'danger')
            return redirect(url_for('auth.register'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            if user['is_admin']:
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin.admin_dashboard')) # Note: changed to admin.admin_dashboard
            else:
                flash('Login successful!', 'success')
                return redirect(url_for('profile'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))