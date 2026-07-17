from flask import Flask, render_template, session, redirect, request, url_for,flash
import os
import uuid
import sqlite3
import json
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "secret123")
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config["DB_PATH"] = os.path.join(os.path.dirname(__file__), 'shop.db')
app.config["ADMIN_USERNAME"] = os.environ.get("ADMIN_USERNAME", "admin")
app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD", "123456")

UPLOAD_FOLDER = app.config["UPLOAD_FOLDER"]
PRODUCT_IMAGE_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PRODUCT_IMAGE_FOLDER, exist_ok=True)


def get_db():
    conn = sqlite3.connect(app.config["DB_PATH"])
    conn.row_factory = sqlite3.Row
    return conn


def get_default_category(product_id):
    if product_id in range(101, 104):
        return 'section1'
    if product_id in range(104, 108):
        return 'section2'
    if product_id in range(108, 112):
        return 'section3'
    if product_id in range(112, 125):
        return 'section4'
    if product_id in range(125, 129):
        return 'section5'
    return 'general'


def init_db():
    conn = get_db()

    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            original_price REAL,
            description TEXT,
            category TEXT DEFAULT 'general',
            images TEXT,
            colors TEXT,
            requires_attachment INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
        )
    ''')

    try:
        conn.execute("""
            ALTER TABLE products
            ADD COLUMN requires_attachment INTEGER DEFAULT 0
        """)
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

    conn = get_db()
    count = conn.execute('SELECT COUNT(*) as count FROM products').fetchone()['count']
    if count == 0:
        for product in ramadan_products:
            conn.execute(
                '''
  INSERT INTO products (
    product_id, name, price, original_price,
    description, category, images, colors,
    requires_attachment, status
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', 
                (
    product.get('id'),
    product.get('name', ''),
    product.get('price', 0),
    product.get('original_price'),
    product.get('description', ''),
    product.get('category', get_default_category(product.get('id', 0))),
    json.dumps(product.get('images', []), ensure_ascii=False),
    json.dumps(product.get('colors', []), ensure_ascii=False),
    int(product.get('requires_attachment', False)),
    'active'
)
            )
        conn.commit()
    conn.close()


def row_to_product(row):
    if not row:
        return None

    product = dict(row)

    product['images'] = json.loads(product.get('images') or '[]')
    product['colors'] = json.loads(product.get('colors') or '[]')
    product['id'] = product.get('product_id')

    # هل يحتاج صورة من الزبون؟
    product['requires_attachment'] = bool(
        product.get('requires_attachment', 0)
    )

    return product


def get_product(product_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM products WHERE product_id = ?', (product_id,)).fetchone()
    conn.close()
    if row:
        return row_to_product(row)
    return next((p for p in ramadan_products if p['id'] == product_id), None)


def get_all_products():
    conn = get_db()
    rows = conn.execute('SELECT * FROM products WHERE status != ? ORDER BY product_id', ('hidden',)).fetchall()
    conn.close()
    return [row_to_product(row) for row in rows]


def get_products_by_category(category):
    conn = get_db()
    rows = conn.execute('SELECT * FROM products WHERE category = ? AND status != ? ORDER BY product_id', (category, 'hidden')).fetchall()
    conn.close()
    return [row_to_product(row) for row in rows]


def save_order(order_data, items):
    conn = get_db()
    conn.execute(
        '''
        INSERT INTO orders (
            customer_name, customer_phone, customer_address, payment_method,
            delivery_region, order_notes, total, shipping_fee, final_total, items_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_data['customer_name'],
            order_data['customer_phone'],
            order_data['customer_address'],
            order_data['payment_method'],
            order_data['delivery_region'],
            order_data['order_notes'],
            order_data['total'],
            order_data['shipping_fee'],
            order_data['final_total'],
            json.dumps(items, ensure_ascii=False),
            'new'
        )
    )
    conn.commit()
    conn.close()


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return view_func(*args, **kwargs)
    return wrapped


def get_region_shipping_fee(region):
    """Get shipping fee based on delivery region"""
    shipping_fees = {
        'west_bank': 25,       # الضفة الغربية
        'jerusalem': 35,        # القدس
        'inside_palestine': 80  # الداخل الفلسطيني
    }
    return shipping_fees.get(region, 0)

def is_attachment_required(product_id):
    product = get_product(product_id)
    if product:
        return bool(product.get('requires_attachment', 0))
    return False
ramadan_products = [
    {"id": 101, "name": " مصحف القيام", "price": 65, "images": ["moshaf_al_qeeam.jpg", "moshaf_al_qeeam.jpg"],"description":"الحجم : 20*28 "},
    {"id": 102, "name": " بطولة الصيام بصورة الطفل", "price": 10, "images": ["section1a.jpg", "section1aa.jpg"],"description":"الحجم: A5 - فوم - مع ألوان "},
    {"id": 103, "name": " دفتر ألوان بصورة الطفل", "price": 15, "images": ["section1b.jpg", "section1bb.jpg","section1bbb.jpg", "section1bbbb.jpg", "section1bbbbb.jpg"],"description":"دفتر ألوان"},
    {"id": 104, "name": " دفتر ذاكرة الزمن ", "price": 25, "original_price": 30, "images": ["m/section2a.jpg", "m/section2a2.jpg","m/section2a3.jpg" ,"m/section2a4.jpg" ,"m/section2a5.jpg" , "m/section2a6.jpg" ,"m/section2a7.jpg" ,"m/section2a8.jpg" ,"m/section2a9.jpg"],"description":"الحجم : A5 - مخصص لتنظيم دراسة مادة التاريخ مكون من ٣ أقسام (قسم التواريخ، الشخصيات، الملاحظات) "},
    {"id": 105, "name": "دفتر خُطى النجاح", "price": 30, "images": ["m/section2b.jpg", "m/section2b2.jpg" ,"m/section2b3.jpg" ,"m/section2b4.jpg","m/section2b5.jpg" ,"m/section2b6.jpg"],"description":" الحجم : A5 - منظم دراسي  "},
    {"id": 106, "name": "دفتر حُلمي أن أحفظ القرآن الكريم", "price": 20, "images": ["m/section2d.jpg", "m/section2d2.jpg","m/section2d3.jpg", "m/section2d4.jpg", "m/section2d5.jpg" ,"m/section2d6.jpg" ,"m/section2d7.jpg","m/section2d8.jpg"],"description":"الحجم :A5 - مصمم ليكون أداة تشجيع وتحفيز تجعل الحفظ ممتع ومنظم لطفلك، يحتوي على جدول مرن لحفظ السور والآيات، بالإضافة إلى أنشطة ممتعة تعزز الفهم والتعلم. "},
    {"id": 107 ,"name": "مفكرة ما دام الأمل طريقاً فسنحياه","price": 65 , "original_price": 75,"images": ["m/section2e.jpg","m/section2e2.jpg","m/section2e3.jpg","m/section2e4.jpg","m/section2e5.jpg","m/section2e6.jpg","m/section2e7.jpg","m/section2e8.jpg","m/section2e9.jpg"],
  "description": "مفكرة يومية مصممة لتكون عملية ومريحة وتساعدك على تنظيم يومك بدون ضغط والالتزام بروتين جديد يطّور حياتك.\n\nتشكل:\n• صفحات يومية لتنظيم المهام، العادات الصحية والدينية، وروتينك الصباحي والمسائي\n• مساحة شخصية يومية للتفريغ، الامتنان، والأفكار\n• صفحات شهرية لمهامك وتحدّي شهري مع تتبّع\n• اقتباسات شهرية محفّزة ترافقك طول الطريق\n\n🤍 توابعها:\nفاصل كتب + ورقة Vision Board حجم A3 تضيفي عليها صور وأحلامك لتكون قدّام عينك دايماً\n\nتفاصيل سريعة:\nالحجم A5 | تغطي 5 أشهر | متوفرة باللون الزهري والبيج | بتوصلك بغلاف خاص بقرطاس"
  , "colors": [
    {"name": "زهري", "code": "#d8a1a2"},
    {"name": "بيج", "code": "#cfc194"},]},
    {"id": 112, "name": "بكيت هايلايتر - 6 ألوان", "price": 15,  "images": ["h/section4a.jpg", "h/section4.jpg"],"description":"بكيت هايلايتر - 6 ألوان"},
    {"id": 113, "name": "بكيت هايلايتر - 4 ألوان", "price": 8, "images": ["h/section4b2.jpg", "h/section4b.jpg"],"description":" بكيت هايلايتر - 4 ألوان"},
    {"id": 114, "name": "بكيت هايلايتر - ألوان", "price": 15, "images": ["h/section4d2.jpg", "h/section4d.jpg"],"description":"بكيت هايلايتر - ألوان"},
    {"id": 115, "name": "هايلايتر ", "price": 2, "images": [ "h/section4f2.jpg","h/section4f1.jpg"],"colors": [
    {"name": "بنفسجي 1", "code": "#361f63"},
    {"name": "بنفسجي 2", "code": "#7a7ac0"},
    {"name": "بنفسجي 3", "code": "#888a97"},
    {"name": "بنفسجي 4", "code": "#b197be"},]},
    {"id": 116, "name": "هايلايتر ", "price": 2, "images": [ "h/section4j.jpg","h/section4j1.jpg","h/section4j2.jpg"],"colors": [
    {"name": "اصفر 1", "code": "#e2bf57"},
    {"name": "اصفر 2", "code": "#d0df00"},
    {"name": "اصفر 3", "code": "#a6af73"},]},
    {"id": 117, "name": "هايلايتر ", "price": 2, "images": [ "h/section4k.jpg","h/section4k1.jpg","h/section4k2.jpg"],"colors": [
    {"name": "زهري 1", "code": "#c97b89"},
    {"name": "زهري 2", "code": "#967774"},
    {"name": "زهري 3", "code": "#fe1683"},
    {"name": "زهري 4", "code": "#955053"},]},
    {"id": 118, "name": "هايلايتر ", "price": 2, "images": [ "h/section4l.jpg","h/section4l1.jpg"],"colors": [
    {"name": "برتقالي مُحمر", "code": "#fe2327"},
    {"name": "برتقالي ", "code": "#ff562f"},
    {"name": "قرميدي", "code": "#d06752"},]},
    {"id": 119, "name": "هايلايتر ", "price": 2, "images": [ "h/section4m.jpg","h/section4m1.jpg"],"colors": [
    {"name": "اخضر 1", "code": "#00a547"},
    {"name": "اخضر 2", "code": "#6bc19c"},
    {"name": "اخضر 3", "code": "#a9c386"},
    {"name": "اخضر 4", "code": "#7c6f54"},]},
    {"id": 120, "name": "هايلايتر ", "price": 2, "images": [ "h/section4n.jpg"],"colors": [
    {"name": "ازرق", "code": "#007b9c"},
    {"name": "اخضر ", "code": "#44b47c"},]},
    {"id": 121, "name": "هايلايتر ", "price": 2, "images": [ "h/section4o.jpg","h/section4o1.jpg","h/section4o2.jpg"],"colors": [
    {"name": "اخضر 1", "code": "#57b895"},
    {"name": "برتقالي", "code": "#da964d"},
    {"name": "اخضر 2", "code": "#5eae73"},]},
    {"id": 122, "name": "قلم حبر سائل", "price": 3.5, "images": ["h/section4e.jpg"],"description":"قلم حبر سائل - لون الحبر أسود","colors": [
    {"name": "زهري 1", "code": "#dbcfc1"},
    {"name": "زهري 2", "code": "#c48888"},
    {"name": "بنفسجي 1", "code": "#c2c1bf"},
    {"name": "بنفسجي 2", "code": "#c7b3bf"},
    {"name": "ازرق 1", "code": "#90b7b6"},
    {"name": "ازرق 2", "code": "#58819b"},
    {"name": "اخضر 1", "code": "#c2dfc2"},
    {"name": "اخضر 2", "code": "#6e8f58"},]},
    {"id": 123, "name": "قلم رصاص مع بريات", "price": 4, "images": ["h/section4p.jpg"]},
    {"id": 124, "name": "أقلام رصاص لا نهائية الاستخدام", "price": 2, "images": ["h/section4t1.jpg","h/section4t.jpg"],"colors": [
    {"name": "اصفر 1", "code": "#f6b910"},
    {"name": "احمر", "code": "#af0001"},
    {"name": "اسود", "code": "#030609"},
    {"name": "كحلي", "code": "#010e51"},
    {"name": "اصفر 2", "code": "#e5db9d"},
    {"name": "اصفر 3", "code": "#acf51f"},]},
    
    {"id": 108, "name": "دفتر هارد كڤر", "price": 17,  "images": ["d/section3.jpg", "d/section3a.jpg"],"description":"الحجم : A5 - الورق الداخلي مسطر "},
    {"id": 109, "name": "دفتر هارد كڤر", "price": 17, "images": ["d/section3b.jpg", "d/section3b2.jpg"],"description":" الحجم : A5 -  الورق الداخلي مسطر  "},
    {"id": 110, "name": "دفتر هارد كڤر مع آلة حاسبة", "price": 19, "images": ["d/section3d.jpg", "d/section3d2.jpg","d/section3d3.jpg"],"description":"الحجم :A5 - الورق الداخلي مسطر", "colors": [
    {"name": "زهري", "code": "#d99ebc"},
    {"name": "بُني", "code": "#b3814c"},
    {"name": "أزرق", "code": "#a1bfc9"},]},
    {"id": 111, "name": "دفتر هارد كڤر مع آلة حاسبة", "price": 15, "images": [ "d/section3d4.jpg"],"description":"الحجم : صغير - الورق الداخلي مسطر"},
    ] 

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/section1')
def section1():
    favorites = session.get("favorites", [])
    products = get_products_by_category('section1')
    return render_template("section1.html", products=products, favorites=favorites)
 

@app.route('/section2')
def section2():
    favorites = session.get("favorites", [])
    products = get_products_by_category('section2')
    return render_template("section2.html", products=products, favorites=favorites)

@app.route('/section3')
def section3():
    favorites = session.get("favorites", [])
    products = get_products_by_category('section3')
    return render_template("section3.html", products=products, favorites=favorites)

@app.route('/section4')
def section4():
    favorites = session.get("favorites", [])
    products = get_products_by_category('section4')
    return render_template("section4.html", products=products, favorites=favorites)

@app.route('/section5')
def section5():
    favorites = session.get("favorites", [])
    products = get_products_by_category('section5')
    return render_template("section5.html", products=products, favorites=favorites)

@app.route('/section6')
def section6():
    favorites = session.get("favorites", [])
    products = get_products_by_category('section6')
    return render_template("section6.html", products=products, favorites=favorites)

@app.route('/section7')
def section7():
    favorites = session.get("favorites", [])
    products = get_products_by_category('section7')
    return render_template("section7.html", products=products, favorites=favorites)

@app.route('/section8')
def section8():
    favorites = session.get("favorites", [])
    products = get_products_by_category('section8')
    return render_template("section8.html", products=products, favorites=favorites)



@app.route("/toggle_favorite/<int:product_id>")
def toggle_favorite(product_id):
    favorites = session.get("favorites", [])
    if product_id in favorites:
        favorites.remove(product_id)
    else:
        favorites.append(product_id)
    session["favorites"] = favorites
    return redirect(request.referrer)

@app.route("/details/<int:product_id>")
def details(product_id):
    product = get_product(product_id)
    need_color = request.args.get('need_color') == '1'
    attachment_error = request.args.get('attachment_error', '')
    return render_template(
        "details.html",
        product=product,
        need_color=need_color,
        attachment_error=attachment_error,
    )
    
@app.route('/favorites')
def favorites():
    fav_ids = session.get('favorites', [])
    fav_products = [get_product(pid) for pid in fav_ids if get_product(pid)]
    return render_template('favorites.html', products=fav_products)

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    cart_items = []
    total = 0

    # group cart keys by product id -> aggregate colors and quantities
    grouped = {}
    for key, cart_value in cart.items():
        if '|' in str(key):
            pid_str, color_name = str(key).split('|', 1)
        else:
            pid_str, color_name = str(key), None
        if not pid_str.isdigit():
            continue
        pid = int(pid_str)
        product = get_product(pid)
        if not product:
            continue

        group = grouped.setdefault(pid, {
            'product': product,
            'colors': {},
            'quantity': 0,
            'subtotal': 0,
            'image': product['images'][0],
            'attachment': None,
        })

        if isinstance(cart_value, dict):
            qty = cart_value.get('quantity', 1)
            if cart_value.get('attachment'):
                group['attachment'] = cart_value.get('attachment')
        else:
            qty = cart_value

        group['quantity'] += qty
        group['colors'][color_name] = group['colors'].get(color_name, 0) + qty

    # convert grouped to cart_items list with color codes and subtotals
    for pid, g in grouped.items():
        product = g['product']
        item = product.copy()
        item['id'] = product['id']
        item['quantity'] = g['quantity']
        item['image'] = g['image']
        # build colors list
        colors_list = []
        for cname, cqty in g['colors'].items():
            if cname:
                code = next((c.get('code') for c in product.get('colors', []) if c.get('name') == cname), None)
            else:
                code = None
            colors_list.append({'name': cname, 'code': code, 'quantity': cqty})
        item['colors'] = colors_list
        item['subtotal'] = item['price'] * item['quantity']
        total += item['subtotal']
        cart_items.append(item)

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total
    )


@app.route('/add-to-cart/<int:product_id>', methods=['GET', 'POST'])
def add_to_cart(product_id):
    product = get_product(product_id)
    if not product:
        return redirect(url_for('home'))

    attachment_required = is_attachment_required(product_id)
    if request.method == 'GET' and attachment_required:
        return redirect(
            url_for('details', product_id=product_id, attachment_error='المنتج يحتاج صورة لإكمال الشراء.')
        )

    colors_param = request.form.get('colors', '').strip() if request.method == 'POST' else request.args.get('colors', '').strip()
    single_color = request.form.get('color', '').strip() if request.method == 'POST' else request.args.get('color', '').strip()
    cart = session.get('cart', {})
    attachment_filename = None

    if attachment_required:
        attachment = request.files.get('attachment')
        if not attachment or attachment.filename == '':
            return redirect(
                url_for('details', product_id=product_id, attachment_error='من فضلك أرفق صورة قبل الشراء.')
            )
        filename = secure_filename(f"{uuid.uuid4().hex}_{attachment.filename}")
        attachment.save(os.path.join(UPLOAD_FOLDER, filename))
        attachment_filename = filename

    # helper to add one color entry
    def add_one(color_name):
        key = f"{product_id}|{color_name}"
        existing = cart.get(key, 0)
        if isinstance(existing, dict):
            qty = existing.get('quantity', 0) + 1
            cart[key] = {
                'quantity': qty,
                'color': color_name,
                'attachment': attachment_filename or existing.get('attachment')
            }
        else:
            cart[key] = {
                'quantity': 1,
                'color': color_name,
                'attachment': attachment_filename
            }

    if colors_param:
        colors = [c.strip() for c in colors_param.split(',') if c.strip()]
        if not colors:
            return redirect(url_for('details', product_id=product_id, need_color=1))
        for c in colors:
            add_one(c)
    elif single_color:
        add_one(single_color)
    else:
        key = str(product_id)
        existing = cart.get(key, 0)
        if isinstance(existing, dict):
            qty = existing.get('quantity', 0) + 1
            cart[key] = {
                'quantity': qty,
                'attachment': attachment_filename or existing.get('attachment')
            }
        else:
            if attachment_required:
                cart[key] = {
                    'quantity': 1,
                    'attachment': attachment_filename
                }
            else:
                cart[key] = existing + 1 if existing else 1

    session['cart'] = cart
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/increase_qty/<int:product_id>')
def increase_qty(product_id):
    cart = session.get('cart', {})
    pid = str(product_id)
    color = request.args.get('color', '').strip()
    key = f"{pid}|{color}" if color else pid
    if key in cart:
        item = cart[key]
        if isinstance(item, dict):
            item['quantity'] = item.get('quantity', 0) + 1
            cart[key] = item
        else:
            cart[key] = item + 1
        session['cart'] = cart
        session.modified = True
    return redirect(url_for('cart'))


@app.route('/increase_total/<int:product_id>')
def increase_total(product_id):
    cart = session.get('cart', {})
    pid = str(product_id)
    # prefer to increment first color variant if exists
    variant_key = None
    for k in list(cart.keys()):
        if k.startswith(pid + '|'):
            variant_key = k
            break
    if variant_key:
        item = cart[variant_key]
        if isinstance(item, dict):
            item['quantity'] = item.get('quantity', 0) + 1
            cart[variant_key] = item
        else:
            cart[variant_key] = item + 1
    else:
        existing = cart.get(pid, 0)
        cart[pid] = existing + 1 if existing else 1
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/decrease_qty/<int:product_id>')
def decrease_qty(product_id):
    cart = session.get('cart', {})
    pid = str(product_id)
    color = request.args.get('color', '').strip()
    key = f"{pid}|{color}" if color else pid
    if key in cart:
        item = cart[key]
        if isinstance(item, dict):
            item['quantity'] = item.get('quantity', 1) - 1
            if item['quantity'] <= 0:
                cart.pop(key, None)
            else:
                cart[key] = item
        else:
            cart[key] -= 1
            if cart[key] <= 0:
                cart.pop(key, None)
        session['cart'] = cart
        session.modified = True
    return redirect(url_for('cart'))


@app.route('/decrease_total/<int:product_id>')
def decrease_total(product_id):
    cart = session.get('cart', {})
    pid = str(product_id)
    # prefer to decrement last color variant if exists
    variant_key = None
    for k in list(cart.keys())[::-1]:
        if k.startswith(pid + '|'):
            variant_key = k
            break
    key = variant_key if variant_key else pid
    if key in cart:
        item = cart[key]
        if isinstance(item, dict):
            item['quantity'] = item.get('quantity', 1) - 1
            if item['quantity'] <= 0:
                cart.pop(key, None)
            else:
                cart[key] = item
        else:
            cart[key] -= 1
            if cart[key] <= 0:
                cart.pop(key, None)
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/remove-from-cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    color = request.args.get('color', '').strip()
    pid = str(product_id)
    key = f"{pid}|{color}" if color else pid
    if key in cart:
        cart.pop(key, None)
        session['cart'] = cart
        session.modified = True
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', {})
    cart_items = []
    total = 0

    # group cart keys by product id -> aggregate colors and quantities (same as /cart)
    grouped = {}
    for key, cart_value in cart.items():
        if '|' in str(key):
            pid_str, color_name = str(key).split('|', 1)
        else:
            pid_str, color_name = str(key), None
        if not pid_str.isdigit():
            continue
        pid = int(pid_str)
        product = get_product(pid)
        if not product:
            continue

        group = grouped.setdefault(pid, {
            'product': product,
            'colors': {},
            'quantity': 0,
            'subtotal': 0,
            'image': product['images'][0],
            'attachment': None,
        })

        if isinstance(cart_value, dict):
            qty = cart_value.get('quantity', 1)
            if cart_value.get('attachment'):
                group['attachment'] = cart_value.get('attachment')
        else:
            qty = cart_value

        group['quantity'] += qty
        group['colors'][color_name] = group['colors'].get(color_name, 0) + qty

    # convert grouped to cart_items list with color codes and subtotals
    for pid, g in grouped.items():
        product = g['product']
        item = product.copy()
        item['id'] = product['id']
        item['quantity'] = g['quantity']
        item['image'] = g['image']
        item['attachment'] = g.get('attachment')   # إضافة صورة الزبون للطلب

# build colors list
        # build colors list
        colors_list = []
        for cname, cqty in g['colors'].items():
            if cname:
                code = next((c.get('code') for c in product.get('colors', []) if c.get('name') == cname), None)
            else:
                code = None
            colors_list.append({'name': cname, 'code': code, 'quantity': cqty})
        item['colors'] = colors_list
        item['subtotal'] = item['price'] * item['quantity']
        total += item['subtotal']
        cart_items.append(item)

    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        customer_phone = request.form.get('customer_phone', '').strip()
        customer_address = request.form.get('customer_address', '').strip()
        payment_method = request.form.get('payment_method', '').strip()
        delivery_region = request.form.get('delivery_region', '').strip()
        order_notes = request.form.get('order_notes', '').strip()
        
        # Calculate shipping fee based on delivery region
        shipping_fee = get_region_shipping_fee(delivery_region)
        final_total = total + shipping_fee

        save_order({
        'customer_name': customer_name,
        'customer_phone': customer_phone,
        'customer_address': customer_address,
        'payment_method': payment_method,
        'delivery_region': delivery_region,
        'order_notes': order_notes,
        'total': total,
        'shipping_fee': shipping_fee,
        'final_total': final_total,
        'items': cart_items
        }, cart_items)

        session.pop('cart', None)
        session.modified = True

        return render_template(
            'checkout_success.html',
            total=total,
            shipping_fee=shipping_fee,
            final_total=final_total,
            cart_items=cart_items,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
            payment_method=payment_method,
            delivery_region=delivery_region,
            order_notes=order_notes,
        )

    return render_template('checkout.html', cart_items=cart_items, total=total)


@app.route('/admin')
def admin_login_page():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html', message=request.args.get('message', ''))


@app.route('/admin/login', methods=['POST'])
def admin_login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
        session['admin_logged_in'] = True
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login_page', message='اسم المستخدم أو كلمة المرور غير صحيحة'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login_page'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    conn = get_db()
    product_count = conn.execute('SELECT COUNT(*) as count FROM products').fetchone()['count']
    order_count = conn.execute('SELECT COUNT(*) as count FROM orders').fetchone()['count']
    recent_orders = conn.execute('SELECT * FROM orders ORDER BY order_id DESC LIMIT 5').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', product_count=product_count, order_count=order_count, recent_orders=recent_orders)


@app.route('/admin/orders', methods=['GET', 'POST'])
@login_required
def admin_orders():
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        new_status = request.form.get('status')
        conn = get_db()
        conn.execute(
            'UPDATE orders SET status = ? WHERE order_id = ?',
            (new_status, order_id)
        )
        conn.commit()
        conn.close()

    conn = get_db()
    orders = conn.execute(
        'SELECT * FROM orders ORDER BY order_id DESC'
    ).fetchall()

    orders_with_items = []

    for order in orders:
        order = dict(order)

        try:
            order['items'] = json.loads(order['items_json'])
        except:
            order['items'] = []

        orders_with_items.append(order)

    conn.close()

    return render_template(
        'admin_orders.html',
        orders=orders_with_items
    )

@app.route('/admin/products', methods=['GET', 'POST'])
@login_required
def admin_products():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = float(request.form.get('price', 0) or 0)
        original_price = request.form.get('original_price', '').strip()
        original_price = float(original_price) if original_price else None
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'general').strip()
        uploaded_images = []
        for file in request.files.getlist('images'):
            if file and file.filename:
                filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
                file.save(os.path.join(PRODUCT_IMAGE_FOLDER, filename))
                uploaded_images.append(filename)
        if name:
            requires_attachment = 1 if request.form.get('requires_attachment') else 0

            conn = get_db()

        conn.execute(
    '''
    INSERT INTO products 
    (name, price, original_price, description, category, images, colors, requires_attachment, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''',
    (
        name,
        price,
        original_price,
        description,
        category,
        json.dumps(uploaded_images or ['default.jpg'], ensure_ascii=False),
        '[]',
        requires_attachment,
        'active'
    )
)
        conn.commit()
        conn.close()
    conn = get_db()
    products = conn.execute('SELECT * FROM products ORDER BY product_id DESC').fetchall()
    conn.close()
    return render_template('admin_products.html', products=products)


init_db()

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):

    conn = get_db()

    product = conn.execute(
        'SELECT * FROM products WHERE product_id = ?',
        (product_id,)
    ).fetchone()

    if not product:
        conn.close()
        return redirect(url_for('admin_products'))


    if request.method == 'POST':

        name = request.form.get('name', '').strip()

        price = float(
            request.form.get('price', 0) or 0
        )


        original_price = request.form.get(
            'original_price',
            ''
        ).strip()

        original_price = (
            float(original_price)
            if original_price else None
        )


        description = request.form.get(
            'description',
            ''
        ).strip()


        category = request.form.get(
            'category',
            'general'
        ).strip()


        # ✅ الألوان الجديدة
        colors = request.form.get(
            'colors',
            '[]'
        )


        # ✅ هل يحتاج صورة من الزبون؟
        requires_attachment = 1 if request.form.get(
            'requires_attachment'
        ) else 0



        # الصور القديمة
        old_images = json.loads(
            product['images']
        ) if product['images'] else []


        # الصور الجديدة
        uploaded_images = []

        for file in request.files.getlist('images'):

            if file and file.filename:

                filename = secure_filename(
                    f"{uuid.uuid4().hex}_{file.filename}"
                )

                file.save(
                    os.path.join(
                        PRODUCT_IMAGE_FOLDER,
                        filename
                    )
                )

                uploaded_images.append(filename)



        if uploaded_images:
            images = uploaded_images
        else:
            images = old_images



        conn.execute(
            '''
            UPDATE products
            SET name=?,
                price=?,
                original_price=?,
                description=?,
                category=?,
                images=?,
                colors=?,
                requires_attachment=?
            WHERE product_id=?
            ''',
            (
                name,
                price,
                original_price,
                description,
                category,
                json.dumps(
                    images,
                    ensure_ascii=False
                ),
                colors,
                requires_attachment,
                product_id
            )
        )


        conn.commit()
        conn.close()

        return redirect(
            url_for('admin_products')
        )


    conn.close()

    return render_template(
        'edit_product.html',
        product=product
    )
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))

        return f(*args, **kwargs)

    return decorated_function

@app.route('/admin/delete-product/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM products WHERE product_id = ?",
        (product_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for('admin_products'))

@app.route('/admin/product/<int:product_id>/delete-image/<image_name>')
@admin_required
def delete_product_image(product_id, image_name):

    conn = get_db()

    product = conn.execute(
        "SELECT images FROM products WHERE product_id=?",
        (product_id,)
    ).fetchone()

    if not product:
        conn.close()
        return redirect(url_for('admin_products'))

    images = json.loads(product["images"] or "[]")

    # حذف الصورة من القائمة
    if image_name in images:
        images.remove(image_name)

        # حذف الملف من المجلد
        image_path = os.path.join(
            app.static_folder,
            "images",
            image_name
        )

        if os.path.exists(image_path):
            os.remove(image_path)

        # تحديث قاعدة البيانات
        conn.execute(
            "UPDATE products SET images=? WHERE product_id=?",
            (json.dumps(images), product_id)
        )
        conn.commit()

    conn.close()

    flash("تم حذف الصورة بنجاح")

    return redirect(
        url_for(
            "edit_product",
            product_id=product_id
        )
    )
@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return json.loads(value)
    except:
        return []
if __name__ == '__main__':
    app.run(debug=True)
