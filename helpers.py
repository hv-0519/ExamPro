import sqlite3
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash
from flask import url_for, redirect


def send_email(
    to_email,
    subject,
    body,
    from_email="jay451428@gmail.com",
    from_password="xpya nqal apnd jxqe",  # Use environment variables in production!
):
    """Send email using Gmail SMTP"""
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, from_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email sending failed:", e)  # Log in production


def generate_username(fname, lname):
    """Generate username from first and last name"""
    return f"{fname.lower()}.{lname.lower()}{random.randint(100, 999)}"


def generate_password(length=8):
    """Generate random password"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def user_exists(username, role=None):
    """Check if user exists in database"""
    conn = sqlite3.connect("database/exam.db")
    cursor = conn.cursor()
    if role:
        cursor.execute(
            "SELECT 1 FROM users WHERE username=? AND role=?", (username, role)
        )
    else:
        cursor.execute("SELECT 1 FROM users WHERE username=?", (username,))
    res = cursor.fetchone()
    conn.close()
    return bool(res)


def number_to_emoji(number):
    """Convert number to emoji representation"""
    emoji_map = {
        0: "0️⃣",
        1: "1️⃣",
        2: "2️⃣",
        3: "3️⃣",
        4: "4️⃣",
        5: "5️⃣",
        6: "6️⃣",
        7: "7️⃣",
        8: "8️⃣",
        9: "9️⃣",
    }
    return "".join(emoji_map[int(digit)] for digit in str(number))


def get_admin_data(username, table_name, single=False, where_clause=None, params=()):
    """
    Fetch data from database with admin validation
    Returns: (data, redirect_response)
    """
    # Admin validation
    if not username or not user_exists(username, "admin"):
        return None, redirect(url_for("login"))

    conn = sqlite3.connect("database/exam.db")
    cursor = conn.cursor()

    query = f"SELECT * FROM {table_name}"
    if where_clause:
        query += f" WHERE {where_clause}"

    cursor.execute(query, params)

    if single:
        data = cursor.fetchone()
    else:
        data = cursor.fetchall()

    conn.close()
    return data, None