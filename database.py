import sqlite3
import os

# Lokasi database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "laboratorium.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    # ==========================================
    # TABEL USERS
    # ==========================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # ==========================================
    # TABEL BARANG
    # ==========================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS barang (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_barang TEXT NOT NULL,
            kategori TEXT NOT NULL,
            stok INTEGER NOT NULL,
            kondisi TEXT NOT NULL
        )
    """)

    # ==========================================
    # TABEL PEMINJAMAN
    # ==========================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS peminjaman (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nama_mahasiswa TEXT NOT NULL,
            nim TEXT NOT NULL,
            no_whatsapp TEXT NOT NULL,

            tanggal_pinjam TEXT NOT NULL,
            tenggat_kembali TEXT NOT NULL,
            tanggal_kembali TEXT,

            status TEXT NOT NULL
        )
    """)

    # ==========================================
    # TABEL DETAIL PEMINJAMAN
    # ==========================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS detail_peminjaman (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            peminjaman_id INTEGER NOT NULL,
            barang_id INTEGER NOT NULL,
            jumlah INTEGER NOT NULL,

            FOREIGN KEY (peminjaman_id)
            REFERENCES peminjaman(id),

            FOREIGN KEY (barang_id)
            REFERENCES barang(id)
        )
    """)

    # ==========================================
    # AKUN ADMIN
    # ==========================================

    admin = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        ("admin",)
    ).fetchone()

    if admin is None:

        conn.execute("""
            INSERT INTO users
            (nama, username, password, role)
            VALUES (?, ?, ?, ?)
        """, (
            "Administrator",
            "admin",
            "admin123",
            "admin"
        ))

    conn.commit()
    conn.close()