from flask import Blueprint, url_for, render_template, request, redirect
import sqlite3, random, string
from werkzeug.security import generate_password_hash, check_password_hash
from utils.helpers import generate_password, generate_username, send_email

auth_bp = Blueprint("auth", __name__)

# ---------------- Register ----------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fname = request.form["fname"]
        lname = request.form["lname"]
        email = request.form.get("email")
        contact_no = request.form.get("contact_no")
        gender = request.form.get("gender")
        date_of_birth = request.form.get("date_of_birth")
        address = request.form.get("address")
        photo_path = request.form.get("photo_path")

        username = generate_username(fname, lname)
        raw_password = generate_password()
        password_hash = generate_password_hash(raw_password)

        conn = sqlite3.connect("database/exam.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (username, password_hash, role, is_temp_password) VALUES (?, ?, ?, 1)",
            (username, password_hash, "student"),
        )
        user_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO student_profiles 
               (user_id, first_name, last_name, email, contact_no, gender, date_of_birth, address, photo_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                fname,
                lname,
                email,
                contact_no,
                gender,
                date_of_birth,
                address,
                photo_path,
            ),
        )

        conn.commit()
        conn.close()

        if email:
            send_email(
                to_email=email,
                subject="Your ExamPro Account Credentials",
                body=f"""Hello {fname},

Username: {username}
Temporary Password: {raw_password}

Please login and change password.
""",
                from_email="jay451428@gmail.com",
                from_password="xpya nqal apnd jxqe",
            )

        return redirect(url_for("auth.login"))

    return render_template("common/register.html")


# ---------------- Login ----------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database/exam.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash, role, is_temp_password FROM users WHERE username=?",
            (username,),
        )
        user = cursor.fetchone()
        conn.close()

        if not user or not check_password_hash(user[0], password):
            return render_template("common/login.html", error="Invalid credentials")

        role, is_temp_password = user[1], user[2]

        if role == "student" and is_temp_password:
            return redirect(url_for("auth.update_password", username=username))

        if role == "admin":
            return redirect(url_for("admin.admin_dashboard", username=username))

        return redirect(url_for("student.dashboard", username=username))

    return render_template("common/login.html")


# ---------------- Update Password ----------------
@auth_bp.route("/update_password", methods=["GET", "POST"])
def update_password():
    username = request.args.get("username") or request.form.get("username")
    if not username:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        old = request.form["old_password"]
        new = request.form["new_password"]
        confirm = request.form["confirm_password"]

        if new != confirm:
            return render_template(
                "common/update_password.html",
                username=username,
                error="Passwords do not match",
            )

        conn = sqlite3.connect("database/exam.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash FROM users WHERE username=?", (username,)
        )
        user = cursor.fetchone()

        if not user or not check_password_hash(user[0], old):
            conn.close()
            return render_template(
                "common/update_password.html",
                username=username,
                error="Old password incorrect",
            )

        cursor.execute(
            "UPDATE users SET password_hash=?, is_temp_password=0 WHERE username=?",
            (generate_password_hash(new), username),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("auth.login"))

    return render_template("common/update_password.html", username=username)


# ---------------- Forgot Password ----------------
@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]

        conn = sqlite3.connect("database/exam.db")
        cursor = conn.cursor()
        cursor.execute(
            """SELECT u.user_id, u.username
               FROM users u
               JOIN student_profiles sp ON u.user_id = sp.user_id
               WHERE sp.email=?""",
            (email,),
        )
        res = cursor.fetchone()

        if not res:
            conn.close()
            return render_template(
                "common/forgot_password.html", error="Email not found"
            )

        user_id, username = res
        reset_code = "".join(random.choices(string.ascii_letters + string.digits, k=6))

        cursor.execute(
            "INSERT INTO password_resets (user_id, reset_code) VALUES (?, ?)",
            (user_id, reset_code),
        )
        conn.commit()
        conn.close()

        send_email(
            to_email=email,
            subject="Password Reset Code",
            body=f"Your reset code: {reset_code}",
            from_email="jay451428@gmail.com",
            from_password="xpya nqal apnd jxqe",
        )

        return redirect(url_for("auth.verify_code"))

    return render_template("common/forgot_password.html")


@auth_bp.route("/verify_code", methods=["GET", "POST"])
def verify_code():
    if request.method == "POST":
        code = request.form["reset_code"]

        conn = sqlite3.connect("database/exam.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id FROM password_resets WHERE reset_code=? AND is_used=0",
            (code,),
        )
        res = cursor.fetchone()

        if not res:
            conn.close()
            return render_template("common/verify_code.html", error="Invalid code")

        cursor.execute(
            "UPDATE password_resets SET is_used=1 WHERE reset_code=?", (code,)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("auth.reset_password", user_id=res[0]))

    return render_template("common/verify_code.html")


@auth_bp.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    user_id = request.args.get("user_id")
    if not user_id:
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        new = request.form["new_password"]
        confirm = request.form["confirm_password"]

        if new != confirm:
            return render_template(
                "common/reset_password.html",
                user_id=user_id,
                error="Passwords do not match",
            )

        conn = sqlite3.connect("database/exam.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash=?, is_temp_password=0 WHERE user_id=?",
            (generate_password_hash(new), user_id),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("auth.login"))

    return render_template("common/reset_password.html", user_id=user_id)


# ---------------- Logout ----------------
@auth_bp.route("/logout")
def logout():
    return redirect(url_for("common.hello"))
