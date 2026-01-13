from flask import Blueprint, url_for, render_template, request, redirect
import sqlite3
from utils.helpers import user_exists

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/dashboard")
def dashboard():
    username = request.args.get("username")

    if not username or not user_exists(username, "student"):
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database/exam.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sp.photo_path
        FROM users u
        JOIN student_profiles sp ON u.user_id = sp.user_id
        WHERE u.username = ?
        """,
        (username,),
    )
    row = cursor.fetchone()
    conn.close()

    photo_path = row[0] if row else None

    return render_template(
        "student/student_dashboard.html",
        username=username,
        photo_path=photo_path,
    )
