import sqlite3
import re

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect('jengamart.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the products and categories tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')

    # Create products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            image_file TEXT,
            featured INTEGER DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    print("Initialized the database.")

def populate_db():
    """Populates the database with initial product data."""
    products_data = [
        # CEMENT
        {"name": "Bamburi Nguvu Cement 50kg", "category": "CEMENT", "price": "885 KSh", "featured": 1},
        {"name": "Bamburi Fundi Cement 50kg", "category": "CEMENT", "price": "790 KSh"},
        {"name": "Bamburi Tembo Cement 50kg", "category": "CEMENT", "price": "850 KSh"},
        {"name": "Simba Cement 32.5R 50kg", "category": "CEMENT", "price": "950 KSh"},
        # STEEL
        {"name": "Deformed Steel Bar D8 (12m)", "category": "STEEL", "price": "450-520 KSh", "featured": 1},
        {"name": "Deformed Steel Bar D10 (12m)", "category": "STEEL", "price": "600-770 KSh"},
        {"name": "Deformed Steel Bar D12 (12m)", "category": "STEEL", "price": "900-1,150 KSh"},
        {"name": "High Tensile Steel 16mm", "category": "STEEL", "price": "approx. 145 KSh per kg"},
        # WOOD
        {"name": "Cypress Timber 4x2", "category": "WOOD", "price": "55 KSh per ft", "featured": 1},
        {"name": "Pine Timber 4x2", "category": "WOOD", "price": "38 KSh per ft"},
        {"name": "Cypress Timber 2x2", "category": "WOOD", "price": "28 KSh per ft"},
        # PLUMBING
        {"name": "PVC Pipe 32mm (6m)", "category": "PLUMBING", "price": "350 KSh"},
        {"name": "PVC Pipe 110mm (6m)", "category": "PLUMBING", "price": "2,730 KSh"},
        {"name": "HDPE Coupling 50mm", "category": "PLUMBING", "price": "550 KSh"},
        # ELECTRICAL
        {"name": "PVC Electrical Conduit 20mm (4m)", "category": "ELECTRICAL", "price": "120 KSh"},
        {"name": "Flexible Conduit 25mm (roll)", "category": "ELECTRICAL", "price": "2,500 KSh"},
        # AGGREGATES
        {"name": "Fine Sand", "category": "AGGREGATES", "price": "approx. 3,609 KSh per m³"},
        {"name": "Ballast / Coarse Aggregate", "category": "AGGREGATES", "price": "approx. 4,467 KSh per m³"},
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    for product in products_data:
        # Get or insert category
        cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (product['category'],))
        cursor.execute("SELECT id FROM categories WHERE name = ?", (product['category'],))
        category_id = cursor.fetchone()['id']

        # Extract numeric part from price string (e.g., "885 KSh" -> 885.0)
        price_str = product['price']
        numeric_price = 0.0
        
        match = re.match(r'[\d,\.]+', price_str)
        if match:
            # Remove commas, then convert to float
            numeric_price = float(match.group(0).replace(',', ''))
        
        # Insert product
        cursor.execute(
            "INSERT INTO products (name, category_id, price, image_file, featured) VALUES (?, ?, ?, ?, ?)",
            (
                product['name'],
                category_id,
                numeric_price, # Use the converted numeric price
                "placeholder.jpg",
                product.get('featured', 0)
            )
        )

    conn.commit()
    conn.close()
    print("Populated the database with initial data.")

if __name__ == "__main__":
    init_db()
    populate_db()
