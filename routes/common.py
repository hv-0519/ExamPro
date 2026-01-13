from flask import Blueprint, render_template

common_bp = Blueprint("common", __name__)


@common_bp.route("/")
def hello():
    return render_template("common/index.html")


@common_bp.route("/features")
def features():
    return render_template("common/features.html")


@common_bp.route("/about")
def about_us():
    return render_template("common/about_us.html")
