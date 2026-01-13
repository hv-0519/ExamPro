from flask import Blueprint, url_for, render_template, request, redirect
import sqlite3
import io
import csv  # ✅ REQUIRED

from utils.helpers import (
    get_admin_data,
    number_to_emoji,
    user_exists,
)

admin_bp = Blueprint("admin", __name__, url_prefix="")


@admin_bp.route("/dashboard")
def admin_dashboard():
    username = request.args.get("username")

    _, redirect_resp = get_admin_data(username, "users")
    if redirect_resp:
        return redirect_resp

    conn = sqlite3.connect("database/exam.db")
    cursor = conn.cursor()

    # Get total students
    cursor.execute("""SELECT COUNT(*) from users where role = 'student'""")
    total_student = cursor.fetchone()[0]

    # Get total exams
    cursor.execute("""SELECT COUNT(*) FROM exams""")
    total_exams = cursor.fetchone()[0]

    # Get recent 5 students
    cursor.execute(
        """
    SELECT u.username, sp.first_name, sp.email
    FROM users u
    LEFT JOIN student_profiles sp ON u.user_id = sp.user_id
    WHERE u.role = 'student'
    ORDER BY u.user_id DESC
    LIMIT 5
    """
    )
    students = cursor.fetchall()

    # Get recent 5 Exams
    cursor.execute(
        """
        SELECT title, duration_minutes, total_marks
        FROM exams
        ORDER BY rowid DESC
        LIMIT 5
        """
    )
    exams = cursor.fetchall()
    conn.close()

    # Convert to list of dicts
    student_list = [
        {
            "username": row[0],
            "first_name": row[1] if row[1] else "N/A",
            "email": row[2] if row[2] else "N/A",
        }
        for row in students
    ]

    # Convert exams to list of dicts
    exam_list = [
        {
            "title": row[0],
            "duration_minutes": row[1],
            "marks": row[2],
        }
        for row in exams
    ]

    total_students_emoji = number_to_emoji(total_student)
    total_exam_emoji = number_to_emoji(total_exams)

    return render_template(
        "admin/admin_dashboard.html",
        username=username,
        total_student=total_student,
        total_exams=total_exams,
        total_students_emoji=total_students_emoji,
        total_exam_emoji=total_exam_emoji,
        students=student_list,
        exams=exam_list,
    )


@admin_bp.route("/exams")
def admin_exams():
    username = request.args.get("username")
    exams, redirect_resp = get_admin_data(username, "exams")
    if redirect_resp:
        return redirect_resp
    return render_template("admin/admin_exams.html", username=username, exams=exams)


@admin_bp.route("/exams/<int:exam_id>")
def exam_detail(exam_id):
    username = request.args.get("username")

    exam, redirect_resp = get_admin_data(
        username,
        "exams",
        single=True,
        where_clause="exam_id = ?",
        params=(exam_id,),
    )
    if redirect_resp:
        return redirect_resp

    return render_template("admin/exam.html", username=username, exam=exam)


@admin_bp.route("/students")
def students():
    username = request.args.get("username")

    # Only use this for admin validation
    _, redirect_resp = get_admin_data(username, "users")
    if redirect_resp:
        return redirect_resp

    # Now manually fetch student data
    conn = sqlite3.connect("database/exam.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
    u.user_id,
    u.username,
    sp.first_name,
    sp.last_name,
    sp.email,
    sp.photo_path
FROM users u
JOIN student_profiles sp ON u.user_id = sp.user_id
ORDER BY u.user_id DESC
LIMIT 5
    """
    )
    students = cursor.fetchall()
    conn.close()

    # Convert to list of dicts

    return render_template("admin/students.html", username=username, res=students)


@admin_bp.route("/risk_analysis")
def risk_analysis():
    username = request.args.get("username")
    res, redirect_resp = get_admin_data(username, "risk_analysis")
    if redirect_resp:
        return redirect_resp
    return render_template("admin/risk_analysis.html", username=username, res=res)


@admin_bp.route("/behavior_logs")
def behavior_logs():
    username = request.args.get("username")
    res, redirect_resp = get_admin_data(username, "behavior_logs")
    if redirect_resp:
        return redirect_resp
    return render_template("admin/behavior_logs.html", username=username, res=res)


@admin_bp.route("/exams/<int:exam_id>/upload_csv", methods=["GET", "POST"])
def upload_csv(exam_id):
    username = request.args.get("username")

    def get_connection():
        return sqlite3.connect("database/exam.db", timeout=10)

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # exam title
        cursor.execute("SELECT title FROM exams WHERE exam_id = ?", (exam_id,))
        exam = cursor.fetchone()
        title = exam[0] if exam else "Unknown Exam"

        if request.method == "POST":
            file = request.files.get("csv_file")
            if not file:
                return redirect(
                    url_for(
                        "admin.upload_csv",
                        exam_id=exam_id,
                        username=username,
                        status="error",
                        msg="No file selected",
                    )
                )

            stream = io.StringIO(file.stream.read().decode("utf-8"))
            reader = csv.DictReader(stream)

            for row in reader:
                cursor.execute(
                    """
    INSERT OR IGNORE INTO questions
    (exam_id, question_text, option_a, option_b, option_c, option_d,
     correct_option, wrong_answer_explanation, marks)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
                    (
                        exam_id,
                        row["question_text"].strip(),
                        row["option_a"].strip(),
                        row["option_b"].strip(),
                        row["option_c"].strip(),
                        row["option_d"].strip(),
                        row["correct_option"].strip().upper(),
                        row.get("wrong_answer_explanation", "").strip(),
                        int(row.get("marks", 1)),
                    ),
                )

            conn.commit()

            return redirect(
                url_for(
                    "admin.upload_csv",
                    exam_id=exam_id,
                    username=username,
                    status="success",
                )
            )

    except Exception as e:
        if conn:
            conn.rollback()
        return redirect(
            url_for(
                "admin.upload_csv",
                exam_id=exam_id,
                username=username,
                status="error",
                msg=str(e),
            )
        )

    finally:
        if conn:
            conn.close()

    # ✅ GET — FETCH QUESTIONS
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT question_text, option_a, option_b, option_c, option_d,
               correct_option, marks
        FROM questions WHERE exam_id = ?
        """,
        (exam_id,),
    )
    questions = cursor.fetchall()
    conn.close()

    return render_template(
        "admin/upload_csv.html",
        username=username,
        exam_id=exam_id,
        title=title,
        questions=questions,
        status=request.args.get("status"),
        msg=request.args.get("msg"),
    )


@admin_bp.route("/exams/add", methods=["GET", "POST"])
def add_exams():
    username = request.args.get("username")
    _, redirect_resp = get_admin_data(username, "users")
    if redirect_resp:
        return redirect_resp

    if request.method == "POST":
        title = request.form.get("title").strip()
        duration = int(request.form["duration_minutes"])
        total_marks = int(request.form["total_marks"])
        max_attempts = int(request.form.get("max_attempts", 3))

        conn = sqlite3.connect("database/exam.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO exams (title, duration_minutes, total_marks, max_attempts)
            VALUES (?, ?, ?, ?)
            """,
            (title, duration, total_marks, max_attempts),
        )

        exam_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return redirect(url_for("admin.add_exams", exam_id=exam_id, username=username))

    return render_template("admin/add_exams.html", username=username)
