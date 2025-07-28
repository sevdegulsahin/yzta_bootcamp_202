from flask import Blueprint, render_template, request, redirect, url_for, session
from services.supabase_service import supabase
import logging
from werkzeug.utils import secure_filename

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile/<username>')
def profile(username):
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Profile sayfasına erişim denemesi: oturum yok.")
        return redirect(url_for('auth.login'))

    user_profile = session.get('user_profile')

    # Eğer session'daki profil verisi yoksa veya tutarsızsa Supabase'den çek
    if not isinstance(user_profile, dict) or not user_profile or user_profile.get("auth_id") != user_id:
        try:
            # Supabase'den auth_id ile kullanıcıyı bul
            profile_data_response = supabase.table("users").select("*").eq("auth_id", user_id).execute()
            profile_data = profile_data_response.data
            
            if profile_data and isinstance(profile_data, list) and len(profile_data) > 0 and isinstance(profile_data[0], dict):
                user_profile = profile_data[0]
                session['user_profile'] = user_profile
                logging.info(f"Kullanıcı profili Supabase'den çekildi ve session'a kaydedildi: {user_id}")
            else:
                logging.warning(f"Kullanıcı profili bulunamadı: auth_id={user_id}")
                user_profile = None

        except Exception as e:
            logging.error(f"Supabase'den kullanıcı profili çekilirken hata: {e}", exc_info=True)
            user_profile = None

    if user_profile and isinstance(user_profile, dict):
        # Gösterimde kullanılacak verileri hazırla
        display_name = user_profile.get('name') or username.capitalize()
        user_data_for_template = {
            'name': display_name,
            'role': user_profile.get('role', 'Rol Bilgisi Yok'),
            'email': user_profile.get('email', 'email@example.com'),
            'score': user_profile.get('score', 0),
            'total_interviews': user_profile.get('total_interviews', 0),
            'success_rate': user_profile.get('success_rate', 0),
            'total_time': user_profile.get('total_time', 0),  # örn. saniye cinsinden
                'avatar_url': user_profile.get('avatar_url'),   # 

            'progress_data': [
                {'item': 'Frontend Bilgisi', 'value': user_profile.get('frontend_score', 0)},
                {'item': 'Backend Bilgisi', 'value': user_profile.get('backend_score', 0)},
                {'item': 'Mobile Bilgisi', 'value': user_profile.get('mobile_score', 0)},
                # İstersen başka yetenekler ekle
            ]
        }
        return render_template('profile.html', user=user_data_for_template)
    else:
        # Profil verisi yoksa session'ı temizle ve ana sayfaya yönlendir
        logging.warning("Profil verisi bulunamadı, session temizleniyor ve ana sayfaya yönlendiriliyor.")
        session.clear()
        return redirect(url_for('main.index'))
    





    ##ÇALIŞIYOR FAKAT FOTOGRAFI KAYDETMİYOR VERİ TABANINDA USERS TABLOSUNDA avatar_url ADINDA SUTUN OLMALI
# @profile_bp.route('/edit_profile', methods=['GET', 'POST'])
# def edit_profile():
#     user_id = session.get('user_id')
#     if not user_id:
#         return redirect(url_for('auth.login'))

#     if request.method == 'POST':
#         name = request.form.get('name')
#         # Checkbox'lar çoklu seçim olduğundan getlist ile tüm seçimleri al
#         selected_roles = request.form.getlist('roles')  # ['frontend', 'backend'] gibi liste döner
#         # role sütunu tek metin olduğu için listeyi stringe çeviriyoruz (virgülle ayrılmış)
#         role = ",".join(selected_roles) if selected_roles else ""

#         try:
#             update_data = {
#                 "name": name,
#                 "role": role,
#                 # Diğer güncellemeler varsa onları da ekle
#             }

#             supabase.table("users").update(update_data).eq("auth_id", user_id).execute()

#             # Session güncelle
#             user_profile = session.get('user_profile', {})
#             user_profile.update(update_data)
#             session['user_profile'] = user_profile

#             return redirect(url_for('profile.profile', username=name))
#         except Exception as e:
#             logging.error(f"Profil güncellenemedi: {e}", exc_info=True)
#             return f"Profil güncellenirken hata oluştu: {str(e)}", 500

#     # GET isteği için
#     user_profile = session.get('user_profile', {})

#     # Eğer rol string halinde virgülle ayrılmışsa liste yap
#     if "role" in user_profile and isinstance(user_profile["role"], str):
#         user_profile["roles"] = user_profile["role"].split(",")
#     else:
#         user_profile["roles"] = []

#     return render_template('edit_profile.html', user=user_profile)
import os
from werkzeug.utils import secure_filename
from flask import current_app

@profile_bp.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')  # Tek rol seçimi alınıyor

        avatar_file = request.files.get('avatar')
        avatar_url = None

        if avatar_file and avatar_file.filename != '':
            filename = secure_filename(avatar_file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static/uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            avatar_file.save(file_path)
            avatar_url = url_for('static', filename=f'uploads/{filename}') 


        try:
            update_data = {
                "name": name,
                "role": role,
            }
            if avatar_url:
                update_data["avatar_url"] = avatar_url

            supabase.table("users").update(update_data).eq("auth_id", user_id).execute()

            # Session güncelle
            user_profile = session.get('user_profile', {})
            user_profile.update(update_data)
            session['user_profile'] = user_profile

            return redirect(url_for('profile.profile', username=name))
        except Exception as e:
            logging.error(f"Profil güncellenemedi: {e}", exc_info=True)
            return f"Profil güncellenirken hata oluştu: {str(e)}", 500

    user_profile = session.get('user_profile', {})

    # user_profile içindeki 'role' zaten string olmalı, direkt gönderiyoruz
    return render_template('edit_profile.html', user=user_profile)

