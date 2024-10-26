from flask import Flask, render_template, request, redirect, url_for , flash , session
import sqlite3
import datetime

app = Flask(__name__)
app.secret_key = 'secret_key'

import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    print("Opened database successfully")
    conn.execute('CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, address TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS product (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, model TEXT, price REAL, quantity INTEGER)')
    conn.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, product_id INTEGER, quantity INTEGER, order_date DATE, FOREIGN KEY (customer_id) REFERENCES customers(id), FOREIGN KEY (product_id) REFERENCES product(id))')
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password TEXT NOT NULL, role TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, quantity INTEGER, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (product_id) REFERENCES product(id))')
    print("Tables created successfully")
    conn.close()

init_db()
@app.route('/')
def b():
    return render_template('body.html')

#home
@app.route('/body')
def body():
    return render_template('body.html')
#register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            return "User already exists!"
        cursor.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)', ( name, email, password, role))
        conn.commit()        
        if role == 'user':
            add_customer(name, email) 
        conn.close()
        return redirect(url_for('body'))
    return render_template('register.html')
#admin login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=? AND role='admin'", (email, password))
        admin_user = cursor.fetchone()
        if admin_user:
            return redirect(url_for('index'))
        else:
            return redirect(url_for('body', error='Invalid email or password'))
    return render_template('admin_login.html')
#Customer page
@app.route('/index')
def index():
    customers = get_customers()
    return render_template('index.html', customers=customers)
@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    email = request.form['email']
    add_customer(name, email)
    return redirect(url_for('index'))
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if request.method == 'GET':
        customer = get_customer_by_id(id)
        return render_template('customer.html', customer=customer)
    else:
        name = request.form['name']
        email = request.form['email']
        update_customer(id, name, email)
        return redirect(url_for('index'))
@app.route('/delete/<int:id>')
def delete(id):
    delete_customer(id)
    return redirect(url_for('index'))
#product page
@app.route('/products')
def products():
    products = get_products()
    return render_template('products.html', products=products)
@app.route('/add_product', methods=['POST'])
def add_product_route():
    name = request.form['name']
    model=request.form['model']
    price = float(request.form['price'])
    quantity=int(request.form['quantity'])
    add_product(name, model, price, quantity)
    return redirect(url_for('products'))
@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if request.method == 'GET':
        product = get_product_by_id(id)
        return render_template('edit_product.html', product=product)
    else:
        name = request.form['name']
        price = float(request.form['price'])
        quantity = int(request.form['quantity'])
        update_product(id, name, price, quantity)
        return redirect(url_for('products'))
@app.route('/delete_product/<int:id>')
def delete_product_route(id):
    delete_product(id)
    return redirect(url_for('products'))
#select_products
@app.route('/select_products', methods=['GET', 'POST'])
def select_products():
    if request.method == 'POST':
        customer_email = request.form['customer_email']
        order_date = request.form['order_date']
        order_date = datetime.datetime.strptime(order_date, '%Y-%m-%d').date()        
        customer = get_customer_by_email(customer_email)
        if customer:
            customer_id = customer[0]
            selected_product_ids = request.form.getlist('product_ids')
            for product_id in selected_product_ids:
                quantity = int(request.form[f'quantity_{product_id}'])
                add_order(customer_id, product_id, quantity, order_date)  # Update order and product quantity
            return redirect(url_for('order_confirmation', customer_id=customer_id))
        else:
            return "Customer not found!"
    products = get_products()
    return render_template('select_products.html', products=products)
#order confirmation
@app.route('/order_confirmation/<int:customer_id>')
def order_confirmation(customer_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    customer = cur.fetchone()
    cur.execute("""
        SELECT o.id, p.name, p.price, o.quantity, (p.price * o.quantity) AS subtotal
        FROM orders AS o
        JOIN product AS p ON o.product_id = p.id
        WHERE o.customer_id=?
    """, (customer_id,))
    orders = cur.fetchall()
    total = sum(order[4] for order in orders)
    conn.close()
    return render_template('order_confirmation.html', customer=customer, orders=orders, total=total)
#payment
@app.route('/process_payment/<int:customer_id>', methods=['GET', 'POST'])
def process_payment(customer_id):
    if request.method == 'POST':
        card_number = request.form.get('card_number')
        expiry_date = request.form.get('expiry_date')
        cvv = request.form.get('cvv')
        if not all([card_number, expiry_date, cvv]):
            flash("Please fill in all payment details.", "error")
            return redirect(url_for('process_payment', customer_id=customer_id))
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute("UPDATE orders SET payment_status='paid' WHERE customer_id=?", (customer_id,))
        conn.commit()
        conn.close()
        flash("Payment successful!", "success")
        return redirect(url_for('thank_you'))
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    customer = cur.fetchone()
    cur.execute("""
        SELECT o.id, p.name, p.price, o.quantity, (p.price * o.quantity) AS subtotal
        FROM orders AS o
        JOIN product AS p ON o.product_id = p.id
        WHERE o.customer_id=?
    """, (customer_id,))
    orders = cur.fetchall()
    total = sum(order[4] for order in orders)
    conn.close()
    return render_template('process_payment.html', customer=customer, orders=orders, total=total)
@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')
#view all orders
@app.route('/orders_conf')
def orders_conf():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.name, c.email, o.id, p.name, p.price, o.quantity, (p.price * o.quantity) AS subtotal, o.order_date, o.payment_status
        FROM customers AS c
        LEFT JOIN orders AS o ON c.id = o.customer_id
        LEFT JOIN product AS p ON o.product_id = p.id
        ORDER BY c.id, o.id
    """)
    results = cur.fetchall()
    customers = {}
    for row in results:
        customer_id = row[0]
        if customer_id not in customers:
            customers[customer_id] = {
                'id': customer_id,
                'name': row[1],
                'email': row[2],
                'orders': []
            }
        if row[3] is not None:  
            customers[customer_id]['orders'].append({
                'order_id': row[3],
                'product_name': row[4],
                'price': row[5],
                'quantity': row[6],
                'subtotal': row[7],
                'order_date': row[8],  
                'payment_status': row[9]  
            })
    for customer in customers.values():
        customer['total'] = sum(order['subtotal'] or 0 for order in customer.get('orders', []))
    conn.close()
    return render_template('orders_conf.html', customers=customers)
@app.route('/update_order/<int:order_id>', methods=['GET', 'POST'])
def update_order(order_id):
    if request.method == 'POST':
        new_quantity = request.form['new_quantity']
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute("UPDATE orders SET quantity=? WHERE id=?", (new_quantity, order_id))
        conn.commit()
        conn.close()
        return redirect(url_for('orders_conf'))
    else:
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute("SELECT o.id, p.name, o.quantity FROM orders AS o JOIN product AS p ON o.product_id = p.id WHERE o.id=?", (order_id,))
        order = cur.fetchone()
        conn.close()
        
        if order is not None:
            return render_template('update_order.html', order=order)
        else:
            # Handle the case where order is not found
            flash("Order not found!", "error")
            return redirect(url_for('orders_conf'))
@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM orders WHERE id=?", (order_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('orders_conf'))
#CRUD OF CUSTOMER
def add_customer(name, email):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO customers (name, email) VALUES (?, ?)", (name, email))
    conn.commit()
    conn.close()
def get_customers():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers")
    rows = cur.fetchall()
    conn.close()
    return rows
def get_customer_by_id(customer_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    customer = cur.fetchone()
    conn.close()
    return customer
def update_customer(customer_id, name, email):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("UPDATE customers SET name=?, email=? WHERE id=?", (name, email, customer_id))
    conn.commit()
    conn.close()
def delete_customer(customer_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM customers WHERE id=?", (customer_id,))
    conn.commit()
    conn.close()
#CRUD OF PRODUCT
def add_product(name,model, price, quantity):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO product (name,model, price, quantity) VALUES (?,?,  ?, ?)", (name, model,price, quantity))
    conn.commit()
    conn.close()
def get_products():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM product")
    rows = cur.fetchall()
    conn.close()
    return rows
def get_product_by_id(product_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM product WHERE id=?", (product_id,))
    product = cur.fetchone()
    conn.close()
    return product  
def update_product(product_id, name, price,quantity):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("UPDATE product SET name=?, price=? ,quantity=? WHERE id=?", (name, price,quantity, product_id))
    conn.commit()
    conn.close()
def delete_product(product_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM product WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
# Fetch a customer by email
def get_customer_by_email(email):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE email=?", (email,))
    customer = cur.fetchone()
    conn.close()
    return customer
# Add new order record
def add_order(customer_id, product_id, quantity, order_date):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (customer_id, product_id, quantity, order_date) VALUES (?, ?, ?, ?)",
                (customer_id, product_id, quantity, order_date))
    cur.execute("SELECT quantity FROM product WHERE id=?", (product_id,))
    available_quantity = cur.fetchone()[0]
    if quantity > available_quantity:
        conn.close()
        return "Selected quantity exceeds available quantity"
    updated_quantity = available_quantity - quantity
    cur.execute("UPDATE product SET quantity=? WHERE id=?", (updated_quantity, product_id))
    conn.commit()
    conn.close()
def get_all_orders_with_details():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id AS customer_id, c.name AS customer_name, c.email AS customer_email,
               p.id AS product_id, p.name AS product_name, p.price AS product_price, o.quantity
        FROM orders AS o
        JOIN customers AS c ON o.customer_id = c.id
        JOIN product AS p ON o.product_id = p.id
    """)
    orders = cur.fetchall()
    conn.close()
    return orders

# User Login
@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=? AND role='user'", (email, password))
        customer = cursor.fetchone()
        conn.close()
        if customer:
            customer_id = customer[0]-1
            return redirect(url_for('uorder_confirmation', customer_id=customer_id))  
        else:
            return redirect(url_for('body', error='Invalid email or password'))
    return render_template('user_login.html')
@app.route('/uorder_confirmation/<int:customer_id>')
def uorder_confirmation(customer_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    customer = cur.fetchone()
    cur.execute("""
        SELECT o.id, p.name, p.price, o.quantity, (p.price * o.quantity) AS subtotal
        FROM orders AS o
        JOIN product AS p ON o.product_id = p.id
        WHERE o.customer_id=?
    """, (customer_id,))
    orders = cur.fetchall()
    total = sum(order[4] for order in orders)
    conn.close()
    return render_template('uorder_confirmation.html', customer=customer, orders=orders, total=total)

@app.route('/user_products')
def user_products():
    products = get_products()
    if 'customer_id' not in session:
        return redirect(url_for('user_login'))  # Redirect to login if customer ID is not in session

    customer_id = session['customer_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
        

    cursor.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    customer = cursor.fetchone()
        
    conn.close()
    return render_template('user_index.html', products=products,customer=customer)
# Search Products by Model
@app.route('/user_search_products', methods=['GET', 'POST'])
def user_search_products():
    if 'customer_id' not in session:
        return redirect(url_for('user_login'))  # Redirect to login if customer ID is not in session

    customer_id = session['customer_id']  # Get the customer ID from the session

    if request.method == 'POST':
        model = request.form['model']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM product WHERE model=?", (model,))
        products = cursor.fetchall()

        cursor.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
        customer = cursor.fetchone()
        
        conn.close()
        return render_template('user_search_products.html', products=products , customer=customer)
    return render_template('user_search_products.html')


@app.route('/user_select_products', methods=['GET', 'POST'])
def user_select_products():
    if request.method == 'POST':
        customer_email = request.form['customer_email']
        order_date = request.form['order_date']
        order_date = datetime.datetime.strptime(order_date, '%Y-%m-%d').date()        
        customer = get_customer_by_email(customer_email)
        if customer:
            customer_id = customer[0]
            selected_product_ids = request.form.getlist('product_ids')
            for product_id in selected_product_ids:
                quantity = int(request.form[f'quantity_{product_id}'])
                add_order(customer_id, product_id, quantity, order_date)  # Update order and product quantity
            return redirect(url_for('order_confirmation', customer_id=customer_id))
        else:
            return "Customer not found!"
    products = get_products()
    return render_template('user_select_products.html', products=products)

if __name__ == '__main__':
    app.run(debug=True)
