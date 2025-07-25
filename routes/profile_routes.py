from flask import Blueprint, render_template, request, redirect, url_for, session
from services.supabase_service import supabase
import logging

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile/<username>')
def profile(username):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    user_profile = session.get('user_profile')
    if not isinstance(user_profile, dict) or not user_profile or user_profile.get("auth_id") != user_id:
        try:
            profile_data_response = supabase.table("users").select("*").eq("auth_id", user_id).execute()
            profile_data = profile_data_response.data
            if profile_data and isinstance(profile_data, list) and len(profile_data) > 0 and isinstance(profile_data[0], dict):
                user_profile = profile_data[0]
                session['user_profile'] = user_profile
            else:
                user_profile = None
        except Exception as e:
            user_profile = None
    if user_profile and isinstance(user_profile, dict):
        display_name = user_profile.get('name', username.capitalize())
        user_data_for_template = {
            'name': display_name,
            'role': user_profile.get('role', 'Rol Bilgisi Yok'),
            'score': user_profile.get('score', 'N/A'),
            'progress_data': [
                {'item': 'Frontend Bilgisi', 'value': user_profile.get('frontend_score', 0)},
                {'item': 'Backend Bilgisi', 'value': user_profile.get('backend_score', 0)},
                {'item': 'Mobile Bilgisi', 'value': user_profile.get('mobile_score', 0)},
            ]
        }
        return render_template('profile.html', user=user_data_for_template)
    else:
        session.clear()
        return redirect(url_for('main.index')) 