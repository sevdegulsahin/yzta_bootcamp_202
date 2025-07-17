import logging
from flask import Flask
from routes.auth_routes import auth_bp
from routes.interview_routes import interview_bp
from routes.profile_routes import profile_bp
from routes.error_routes import error_bp
from routes.main_routes import main_bp

app = Flask(__name__)
app.config.from_object('config.Config')

app.register_blueprint(auth_bp)
app.register_blueprint(interview_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(error_bp)
app.register_blueprint(main_bp)

if __name__ == "__main__":
    app.run(debug=True)