from flask import Blueprint, render_template, session, redirect, url_for

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    user = session.get('user_profile')
    return render_template('index.html', user=user) 