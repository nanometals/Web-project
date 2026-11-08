import os
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv('DATA_DIR', BASE_DIR / 'data'))
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', BASE_DIR / 'uploads'))
DB_PATH = Path(os.getenv('DB_PATH', DATA_DIR / 'nanometals.db'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'heic'}
MAX_FILES = 5

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-me-before-production')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            price TEXT NOT NULL,
            unit TEXT DEFAULT '/kg',
            note TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT DEFAULT '',
            phone TEXT NOT NULL,
            email TEXT DEFAULT '',
            region TEXT DEFAULT '',
            inquiry_type TEXT DEFAULT '',
            metal_type TEXT DEFAULT '',
            amount TEXT DEFAULT '',
            message TEXT DEFAULT '',
            files TEXT DEFAULT '',
            status TEXT DEFAULT 'New',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    ''')

    count = conn.execute('SELECT COUNT(*) AS c FROM prices').fetchone()['c']
    if count == 0:
        now = datetime.now().isoformat(timespec='seconds')
        seed = [
            ('special','폐초경 · 엔드밀','₩100,000','/kg','예시 단가',1),
            ('special','폐초경 · 인서트','₩80,000','/kg','예시 단가',2),
            ('special','하이스','₩8,000','/kg','예시 단가',3),
            ('special','하이스 분철','₩6,000','/kg','예시 단가',4),
            ('special','티타늄','₩2,000','/kg','예시 단가',5),
            ('special','주석 바','₩50,000','/kg','예시 단가',6),
            ('special','몰리브덴','₩55,000','/kg','예시 단가',7),
            ('special','순수 니켈','₩19,500','/kg','예시 단가',8),
            ('precious','금 (Gold)','문의','/g','실시간 단가 확인',1),
            ('precious','은 (Silver)','문의','/kg','실시간 단가 확인',2),
            ('precious','백금 (Platinum)','문의','/g','실시간 단가 확인',3),
            ('precious','팔라듐 (Palladium)','문의','/g','실시간 단가 확인',4),
            ('trading','구리','문의','/kg','시장 단가 기준',1),
            ('trading','황동','문의','/kg','시장 단가 기준',2),
            ('trading','알루미늄','문의','/kg','시장 단가 기준',3),
            ('trading','스테인리스','₩1,700','/kg','예시 단가',4),
            ('equipment','PVD 장비','견적 문의','','맞춤 설계·제작',1),
            ('equipment','진공 열증착 장비','견적 문의','','맞춤 설계·제작',2),
            ('equipment','소결로','견적 문의','','맞춤 설계·제작',3),
            ('equipment','특수 금속 회수장비','견적 문의','','상담 후 설계',4),
        ]
        conn.executemany('''INSERT INTO prices(category,name,price,unit,note,sort_order,updated_at)
                            VALUES(?,?,?,?,?,?,?)''', [(*row, now) for row in seed])

    defaults = {
        'company_name': 'NANO METALS TRADING',
        'company_name_ko': '나노메탈스 트레이딩',
        'phone': '',
        'kakao_url': '',
        'contact_email': '',
        'address': '',
    }
    for key, value in defaults.items():
        conn.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)', (key, value))
    conn.commit()
    conn.close()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return fn(*args, **kwargs)
    return wrapper


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_settings():
    conn = get_db()
    rows = conn.execute('SELECT key,value FROM settings').fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}


@app.route('/')
def index():
    return render_template('index.html', settings=get_settings())


@app.route('/api/prices')
def api_prices():
    conn = get_db()
    rows = conn.execute('SELECT id,category,name,price,unit,note,updated_at FROM prices ORDER BY category,sort_order,id').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.post('/api/inquiries')
def api_inquiries():
    form = request.form
    name = form.get('name', '').strip()
    phone = form.get('phone', '').strip()
    if not name or not phone:
        return jsonify({'ok': False, 'message': '성명과 연락처는 필수입니다.'}), 400

    saved_files = []
    incoming = request.files.getlist('photos')[:MAX_FILES]
    for f in incoming:
        if not f or not f.filename:
            continue
        if not allowed_file(f.filename):
            return jsonify({'ok': False, 'message': '이미지는 JPG, PNG, WEBP, HEIC 형식만 업로드할 수 있습니다.'}), 400
        safe = secure_filename(f.filename)
        ext = safe.rsplit('.', 1)[1].lower()
        stored = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:10]}.{ext}"
        f.save(UPLOAD_DIR / stored)
        saved_files.append(stored)

    conn = get_db()
    conn.execute('''INSERT INTO inquiries
        (name,company,phone,email,region,inquiry_type,metal_type,amount,message,files,status,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''', (
        name,
        form.get('company','').strip(),
        phone,
        form.get('email','').strip(),
        form.get('region','').strip(),
        form.get('inquiry_type','').strip(),
        form.get('metal_type','').strip(),
        form.get('amount','').strip(),
        form.get('message','').strip(),
        ','.join(saved_files),
        'New',
        datetime.now().isoformat(timespec='seconds')
    ))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'message': '문의가 등록되었습니다.'})


@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        supplied = request.form.get('password', '')
        admin_hash = os.getenv('ADMIN_PASSWORD_HASH', '')
        admin_password = os.getenv('ADMIN_PASSWORD', '')
        valid = check_password_hash(admin_hash, supplied) if admin_hash else (admin_password and supplied == admin_password)
        if valid:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('비밀번호가 올바르지 않습니다.', 'error')
    return render_template('admin_login.html')


@app.post('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin')
@login_required
def admin_dashboard():
    conn = get_db()
    inquiries = conn.execute('SELECT * FROM inquiries ORDER BY id DESC').fetchall()
    prices = conn.execute('SELECT * FROM prices ORDER BY category,sort_order,id').fetchall()
    conn.close()
    return render_template('admin.html', inquiries=inquiries, prices=prices, settings=get_settings())


@app.post('/admin/prices/<int:price_id>')
@login_required
def admin_update_price(price_id):
    conn = get_db()
    conn.execute('''UPDATE prices SET name=?,price=?,unit=?,note=?,updated_at=? WHERE id=?''', (
        request.form.get('name','').strip(),
        request.form.get('price','').strip(),
        request.form.get('unit','').strip(),
        request.form.get('note','').strip(),
        datetime.now().isoformat(timespec='seconds'),
        price_id
    ))
    conn.commit(); conn.close()
    flash('단가가 수정되었습니다.', 'success')
    return redirect(url_for('admin_dashboard') + '#prices')


@app.post('/admin/inquiries/<int:inquiry_id>/status')
@login_required
def admin_update_status(inquiry_id):
    status = request.form.get('status', 'New')
    if status not in {'New','Contacted','Quoted','Completed','Cancelled'}:
        status = 'New'
    conn = get_db(); conn.execute('UPDATE inquiries SET status=? WHERE id=?', (status, inquiry_id)); conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard'))


@app.post('/admin/settings')
@login_required
def admin_settings():
    allowed = {'company_name','company_name_ko','phone','kakao_url','contact_email','address'}
    conn = get_db()
    for key in allowed:
        conn.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, request.form.get(key,'').strip()))
    conn.commit(); conn.close()
    flash('회사 정보가 저장되었습니다.', 'success')
    return redirect(url_for('admin_dashboard') + '#settings')


@app.route('/admin/uploads/<path:filename>')
@login_required
def admin_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.cli.command('hash-password')
def hash_password():
    import getpass
    print(generate_password_hash(getpass.getpass('Admin password: ')))


init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=os.getenv('FLASK_DEBUG') == '1')
