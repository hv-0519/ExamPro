from flask import Flask
import os
from routes.common import common_bp
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.student import student_bp

app = Flask(__name__)

app.register_blueprint(common_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(student_bp)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# To Run On Port 6969
if __name__ == "__main__":
    app.run(port=6969, debug=True)