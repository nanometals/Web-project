# Nano Metals Trading Website

A deployable Flask + SQLite website built from the supplied Nano Metals Trading HTML design.

## Included
- Korean public website
- Daily metal prices loaded from the database
- Customer inquiry popup
- Up to 5 product/scrap image uploads
- Customer inquiry database
- Password-protected admin dashboard
- Price editing
- Inquiry status management
- Company phone, KakaoTalk, email and address settings

## Local setup (Windows / macOS / Linux)

1. Install Python 3.11 or newer.
2. Open a terminal in this folder.
3. Create a virtual environment:

   Windows:
   `python -m venv .venv`
   `.venv\\Scripts\\activate`

   macOS/Linux:
   `python3 -m venv .venv`
   `source .venv/bin/activate`

4. Install packages:
   `pip install -r requirements.txt`

5. Set environment variables.

   Windows PowerShell:
   `$env:SECRET_KEY="a-long-random-secret"`
   `$env:ADMIN_PASSWORD="your-strong-admin-password"`

   macOS/Linux:
   `export SECRET_KEY="a-long-random-secret"`
   `export ADMIN_PASSWORD="your-strong-admin-password"`

6. Run:
   `python app.py`

7. Open:
   Website: `http://127.0.0.1:5000`
   Admin: `http://127.0.0.1:5000/admin`

## Production security
- Do not use the example SECRET_KEY.
- Use a strong administrator password.
- Prefer ADMIN_PASSWORD_HASH instead of ADMIN_PASSWORD.
- Put the website behind HTTPS.
- Back up `data/nanometals.db` and `uploads/`.
- For multi-server deployment, replace SQLite/local uploads with a managed database and object storage.

## Domain deployment
The application can be deployed to any host that runs Python/WSGI.
Production start command:
`gunicorn app:app --bind 0.0.0.0:$PORT`

After deployment:
1. Add `nanometaltrading.co.kr` as a custom domain at the hosting provider.
2. Copy the DNS records supplied by the hosting provider into the domain DNS manager.
3. Also add `www.nanometaltrading.co.kr` if desired.
4. Enable/verify SSL/HTTPS.
5. Open `/admin`, enter the admin password, then fill company phone, KakaoTalk URL, email and address.
6. Submit a test inquiry with a photo and verify that it appears in the admin dashboard.

## Important hosting note
The current build stores the database and uploaded photos on disk. Use persistent disk/storage on the host. If the host has an ephemeral filesystem, data can disappear after a redeploy/restart.
