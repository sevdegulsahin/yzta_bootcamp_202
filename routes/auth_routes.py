from flask import Blueprint, render_template, request, redirect, url_for, session
from services.supabase_service import supabase
import logging

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        logging.info(f"Login POST isteği alındı: E-posta={email}")

        if not email or not password:
            error_message = "Lütfen e-posta ve şifrenizi girin."
            return render_template('login.html', error=error_message)

        if not supabase:
            error_message = "Sunucu hatası: Supabase bağlantısı kurulamadı."
            return render_template('login.html', error=error_message)

        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})

            user_id = None
            user_email = None
            user_profile = None

            if response and hasattr(response, 'user') and response.user:
                user_id = response.user.id
                user_email = response.user.email
                logging.info(f"Oturum açma başarılı. User ID: {user_id}, E-posta: {user_email}")
            else:
                error_message = "Hatalı e-posta veya şifre. Lütfen tekrar deneyin."
                logging.warning("Oturum açma başarısız. Kullanıcı nesnesi bulunamadı.")
                return render_template('login.html', error=error_message)

            if user_id:
                profile_data_response = supabase.table("users").select("*").eq("auth_id", user_id).execute()
                profile_data = profile_data_response.data

                if profile_data and isinstance(profile_data, list) and len(profile_data) > 0 and isinstance(profile_data[0], dict):
                    user_profile = profile_data[0]
                    logging.info(f"Profil bilgileri başarıyla çekildi. User ID: {user_id}")
                else:
                    logging.warning(f"Profil bilgileri çekilemedi veya eksik. Supabase yanıtı: {profile_data}")
                    user_profile = None

                session['user_id'] = user_id
                session['user_email'] = user_email
                session['user_profile'] = user_profile

                display_name = user_profile.get('name', user_email.split('@')[0].capitalize() if user_email else 'Kullanici')
                return redirect(url_for('profile.profile', username=display_name))

            else:
                error_message = "Kullanıcı bilgileri alınamadı. Lütfen tekrar deneyin."
                return render_template('login.html', error=error_message)

        except Exception as e:
            logging.error(f"Supabase oturum açma hatası: {e}")
            error_str = str(e)
            if "invalid login credentials" in error_str or "invalid grant" in error_str:
                error_message = "Hatalı e-posta veya şifre. Lütfen tekrar deneyin."
            else:
                error_message = f"Giriş sırasında bir hata oluştu: {e}"
            return render_template('login.html', error=error_message)

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not name or not email or not password or not confirm_password:
            error_message = "Lütfen tüm alanları doldurun."
            return render_template('register.html', error=error_message)

        if password != confirm_password:
            error_message = "Şifreler uyuşmuyor."
            return render_template('register.html', error=error_message)

        if not supabase:
            error_message = "Sunucu hatası: Supabase bağlantısı kurulamadı."
            return render_template('register.html', error=error_message)

        try:
            response = supabase.auth.sign_up({"email": email, "password": password})

            user_id = None
            user_email_from_response = None

            if response and hasattr(response, 'user') and response.user:
                user_id = response.user.id
                user_email_from_response = response.user.email
                logging.info(f"Supabase Auth kaydı başarılı. User ID: {user_id}")
            else:
                logging.warning(f"Supabase Auth kaydı başarısız veya beklenmedik yanıt. Response: {response}")
                error_message = "Kayıt sırasında bir sorun oluştu. Lütfen bilgilerinizi kontrol edin."
                return render_template('register.html', error=error_message)

            if user_id:
                user_profile_data = {"auth_id": user_id, "name": name, "email": email}
                insert_response, _ = supabase.table("users").insert(user_profile_data).execute()

                if insert_response and len(insert_response) > 0 and insert_response[0]:
                    logging.info("Kullanıcı bilgileri veritabanına eklendi.")
                    return redirect(url_for('auth.login'))
                else:
                    error_message = "Kullanıcı bilgileri veritabanına kaydedilirken bir sorun oluştu. Lütfen tekrar deneyin."
                    logging.error(f"Hata: Kullanıcı bilgileri veritabanına eklenemedi. Response: {insert_response}")
                    try:
                        supabase.auth.delete_user(user_id)
                        logging.info(f"Hata sonrası silinen kullanıcı (Auth ID): {user_id}")
                    except Exception as auth_del_e:
                        logging.error(f"Hata sonrası Auth kullanıcısı silinemedi: {auth_del_e}")
                    return render_template('register.html', error=error_message)
            else:
                error_message = "Kayıt sırasında bir sorun oluştu (Kullanıcı bilgisi alınamadı). Lütfen tekrar deneyin."
                return render_template('register.html', error=error_message)

        except Exception as e:
            error_str = str(e)
            logging.error(f"Supabase kayıt hatası: {error_str}")
            if "duplicate key value violates unique constraint" in error_str or "User already registered" in error_str or "duplicate email" in error_str:
                 error_message = "Bu e-posta adresiyle zaten bir hesap mevcut."
            elif "Password should be at least 8 characters long" in error_str:
                 error_message = "Şifre en az 8 karakter uzunluğunda olmalı."
            else:
                 error_message = f"Kayıt sırasında bir hata oluştu: {e}"
            return render_template('register.html', error=error_message)

    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_profile', None)
    session.pop('chat_history', None)
    session.pop('current_question_id', None)
    session.pop('selected_test_types', None)
    session.pop('selected_category_for_test', None)
    session.pop('total_written_test_questions', None)
    session.pop('current_test_question_index', None)
    session.pop('current_test_question_data', None)
    session.pop('current_test_question_id', None)
    session.pop('current_test_question_num', None)
    session.pop('current_test_question_type', None)
    session.pop('current_test_category', None)
    session.pop('completed_test_questions_data', None) 
    logging.info("Kullanıcı çıkış yaptı.")
    return redirect(url_for('auth.login')) 