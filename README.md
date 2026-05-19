# SIGAROB — Backend (Flask)

Sistem Prediksi Banjir Rob, Kabupaten Indramayu.

---

## Struktur File

```
backend/
├── run.py                      # Entry point
├── requirements.txt
├── .env.example                # Template konfigurasi env
└── app/
    ├── __init__.py             # App factory + inisialisasi extensions
    ├── config.py               # Konfigurasi per environment
    ├── commands.py             # CLI commands (seed-admin, create-tables)
    ├── api/
    │   ├── __init__.py
    │   └── auth.py             # Blueprint: /api/auth/*
    ├── models/
    │   ├── __init__.py
    │   ├── user.py             # Model tabel `users`
    │   └── config.py           # Model tabel config & wa_recipients (stub FK)
    ├── services/
    │   ├── __init__.py
    │   └── auth_service.py     # Logika bisnis autentikasi
    └── utils/
        ├── __init__.py
        ├── responses.py        # Helper respons JSON + decorator require_role
        └── validators.py       # Schema validasi input (marshmallow)
```

---

## Setup

**1. Buat virtual environment & install dependencies**
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Konfigurasi environment**
```bash
cp .env.example .env
# Edit .env — isi DB_PASSWORD, SECRET_KEY, JWT_SECRET_KEY
```

**3. Buat tabel & seed admin pertama**
```bash
flask --app run create-tables
flask --app run seed-admin
# Masukkan username dan password admin saat diminta
```

**4. Jalankan server**
```bash
flask --app run run
# atau:
python run.py
```

---

## API Endpoints

### `POST /api/auth/login`
Login dan dapatkan JWT token.

**Request Body:**
```json
{ "username": "admin", "password": "password123" }
```

**Response 200:**
```json
{
  "status": "success",
  "message": "Login berhasil.",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin",
      "is_active": true,
      "last_login": "2026-04-19T10:00:00"
    }
  }
}
```

**Response 401:**
```json
{ "status": "error", "error": "invalid_credentials", "message": "Username atau password salah." }
```

---

### `GET /api/auth/me`
Ambil profil user yang sedang login. Wajib kirim access token.

**Header:** `Authorization: Bearer <access_token>`

**Response 200:**
```json
{ "status": "success", "data": { "user": { ... } } }
```

---

### `POST /api/auth/refresh`
Perbarui access token menggunakan refresh token.

**Header:** `Authorization: Bearer <refresh_token>`

**Response 200:**
```json
{ "status": "success", "data": { "access_token": "eyJ..." } }
```

---

### `PUT /api/auth/change-password`
Ganti password. Wajib kirim access token.

**Header:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{ "old_password": "lama123", "new_password": "baru12345" }
```

---

### `POST /api/auth/logout`
Konfirmasi logout. Token dihapus di sisi klien (React).

**Header:** `Authorization: Bearer <access_token>`

---

## Role & Akses

| Role       | Keterangan                                                  |
|------------|-------------------------------------------------------------|
| `admin`    | Akses penuh: konfigurasi threshold, kelola akun & penerima WA |
| `operator` | Monitoring data + trigger notifikasi manual                 |

Gunakan decorator `@require_role("admin")` atau `@require_role("admin", "operator")` pada endpoint yang memerlukan pembatasan role.

---

## Format Respons

Semua endpoint menggunakan format JSON yang konsisten:

```json
{
  "status": "success" | "error",
  "message": "Pesan singkat",
  "data": { ... },      // hanya ada saat sukses
  "error": "kode_error" // hanya ada saat error
}
```
