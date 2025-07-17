from flask import Blueprint, render_template

error_bp = Blueprint('error', __name__)

@error_bp.route('/error')
def error_page():
    return render_template('error.html', message="Beklenmedik bir hata oluştu.") 