from flask import Blueprint, render_template, request, redirect, url_for, session
from services.supabase_service import supabase
import logging

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            return render_template('login.html', error="Lütfen e-posta ve şifrenizi girin.")
        if not supabase:
            return render_template('login.html', error="Sunucu hatası: Supabase bağlantısı kurulamadı.")
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if response and hasattr(response, 'user') and response.user:
                user_id = response.user.id
                # users tablosundan profil çek
                profile_data_response = supabase.table("users").select("*").eq("auth_id", user_id).execute()
                profile_data = profile_data_response.data
                if profile_data and isinstance(profile_data, list) and len(profile_data) > 0 and isinstance(profile_data[0], dict):
                    user_profile = profile_data[0]
                else:
                    # Eğer users tablosunda yoksa, otomatik ekle
                    user_profile = {"auth_id": user_id, "name": email.split('@')[0], "email": email}
                    supabase.table("users").insert(user_profile).execute()
                session['user_id'] = user_id
                session['user_email'] = email
                session['user_profile'] = user_profile
                return redirect(url_for('profile.profile', username=user_profile.get('name', 'Kullanici')))
            else:
                return render_template('login.html', error="Hatalı e-posta veya şifre. Lütfen tekrar deneyin.")
        except Exception as e:
            return render_template('login.html', error=f"Giriş sırasında bir hata oluştu: {e}")
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if not name or not email or not password or not confirm_password:
            return render_template('register.html', error="Lütfen tüm alanları doldurun.")
        if password != confirm_password:
            return render_template('register.html', error="Şifreler uyuşmuyor.")
        if not supabase:
            return render_template('register.html', error="Sunucu hatası: Supabase bağlantısı kurulamadı.")
        try:
            response = supabase.auth.sign_up({"email": email, "password": password})
            if response and hasattr(response, 'user') and response.user:
                user_id = response.user.id
                # users tablosuna da ekle
                user_profile_data = {"auth_id": user_id, "name": name, "email": email}
                supabase.table("users").insert(user_profile_data).execute()
                return redirect(url_for('auth.login'))
            else:
                return render_template('register.html', error="Kayıt sırasında bir sorun oluştu.")
        except Exception as e:
            return render_template('register.html', error=f"Kayıt sırasında bir hata oluştu: {e}")
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login')) 