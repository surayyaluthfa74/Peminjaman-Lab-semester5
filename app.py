from flask import Flask, render_template, request, redirect, url_for, session
from database import get_db, init_db
from datetime import date, datetime
from urllib.parse import quote

app = Flask(__name__)

app.secret_key = "kunci-rahasia-peminjaman-lab"

# Membuat database dan tabel
init_db()


# =========================================================
# LOGIN ADMIN
# =========================================================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE username = ?
            AND password = ?
            AND role = 'admin'
        """, (username, password)).fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["nama"] = user["nama"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Username atau password admin salah!"
        )

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    jumlah_barang = conn.execute("""
        SELECT COUNT(*)
        FROM barang
    """).fetchone()[0]

    total_stok = conn.execute("""
        SELECT COALESCE(SUM(stok), 0)
        FROM barang
    """).fetchone()[0]

    jumlah_peminjaman = conn.execute("""
        SELECT COUNT(*)
        FROM peminjaman
    """).fetchone()[0]

    peminjaman_aktif = conn.execute("""
        SELECT COUNT(*)
        FROM peminjaman
        WHERE status = 'Dipinjam'
    """).fetchone()[0]

    # Ambil semua peminjaman aktif
    data_peminjaman = conn.execute("""
        SELECT *
        FROM peminjaman
        WHERE status = 'Dipinjam'
        ORDER BY tenggat_kembali ASC
    """).fetchall()

    # Ambil barang untuk setiap peminjaman
    daftar_tenggat = []

    hari_ini = date.today()

    for data in data_peminjaman:

        detail_barang = conn.execute("""
            SELECT
                detail_peminjaman.jumlah,
                barang.nama_barang
            FROM detail_peminjaman
            JOIN barang
                ON detail_peminjaman.barang_id = barang.id
            WHERE detail_peminjaman.peminjaman_id = ?
        """, (data["id"],)).fetchall()

        tenggat = datetime.strptime(
            data["tenggat_kembali"],
            "%Y-%m-%d"
        ).date()

        selisih = (tenggat - hari_ini).days

        if selisih < 0:
            keterangan = "Terlambat"
        elif selisih == 0:
            keterangan = "Jatuh tempo hari ini"
        else:
            keterangan = f"{selisih} hari lagi"

        daftar_tenggat.append({
            "data": data,
            "barang": detail_barang,
            "keterangan": keterangan,
            "selisih": selisih
        })

    conn.close()

    return render_template(
        "dashboard.html",
        jumlah_barang=jumlah_barang,
        total_stok=total_stok,
        jumlah_peminjaman=jumlah_peminjaman,
        peminjaman_aktif=peminjaman_aktif,
        daftar_tenggat=daftar_tenggat
    )


# =========================================================
# DATA BARANG
# =========================================================

@app.route("/barang")
def barang():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    data_barang = conn.execute("""
        SELECT *
        FROM barang
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "barang.html",
        barang=data_barang
    )


# =========================================================
# TAMBAH BARANG
# =========================================================

@app.route("/barang/tambah", methods=["GET", "POST"])
def tambah_barang():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        nama_barang = request.form["nama_barang"]
        kategori = request.form["kategori"]
        stok = int(request.form["stok"])
        kondisi = request.form["kondisi"]

        conn = get_db()

        conn.execute("""
            INSERT INTO barang
            (nama_barang, kategori, stok, kondisi)
            VALUES (?, ?, ?, ?)
        """, (
            nama_barang,
            kategori,
            stok,
            kondisi
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("barang"))

    return render_template("tambah_barang.html", edit=False)


# =========================================================
# EDIT BARANG
# =========================================================

@app.route("/barang/edit/<int:id>", methods=["GET", "POST"])
def edit_barang(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    barang = conn.execute("""
        SELECT *
        FROM barang
        WHERE id = ?
    """, (id,)).fetchone()

    if barang is None:

        conn.close()

        return redirect(url_for("barang"))

    if request.method == "POST":

        nama_barang = request.form["nama_barang"]
        kategori = request.form["kategori"]
        stok = int(request.form["stok"])
        kondisi = request.form["kondisi"]

        conn.execute("""
            UPDATE barang
            SET nama_barang = ?,
                kategori = ?,
                stok = ?,
                kondisi = ?
            WHERE id = ?
        """, (
            nama_barang,
            kategori,
            stok,
            kondisi,
            id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("barang"))

    conn.close()

    return render_template(
        "tambah_barang.html",
        barang=barang,
        edit=True
    )


# =========================================================
# HAPUS BARANG
# =========================================================

@app.route("/barang/hapus/<int:id>")
def hapus_barang(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    sedang_dipinjam = conn.execute("""
        SELECT *
        FROM detail_peminjaman
        WHERE barang_id = ?

        AND peminjaman_id IN (
            SELECT id
            FROM peminjaman
            WHERE status = 'Dipinjam'
        )
    """, (id,)).fetchone()

    if sedang_dipinjam:

        conn.close()

        return redirect(url_for("barang"))

    conn.execute("""
        DELETE FROM barang
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("barang"))


# =========================================================
# DATA PEMINJAMAN
# =========================================================

@app.route("/peminjaman")
def peminjaman():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    data_peminjaman = conn.execute("""
        SELECT *
        FROM peminjaman
        ORDER BY id DESC
    """).fetchall()

    daftar_peminjaman = []

    hari_ini = date.today()

    for data in data_peminjaman:

        detail_barang = conn.execute("""
            SELECT
                detail_peminjaman.jumlah,
                barang.nama_barang
            FROM detail_peminjaman
            JOIN barang
                ON detail_peminjaman.barang_id = barang.id
            WHERE detail_peminjaman.peminjaman_id = ?
        """, (data["id"],)).fetchall()

        if data["status"] == "Dipinjam":

            tenggat = datetime.strptime(
                data["tenggat_kembali"],
                "%Y-%m-%d"
            ).date()

            selisih = (tenggat - hari_ini).days

            if selisih < 0:
                keterangan_tenggat = "Terlambat"
            elif selisih == 0:
                keterangan_tenggat = "Jatuh tempo hari ini"
            else:
                keterangan_tenggat = f"{selisih} hari lagi"

        else:

            keterangan_tenggat = "Selesai"

        daftar_peminjaman.append({
            "data": data,
            "barang": detail_barang,
            "keterangan_tenggat": keterangan_tenggat
        })

    # Barang yang masih memiliki stok
    data_barang = conn.execute("""
        SELECT *
        FROM barang
        WHERE stok > 0
        ORDER BY nama_barang ASC
    """).fetchall()

    conn.close()

    return render_template(
        "peminjaman.html",
        peminjaman=daftar_peminjaman,
        barang=data_barang
    )


# =========================================================
# TAMBAH PEMINJAMAN BANYAK BARANG
# =========================================================

@app.route("/peminjaman/tambah", methods=["GET", "POST"])
def tambah_peminjaman():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    data_barang = conn.execute("""
        SELECT *
        FROM barang
        WHERE stok > 0
        ORDER BY nama_barang ASC
    """).fetchall()

    if request.method == "POST":

        nama_mahasiswa = request.form["nama_mahasiswa"]
        nim = request.form["nim"]
        no_whatsapp = request.form["no_whatsapp"]

        tanggal_pinjam = request.form["tanggal_pinjam"]
        tenggat_kembali = request.form["tenggat_kembali"]

        # ---------------------------------------------
        # CEK TANGGAL
        # ---------------------------------------------

        tanggal_pinjam_obj = datetime.strptime(
            tanggal_pinjam,
            "%Y-%m-%d"
        ).date()

        tenggat_obj = datetime.strptime(
            tenggat_kembali,
            "%Y-%m-%d"
        ).date()

        if tenggat_obj < tanggal_pinjam_obj:

            conn.close()

            return render_template(
                "tambah_peminjaman.html",
                barang=data_barang,
                error="Tanggal tenggat tidak boleh sebelum tanggal pinjam."
            )

        # ---------------------------------------------
        # AMBIL BARANG YANG DIPILIH
        # ---------------------------------------------

        barang_dipinjam = []

        for item in data_barang:

            jumlah_text = request.form.get(
                f"jumlah_{item['id']}",
                "0"
            )

            try:
                jumlah = int(jumlah_text)
            except ValueError:
                jumlah = 0

            if jumlah > 0:

                if jumlah > item["stok"]:

                    conn.close()

                    return render_template(
                        "tambah_peminjaman.html",
                        barang=data_barang,
                        error=f"Stok {item['nama_barang']} hanya {item['stok']}."
                    )

                barang_dipinjam.append({
                    "id": item["id"],
                    "nama": item["nama_barang"],
                    "jumlah": jumlah
                })

        # ---------------------------------------------
        # HARUS ADA MINIMAL 1 BARANG
        # ---------------------------------------------

        if len(barang_dipinjam) == 0:

            conn.close()

            return render_template(
                "tambah_peminjaman.html",
                barang=data_barang,
                error="Pilih minimal satu barang."
            )

        # ---------------------------------------------
        # BUAT DATA PEMINJAMAN
        # ---------------------------------------------

        cursor = conn.execute("""
            INSERT INTO peminjaman
            (
                nama_mahasiswa,
                nim,
                no_whatsapp,
                tanggal_pinjam,
                tenggat_kembali,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            nama_mahasiswa,
            nim,
            no_whatsapp,
            tanggal_pinjam,
            tenggat_kembali,
            "Dipinjam"
        ))

        peminjaman_id = cursor.lastrowid

        # ---------------------------------------------
        # SIMPAN DETAIL BARANG + KURANGI STOK
        # ---------------------------------------------

        for item in barang_dipinjam:

            conn.execute("""
                INSERT INTO detail_peminjaman
                (
                    peminjaman_id,
                    barang_id,
                    jumlah
                )
                VALUES (?, ?, ?)
            """, (
                peminjaman_id,
                item["id"],
                item["jumlah"]
            ))

            conn.execute("""
                UPDATE barang
                SET stok = stok - ?
                WHERE id = ?
            """, (
                item["jumlah"],
                item["id"]
            ))

        conn.commit()
        conn.close()

        return redirect(url_for("peminjaman"))

    conn.close()

    return render_template(
        "tambah_peminjaman.html",
        barang=data_barang,
        edit=False
    )


# =========================================================
# KEMBALIKAN BARANG
# =========================================================

@app.route("/peminjaman/kembali/<int:id>")
def kembalikan_barang(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    data = conn.execute("""
        SELECT *
        FROM peminjaman
        WHERE id = ?
    """, (id,)).fetchone()

    if data is None:

        conn.close()

        return redirect(url_for("peminjaman"))

    # Hanya proses jika masih dipinjam
    if data["status"] == "Dipinjam":

        tanggal_kembali = date.today().isoformat()

        # Ambil semua barang dalam transaksi
        detail = conn.execute("""
            SELECT *
            FROM detail_peminjaman
            WHERE peminjaman_id = ?
        """, (id,)).fetchall()

        # Kembalikan stok setiap barang
        for item in detail:

            conn.execute("""
                UPDATE barang
                SET stok = stok + ?
                WHERE id = ?
            """, (
                item["jumlah"],
                item["barang_id"]
            ))

        # Ubah status transaksi
        conn.execute("""
            UPDATE peminjaman
            SET status = 'Dikembalikan',
                tanggal_kembali = ?
            WHERE id = ?
        """, (
            tanggal_kembali,
            id
        ))

        conn.commit()

    conn.close()

    return redirect(url_for("peminjaman"))


# =========================================================
# WHATSAPP
# =========================================================

@app.route("/whatsapp/<int:id>")
def whatsapp(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    data = conn.execute("""
        SELECT *
        FROM peminjaman
        WHERE id = ?
    """, (id,)).fetchone()

    if data is None:

        conn.close()

        return redirect(url_for("peminjaman"))

    detail_barang = conn.execute("""
        SELECT
            detail_peminjaman.jumlah,
            barang.nama_barang
        FROM detail_peminjaman
        JOIN barang
            ON detail_peminjaman.barang_id = barang.id
        WHERE detail_peminjaman.peminjaman_id = ?
    """, (id,)).fetchall()

    conn.close()

    nomor = data["no_whatsapp"]

    nomor = nomor.replace(" ", "")
    nomor = nomor.replace("-", "")
    nomor = nomor.replace("+", "")

    if nomor.startswith("0"):
        nomor = "62" + nomor[1:]

    daftar_barang = ""

    for item in detail_barang:

        daftar_barang += (
            f"- {item['nama_barang']} "
            f"(jumlah: {item['jumlah']})\n"
        )

    pesan = f"""Halo {data['nama_mahasiswa']},

Ini pengingat dari Laboratorium.

Barang yang sedang Anda pinjam:
{daftar_barang}
Tanggal pinjam: {data['tanggal_pinjam']}
Batas pengembalian: {data['tenggat_kembali']}

Mohon mengembalikan barang sesuai dengan batas waktu yang telah ditentukan.

Terima kasih.
"""

    link = f"https://wa.me/{nomor}?text={quote(pesan)}"

    return redirect(link)


# =========================================================
# JALANKAN APLIKASI
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)