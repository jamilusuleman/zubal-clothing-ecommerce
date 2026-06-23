from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    flash
)
import sqlite3
import os
from werkzeug.utils import secure_filename
import urllib.parse
import uuid
import config

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

app = Flask(__name__)
app.config.from_object(config.Config)
app.secret_key = app.config["SECRET_KEY"]

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def init_db():

    conn = sqlite3.connect("database.db") 
    cursor = conn.cursor()


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        customer_name TEXT NOT NULL,

        phone TEXT NOT NULL,

        address TEXT NOT NULL,

        products TEXT NOT NULL,

        total REAL NOT NULL,

        status TEXT DEFAULT 'Pending'

    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        category TEXT NOT NULL,

        price REAL NOT NULL,

        description TEXT,

        image TEXT,

        gallery_image TEXT,

        stock INTEGER DEFAULT 0,

        featured INTEGER DEFAULT 0

    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        customer_name TEXT NOT NULL,

        product_id INTEGER NOT NULL,

        rating INTEGER NOT NULL,

        comment TEXT NOT NULL

    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        fullname TEXT NOT NULL,

        email TEXT UNIQUE NOT NULL,

        password TEXT NOT NULL

    )
    """)

    conn.commit()
    conn.close()

init_db()        



#------ LOGIN ROUTE-------

@app.route("/")
def login():

    return render_template(
        "login.html"
    )



#-------- DASHBOARD ROUTE--------      


@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    # Total Products
    cursor.execute(
        "SELECT COUNT(*) FROM products"
    )
    total_products = cursor.fetchone()[0]

    # Total Orders
    cursor.execute(
        "SELECT COUNT(*) FROM orders"
    )
    total_orders = cursor.fetchone()[0]

    # Pending Orders
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status='Pending'
        """
    )
    pending_orders = cursor.fetchone()[0]

    # Delivered Orders
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status='Delivered'
        """
    )
    delivered_orders = cursor.fetchone()[0]

    # Revenue
    cursor.execute(
        """
        SELECT SUM(total)
        FROM orders
        WHERE status='Delivered'
        """
    )

    revenue = cursor.fetchone()[0]

    if revenue is None:
        revenue = 0

    cursor.execute(
    """
    SELECT *
    FROM orders
    ORDER BY id DESC
    LIMIT 5
    """
    )

    recent_orders = cursor.fetchall()     

    # conn.close()

    cursor.execute("""
    SELECT products, COUNT(*) as total_sales
    FROM orders
    GROUP BY products
    ORDER BY total_sales DESC
    LIMIT 1
    """)

    top_product = cursor.fetchone()



    cursor.execute("""
    SELECT *
    FROM products
    WHERE stock <= 5
    """)

    low_stock_products = cursor.fetchall()

    conn.close()

    return render_template( 
        "dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        pending_orders=pending_orders,
        delivered_orders=delivered_orders,
        revenue=revenue,
        recent_orders=recent_orders,
        top_product=top_product,
low_stock_products=low_stock_products
    )



#-------- ADD PRODUCT ROUTE--------

@app.route("/add-product")
def add_product():

    if "user" not in session:

        return redirect("/")
    
    return render_template("add_product.html")



#-------- SAVE PRODUCT ROUTE--------


@app.route("/save-product", methods=["POST"])
def save_product():

    name = request.form["name"]
    category = request.form["category"]
    price = request.form["price"]
    description = request.form["description"]
    stock = request.form["stock"]
    featured = 1 if "featured" in request.form else 0        


    image = request.files["image"]
    
    if image.filename == "":

        flash(
            "Please select a product image.",
            "error"
        )

        return redirect("/add-product")
    
    if not allowed_file(image.filename):

        flash(
            "Only JPG, JPEG, PNG and WEBP images are allowed.",
            "error"
        )

        return redirect("/add-product")


    gallery_image = request.files["gallery_image"]

    if (
        gallery_image.filename != ""
        and
        not allowed_file(gallery_image.filename)
    ):

        flash(
            "Gallery image must be JPG, JPEG, PNG or WEBP.",
            "error"
        )

        return redirect("/add-product")

    original_filename = secure_filename(image.filename)

    filename = f"{uuid.uuid4().hex}_{original_filename}"


    gallery_filename = ""

    if gallery_image.filename != "":

        original_gallery = secure_filename(
            gallery_image.filename
        )

        gallery_filename = (
            f"{uuid.uuid4().hex}_{original_gallery}"
        )    

        gallery_image.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                gallery_filename
        )
    )

    image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    image.save(image_path)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO products 
                (
                name,
                category,
                price,
                description,
                image,
                gallery_image,
                stock,
                featured   
                )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, category, price, description, filename, gallery_filename, stock, featured))

    conn.commit()
    print("Saved image:", filename, gallery_filename)
    conn.close()

    return redirect("/products")



#------- PRODUCTS ROUTE---------

@app.route("/products")
def products():

    if "user" not in session:
        return redirect("/")

    search = request.args.get("search", "")

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    if search:

        cursor.execute(
            """
            SELECT *
            FROM products
            WHERE name LIKE ?
            """,
            ('%' + search + '%',)
        )

    else:

        cursor.execute(
            "SELECT * FROM products"
        )

    products = cursor.fetchall()

    conn.close()

    return render_template(
        "products.html",
        products=products
    )



@app.route("/edit-product/<int:id>")
def edit_product(id):

    if "user" not in session:

        return redirect("/")
    
    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM products WHERE id=?",
        (id,)
    )

    product = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_product.html",
        product=product
    )


#------- UPDATE PRODUCT ROUTE-------

@app.route("/update-product/<int:id>", methods=["POST"])
def update_product(id):

    name = request.form["name"]
    category = request.form["category"]
    price = request.form["price"]
    stock = request.form["stock"]
    description = request.form["description"]
    print("Selected Category:", category)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    image_file = request.files.get("image")


    cursor.execute(
        "SELECT image FROM products WHERE id=?",
        (id,)
    )

    old_image = cursor.fetchone()[0]


    if image_file and image_file.filename != "":

        original_filename = secure_filename(
            image_file.filename
        )

        filename = (
            f"{uuid.uuid4().hex}_{original_filename}"
        )

        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        image_file.save(image_path)

        old_image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            old_image
        )

        if os.path.exists(old_image_path):

            os.remove(old_image_path)


        cursor.execute("""
            UPDATE products
            SET
                name=?,
                category=?,
                price=?,
                stock=?,     
                description=?,
                image=?
            WHERE id=?
        """, (
            name,
            category,
            price,
            stock,
            description,
            filename,
            id
        ))

    else:

        cursor.execute("""
            UPDATE products
            SET
                name=?,
                category=?,
                price=?,
                stock=?,       
                description=?
            WHERE id=?
        """, (
            name,
            category,
            price,
            stock,
            description,
            id
        ))
        

    conn.commit()
    conn.close()

    return redirect("/products")





#------ DELETE PRODUCT ROUTE-------

@app.route("/delete-product/<int:id>")
def delete_product(id):

    if "user" not in session:

        return redirect("/")    

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()



    cursor.execute(
        """
        SELECT image, gallery_image
        FROM products
        WHERE id=?
        """,
        (id,)
    )

    product = cursor.fetchone()


    if product:

        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            product[0]
        )

        if os.path.exists(image_path):

            os.remove(image_path)


        if product[1]:

            gallery_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                product[1]
            )

            if os.path.exists(gallery_path):

                os.remove(gallery_path)




    cursor.execute(
        "DELETE FROM products WHERE id=?",
        (id,)
    )

    conn.commit()

    conn.close()

    return redirect("/products")



@app.route(
    "/login",
    methods=["POST"]
)
def process_login():

    username = request.form["username"]

    password = request.form["password"]

    if (
        username == "admin"
        and
        password == "1234"
    ):

        session["user"] = username

        return redirect(
            "/dashboard"
        )

    return "Invalid Login"


@app.route("/logout")
def logout():

    session.pop(
        "user",
        None
    )

    return redirect("/")



#------ ODERS ROUTE-------

@app.route("/orders")
def orders():

    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM orders"
    )

    orders = cursor.fetchall()

    conn.close()

    return render_template(
        "orders.html",
        orders=orders
    )


# -------SHOP ROUTE--------

@app.route("/shop")
def shop():

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()


    search = request.args.get(
        "search",
        ""
    )

    category = request.args.get(
        "category",
        ""
    )

    query = "SELECT * FROM products WHERE 1=1"

    params = []

    if search:

        query += " AND name LIKE ?"

        params.append(
            "%" + search + "%"
        )

    if category:

        query += " AND category=?"

        params.append(category)

    cursor.execute(
        query,
        params
    )

    products = cursor.fetchall()


    cursor.execute("""
    SELECT *
    FROM products
    ORDER BY id DESC
    LIMIT 4
    """)

    new_arrivals = cursor.fetchall()

    cursor.execute(
    """
    SELECT *
    FROM products
    WHERE featured = 1
    """
    )

    featured_products = cursor.fetchall()

    
    cursor.execute(
        "SELECT * FROM reviews"
    )

    reviews = cursor.fetchall()

    rating_stats = {}


    for product in products:

        product_reviews = []

        for review in reviews:

            if review["product_id"] == product["id"]:

                product_reviews.append(
                    review["rating"]
                )

        if product_reviews:

            average = sum(product_reviews) / len(product_reviews)

            rating_stats[product["id"]] = {

                "average": round(average, 1),

                "count": len(product_reviews)

            }

        else:

            rating_stats[product["id"]] = {

                "average": 0,

                "count": 0

            }


    conn.close()

    cart_count = len(session.get("cart", []))
    wishlist_count = len(session.get("wishlist", []))
    toast = session.pop("toast", None)

    return render_template(
        "shop.html",
        products=products,
        reviews=reviews,
        rating_stats=rating_stats,
        featured_products=featured_products,
        new_arrivals=new_arrivals,
        cart_count=cart_count,
        wishlist_count=wishlist_count,
        toast=toast

    )



#------ PRODUCT ROUTE-------


@app.route("/product/<int:id>")
def product_details(id):

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM products WHERE id=?",
        (id,)
    )

    product = cursor.fetchone()

    cursor.execute(
        """
        SELECT *
        FROM products
        WHERE category=?
        AND id != ?
        LIMIT 4
        """,
        (
            product["category"],
            id
        )
    )

    related_products = cursor.fetchall()

    cursor.execute(
        """
        SELECT *
        FROM reviews
        WHERE product_id=?
        """,
        (id,)
    )

    reviews = cursor.fetchall()


    average_rating = 0

    if reviews:

        total = 0

        for review in reviews:

            total += review["rating"]

        average_rating = round(
            total / len(reviews),
            1
        )


    conn.close()

    if not product:

        return redirect("/shop")

    return render_template(
        "product_details.html",
        product=product,
        reviews=reviews,
        average_rating=average_rating,
        related_products=related_products

    )




# -------ADD TO CART ROIUTE----------

@app.route("/add-to-cart/<int:id>")
def add_to_cart(id):

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM products WHERE id=?",
        (id,)
    )

    product = cursor.fetchone()

    conn.close()

    if not product:

        return redirect("/shop")

    if product["stock"] <= 0:

        return redirect("/shop")

    cart = session.get("cart", [])

    cart.append(id)

    session["cart"] = cart

    session.modified = True

    session["toast"] = "🛒 Product added to cart!"

    return redirect("/shop")



#------ ADD TO WISH_LIST ROUTE -------

@app.route("/add-to-wishlist/<int:id>")
def add_to_wishlist(id):

    wishlist = session.get(
        "wishlist",
        []
    )

    if id not in wishlist:

        wishlist.append(id)

    session["wishlist"] = wishlist

    session.modified = True

    session["toast"] = "❤️ Product added to wishlist!"

    return redirect("/shop")


#-------- REMOVE FROM WISH LIST ROUTE ------


@app.route("/remove-from-wishlist/<int:id>")
def remove_from_wishlist(id):

    wishlist = session.get(
        "wishlist",
        []
    )

    if id in wishlist:

        wishlist.remove(id)

    session["wishlist"] = wishlist

    session.modified = True

    session["toast"] = "❌ Product removed from wishlist!"

    return redirect("/wishlist")






#------- WISH LIST ROUTE------


@app.route("/wishlist")
def wishlist():

    wishlist_ids = session.get(
        "wishlist",
        []
    )

    conn = sqlite3.connect(
        "database.db"
    )

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    products = []

    for product_id in wishlist_ids:

        cursor.execute(
            """
            SELECT *
            FROM products
            WHERE id=?
            """,
            (product_id,)
        )

        product = cursor.fetchone()

        if product:

            products.append(product)

    conn.close()
    toast = session.pop("toast", None)

    return render_template(
        "wishlist.html",
        products=products,
        toast=toast
    )



# --------INCREASE QUANTITY ROUTE--------


@app.route("/increase-quantity/<int:id>")
def increase_quantity(id):

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM products WHERE id=?",
        (id,)
    )

    product = cursor.fetchone()

    conn.close()

    if not product:

        return redirect("/cart")

    cart = session.get("cart", [])

    current_quantity = cart.count(id)

    if current_quantity < product["stock"]:

        cart.append(id)

    session["cart"] = cart

    session.modified = True

    return redirect("/cart")




#------ DECREASE QUANTITY ROUTE------

@app.route("/minus/<int:id>")
def decrease_quantity(id):

    cart = session.get("cart", [])

    if id in cart:

        cart.remove(id)

    session["cart"] = cart

    session.modified = True

    return redirect("/cart")


# --------REMOVE FROM CART ROUTE --------

@app.route("/remove-from-cart/<int:id>")
def remove_from_cart(id):

    cart = session.get("cart", [])

    if id in cart:

        cart.remove(id)

    session["cart"] = cart

    session.modified = True

    session["toast"] = "🗑️ Product removed from cart!"

    return redirect("/cart")


# ---------CART ROUTE-----------

@app.route("/cart")
def cart():

    if "cart" not in session:

        session["cart"] = []

    cart_ids = session["cart"]

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    products = {}

    for product_id in cart_ids:

        cursor.execute(
            "SELECT * FROM products WHERE id=?",
            (product_id,)
        )

        product = cursor.fetchone()

        if product:

            product_id = product["id"]

            if product_id in products:

                products[product_id]["quantity"] += 1

            else:

                products[product_id] = {
                    "id": product["id"],
                    "name": product["name"],
                    "price": product["price"],
                    "image": product["image"],
                    "quantity": 1
                }

    cart_products = list(products.values())

    total = 0

    for product in cart_products:

        total += product["price"] * product["quantity"]    


    conn.close()
    toast = session.pop("toast", None)

    return render_template(
        "cart.html",
        products=cart_products,
        total=total,
        toast=toast
    )



#------ CHECK OUT ROUTE ------------

@app.route("/checkout")
def checkout():

    if "cart" not in session or len(session["cart"]) == 0:
        return redirect("/shop")

    return render_template("checkout.html")


# --------PLACE ORDER ROUTE--------

@app.route("/place-order", methods=["POST"])
def place_order():

    name = request.form["name"]
    phone = request.form["phone"]
    address = request.form["address"]

    cart_ids = session.get("cart", [])

    if not cart_ids:
        return redirect("/shop")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    products = []
    total = 0

    for product_id in cart_ids:

        cursor.execute(
            "SELECT * FROM products WHERE id=?",
            (product_id,)
        )

        product = cursor.fetchone()


        if product:

            products.append(product)

            total += product[2]

            current_stock = product[6]

            new_stock = current_stock - 1

            if new_stock < 0:
                new_stock = 0

            cursor.execute(
                """
                UPDATE products
                SET stock=?
                WHERE id=?
                """,
                (
                    new_stock,
                    product_id
                )
            )        
        
    product_names = ", ".join([p[1] for p in products])

    cursor.execute("""
        INSERT INTO orders (
            customer_name,
            phone,
            address,
            products,
            total,
            status       
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        phone,
        address,
        product_names,
        total,
        "Pending",
        
    ))

    conn.commit()
    conn.close()

    session["cart"] = []

    message = f"New Order from Zubal Clothing | Name: {name} | Phone: {phone} | Address: {address} | Products: {product_names} | Total: ₦{total}"


    encoded_message = urllib.parse.quote(message)

    whatsapp_url = f"https://wa.me/+2349069426528?text={encoded_message}"

    return render_template(
    "order_success.html",
    whatsapp_url=whatsapp_url
    )

    


#-------- ORDER SUCCESS--------

@app.route("/order-success")
def order_success():
    return "<h1>Order placed successfully!</h1><a href='/shop'>Continue Shopping</a>"



#---------- DELIVER ORDER ROUTE----------

@app.route("/deliver-order/<int:id>")
def deliver_order(id):

    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE orders
        SET status='Delivered'
        WHERE id=?
        """,
        (id,)
    )

    conn.commit()

    conn.close()

    return redirect("/orders")


#------- DELETE ORDER ROUTE--------

@app.route("/delete-order/<int:id>")
def delete_order(id):

    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM orders WHERE id=?",
        (id,)
    )

    conn.commit()

    conn.close()

    return redirect("/orders")



#-------- TRACK ORDER ROUTE------

@app.route("/track-order")
def track_order_page():

    return render_template(
        "track_order.html"
    )


#------- TRACK ORDER WITH POST ROUTE-------

@app.route("/track-order", methods=["POST"])
def track_order():

    phone = request.form["phone"]

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM orders
        WHERE phone=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (phone,)
    )

    order = cursor.fetchone()

    conn.close()

    return render_template(
        "order_result.html",
        order=order
    )



#------- ADD REVIEW ROUTE---------


@app.route("/add-review", methods=["POST"])
def add_review():

    customer_name = request.form["customer_name"]

    product_id = request.form["product_id"]

    rating = request.form["rating"]

    comment = request.form["comment"]

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reviews (
        customer_name,
        product_id,
        rating,
        comment
    )
    VALUES (?, ?, ?, ?)
    """, (
        customer_name,
        product_id,
        rating,
        comment
    ))

    conn.commit()

    conn.close()

    return redirect("/shop")


#-------- REGISTER ROUTE (CUSTOMER REGISTER ROUTE)------

@app.route(
    "/register",
    methods=["GET","POST"]
)
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]

        email = request.form["email"]

        password = request.form["password"]

        conn = sqlite3.connect(
            "database.db"
        )

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO customers(
                fullname,
                email,
                password
            )
            VALUES(?,?,?)
            """,
            (
                fullname,
                email,
                password
            )
        )

        conn.commit()

        conn.close()

        return redirect(
            "/customer-login"
        )

    return render_template(
        "register.html"
    )



#-------- CUSTOMER LOGIN ROUTE-------


@app.route(
    "/customer-login",
    methods=["GET","POST"]
)
def customer_login():

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]

        conn = sqlite3.connect(
            "database.db"
        )

        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM customers
            WHERE email=?
            AND password=?
            """,
            (
                email,
                password
            )
        )

        customer = cursor.fetchone()

        conn.close()

        if customer:

            session[
                "customer_id"
            ] = customer["id"]

            session[
                "customer_name"
            ] = customer["fullname"]

            return redirect(
                "/shop"
            )

    return render_template(
        "customer_login.html"
    )


#------ CUSTOMER LOG OUT ROUTE------

@app.route("/customer-logout")
def customer_logout():

    session.pop(
        "customer_id",
        None
    )

    session.pop(
        "customer_name",
        None
    )

    return redirect(
        "/customer-login"
    )



#-------- PAGE NOT FOUND ROUTE--------

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "404.html"
    ), 404


#-------- INTERNAL SERVER ERROR ROUTE--------


@app.errorhandler(500)
def internal_server_error(error):

    return render_template(
        "500.html"
    ), 500



if __name__ == "__main__":

    init_db()

    app.run(
        debug=app.config["DEBUG"]
    )





