from flask import Blueprint, render_template, session, redirect, url_for

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'user_id' in session:
        profile = session.get('user_profile')
        if profile and 'name' in profile:
            return redirect(url_for('profile.profile', username=profile['name']))
        else:
            session.clear()
            return redirect(url_for('auth.login'))
    return render_template('index.html') 