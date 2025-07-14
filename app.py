from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client
import logging
from dotenv import load_dotenv
import os

load_dotenv()  # .env dosyasını YÜKLE önce

import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY ortam değişkeni ayarlı değil!")

genai.configure(api_key=api_key)

# Modeli başlat
model = genai.GenerativeModel("gemini-1.5-pro")



# Modeli başlat
 # "models/" ÖN EKİ OLMADAN
 # DİKKAT: başında `models/` var

from flask import render_template, request, session, redirect, url_for

def generate_interview_question(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"YZ ile mülakat sorusu üretilemedi: {e}")
        return "Şu anda yapay zeka destekli soru üretilemiyor."


# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# .env dosyasından ortam değişkenlerini yükle
load_dotenv()

# Supabase bağlantı bilgileri
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

# Supabase client'ını global olarak tanımla ve başlat
supabase: Client = None
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    logging.error("HATA: Supabase URL veya Anon Key ortam değişkenleri ayarlanmamış.")
    logging.error("Lütfen projenizin kök dizininde .env dosyasını oluşturun ve içine şu satırları ekleyin:")
    logging.error("SUPABASE_URL=\"https://your-project-ref.supabase.co\"")
    logging.error("SUPABASE_ANON_KEY=\"eyJhbGciOiJIUzI1NiIsIn...\"")
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logging.info("Supabase bağlantısı kuruldu.")
    except Exception as e:
        logging.error(f"Supabase bağlantısı kurulamadı: {e}")

app = Flask(__name__)
# Flask'ın oturum yönetimi için gizli anahtarı gereklidir.
# Güvenlik için güçlü ve rastgele bir anahtar kullanılmalı ve .env'den alınmalıdır.
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'varsayilan_cok_gizli_bir_anahtar_degistirmeli')
if app.config['SECRET_KEY'] == 'varsayilan_cok_gizli_bir_anahtar_degistirmeli':
    logging.warning("FLASK_SECRET_KEY ortam değişkeni ayarlanmamış. Güvenlik için derhal değiştirin!")

# --- Rotasyonlar ---
ALLOWED_CATEGORIES = [
    "frontend",
    "backend",
    "mobile",
    "devops",
    "data_science",
    "general"
]

# Ana Sayfa Rotası
@app.route('/interview', methods=['GET', 'POST'])
def interview():
    if 'chat_history' not in session:
        session['chat_history'] = [{"role": "model", "content": "Merhaba! Mülakat simülasyonuna hoş geldiniz. Bana biraz kendinizden bahseder misiniz?"}]

    if request.method == 'POST':
        user_input = request.form.get('user_input')
        session['chat_history'].append({"role": "user", "content": user_input})

        # Sohbeti Gemini formatına çevir
        chat_list = []
        for m in session['chat_history']:
            if m['role'] == 'user':
                chat_list.append({'role': 'user', 'parts': [m['content']]})
            else:
                chat_list.append({'role': 'model', 'parts': [m['content']]})

        chat = model.start_chat(history=chat_list)

        gemini_response = chat.send_message(user_input)
        ai_reply = gemini_response.text
        session['chat_history'].append({"role": "model", "content": ai_reply})

    return render_template('interview.html', chat_history=session['chat_history'])

@app.route('/interview/reset')
def reset_interview():
    session.pop('chat_history', None)
    return redirect(url_for('interview'))

@app.route('/interview/<category>/<int:question_num>')
def interview_question(category, question_num):
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Mülakat sorusu sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('login'))

    ALLOWED_CATEGORIES = ["frontend", "backend", "mobile", "devops", "data_science", "general"]
    if category not in ALLOWED_CATEGORIES:
        logging.error(f"Geçersiz mülakat kategorisi istendi: {category}")
        return render_template('error.html', message="Geçersiz mülakat kategorisi."), 404

    try:
        # Sorulacak promptu oluştur
        prompt = f"{category} kategorisinde bir mülakat yapıyoruz. Bana {question_num}. soruyu ver."

        # Gemini API'den soruyu al
        ai_question = generate_interview_question(prompt)

        return render_template('interview_question.html',
                               question_num=question_num,
                               total_questions=5,
                               question_text=ai_question,
                               category=category)
    except Exception as e:
        logging.exception("YZ ile mülakat sorusu üretilemedi")
        return render_template('error.html', message="Yapay zeka soruyu oluşturamadı.")


@app.route('/')
def index():
    if 'user_id' in session:
        profile = session.get('user_profile')
        if profile and 'name' in profile:
            return redirect(url_for('profile', username=profile['name']))
        else:
            # Profil bilgisi yoksa session'ı temizle ve tekrar giriş iste
            session.clear()
            return redirect(url_for('login'))
    return render_template('index.html')



# Login Sayfası Rotası
# Login Sayfası Rotası
# Login Sayfası Rotası
@app.route('/login', methods=['GET', 'POST'])
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
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            logging.info(f"Supabase sign_in_with_password response: {response}")

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
                # ⭐ execute() sonucu bir nesne döner, .data ile asıl veriye ulaşılır
                profile_data_response = supabase.table("users").select("*").eq("auth_id", user_id).execute()
                profile_data = profile_data_response.data  # ⭐ DÜZENLENDİ

                if profile_data and len(profile_data) > 0 and isinstance(profile_data[0], dict):
                    user_profile = profile_data[0]
                    logging.info(f"Profil bilgileri başarıyla çekildi. User ID: {user_id}")
                else:
                    logging.warning(f"Profil bilgileri çekilemedi veya eksik. Supabase yanıtı: {profile_data}")
                    user_profile = None

                session['user_id'] = user_id
                session['user_email'] = user_email
                session['user_profile'] = user_profile

                if user_profile and 'name' in user_profile:
                    display_name = user_profile.get('name', 'Kullanici')
                else:
                    display_name = user_email.split('@')[0].capitalize() if user_email else 'Kullanici'

                return redirect(url_for('profile', username=display_name))

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


# Diğer tüm rotasyonlar olduğu gibi kalacak...

# --- Diğer tüm rotasyonlar olduğu gibi kalacak ---
# ... (register, profile, index vb. rotalar) ...



# Register Sayfası Rotası
# Register Sayfası Rotası
@app.route('/register', methods=['GET', 'POST'])
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
            # 1. Kullanıcıyı Supabase Authentication ile kaydetme
            # sign_up fonksiyonunun dönüş yapısını kontrol edelim
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            logging.info(f"Supabase sign_up response: {response}") # Yanıtın yapısını görmek için

            user_id = None
            user_email_from_response = None

            # Yanıtın yapısını kontrol et (User nesnesi, tuple, veya dict olabilir)
            if hasattr(response, 'user') and response.user:
                # Eğer yanıtın doğrudan bir 'user' özelliği varsa (User nesnesi gibi)
                user_id = response.user.id
                user_email_from_response = response.user.email
                logging.info(f"Supabase Auth kaydı başarılı (User nesnesi formatında). User ID: {user_id}")
            elif isinstance(response, dict) and response.get('user'):
                # Eğer yanıt bir dict ise ve içinde 'user' anahtarı varsa
                user_id = response['user']['id']
                user_email_from_response = response['user']['email']
                logging.info(f"Supabase Auth kaydı başarılı (dict formatında). User ID: {user_id}")
            elif isinstance(response, tuple) and len(response) > 0 and isinstance(response[0], dict) and response[0].get('user'):
                # Eğer yanıt bir tuple ise ve ilk elemanı dict ise ve içinde 'user' anahtarı varsa
                user_data_from_tuple = response[0]
                user_id = user_data_from_tuple['user']['id']
                user_email_from_response = user_data_from_tuple['user']['email']
                logging.info(f"Supabase Auth kaydı başarılı (tuple formatında). User ID: {user_id}")
            else:
                # Bilinmeyen bir formatta veya user bilgisi yoksa
                logging.warning(f"Supabase Auth kaydı başarısız (beklenmedik yanıt formatı veya user bilgisi yok). Response: {response}")
                error_message = "Kayıt sırasında bir sorun oluştu. Lütfen bilgilerinizi kontrol edin."
                return render_template('register.html', error=error_message)

            # user_id başarıyla alındıysa devam et
            if user_id:
                # 2. Ek kullanıcı bilgilerini kendi 'users' tablonuza kaydetme
                user_profile_data = {
                    "auth_id": user_id,
                    "name": name,
                    "email": email
                }

                # Supabase'in table().insert() methodu ile veriyi ekle
                insert_response, _ = supabase.table("users").insert(user_profile_data).execute()

                if insert_response and len(insert_response) > 0 and insert_response[0]:
                    logging.info("Kullanıcı bilgileri veritabanına eklendi.")
                    return redirect(url_for('login'))
                else:
                    error_message = "Kullanıcı bilgileri veritabanına kaydedilirken bir sorun oluştu. Lütfen tekrar deneyin."
                    logging.error(f"Hata: Kullanıcı bilgileri veritabanına eklenemedi. Response: {insert_response}")
                    # Hata durumunda Auth'dan kullanıcıyı silme denemesi (SDK'ya göre değişir)
                    try:
                        # delete_res = supabase.auth.delete_user(user_id)
                        pass
                    except Exception as auth_del_e:
                        logging.error(f"Hata sonrası Auth kullanıcısı silinemedi: {auth_del_e}")
                    return render_template('register.html', error=error_message)
            else:
                # user_id alınamadıysa
                error_message = "Kayıt sırasında bir sorun oluştu (Kullanıcı bilgisi alınamadı). Lütfen tekrar deneyin."
                return render_template('register.html', error=error_message)

        except Exception as e:
            error_str = str(e)
            logging.error(f"Supabase kayıt hatası: {error_str}")

            if "duplicate key value violates unique constraint" in error_str or \
               "User already registered" in error_str or \
               "duplicate email" in error_str:
                 error_message = "Bu e-posta adresiyle zaten bir hesap mevcut."
            elif "Password should be at least 8 characters long" in error_str:
                 error_message = "Şifre en az 8 karakter uzunluğunda olmalı."
            else:
                 error_message = f"Kayıt sırasında bir hata oluştu: {e}"

            return render_template('register.html', error=error_message)

    return render_template('register.html')

# Profile Sayfası Rotası
@app.route('/profile/<username>')
def profile(username):
    user_id = session.get('user_id')
    if not user_id or not supabase:
        logging.warning("Profil sayfasına erişim denemesi, oturum yok veya Supabase bağlantısı yok.")
        return redirect(url_for('login'))

    user_profile = session.get('user_profile')
    
    # Supabase'den profili çekme mantığını biraz daha güvenli hale getirelim
    # Session'daki profil bilgisi hatalıysa veya yoksa, tekrar çekmeye çalışalım
    if not isinstance(user_profile, dict) or not user_profile or user_profile.get("auth_id") != user_id:
        logging.warning(f"Session'daki profil bilgisi hatalı veya eksik. User ID: {user_id}. Supabase'den tekrar çekiliyor...")
        try:
            profile_data_response, _ = supabase.table("users").select("*").eq("auth_id", user_id).execute()
            if profile_data_response and len(profile_data_response) > 0 and isinstance(profile_data_response[0], dict):
                user_profile = profile_data_response[0] # Doğru dict formatında geldi
                session['user_profile'] = user_profile # Session'ı güncelle
                logging.info(f"Profil bilgileri Supabase'den yeniden çekildi ve session'a kaydedildi. User ID: {user_id}")
            else:
                logging.error(f"Profil bilgileri Supabase'den tekrar çekilemedi. User ID: {user_id}, Response: {profile_data_response}")
                user_profile = None # Hata durumunda None yap
        except Exception as e:
            logging.error(f"Profil verisi Supabase'den çekilirken hata: {e}")
            user_profile = None # Hata durumunda None yap

    # Şimdi user_profile'ın doğru olup olmadığını kontrol edelim
    if user_profile and isinstance(user_profile, dict): # Eğer user_profile bir dict ise
        display_name = user_profile.get('name', username.capitalize()) # Name'i çek, yoksa URL'den gelen username'i kullan
        
        user_data_for_template = {
            'name': display_name,
            'role': user_profile.get('role', 'Rol Bilgisi Yok'),
            'score': user_profile.get('score', 'N/A'), # 'N/A' veya başka bir varsayılan değer
            'progress_data': [
                {'item': 'Item 1', 'value': 20},
                {'item': 'Item 2', 'value': 40},
                {'item': 'Item 3', 'value': 55},
                {'item': 'Item 4', 'value': 70},
                {'item': 'Item 5', 'value': 100},
            ]
        }
        return render_template('profile.html', user=user_data_for_template)
    else:
        # User_profile hala dict değilse veya None ise (yani profil bilgisi alınamadıysa)
        logging.warning(f"Profil bilgileri yüklenemedi. Kullanıcıyı ana sayfaya yönlendiriliyor. User ID: {user_id}")
        # Oturumu temizleyip ana sayfaya yönlendir
        session.pop('user_id', None)
        session.pop('user_profile', None)
        return redirect(url_for('index'))

# Diğer tüm rotasyonlar olduğu gibi kalacak...

# Create Interview Sayfası Rotası
@app.route('/create_interview', methods=['GET', 'POST'])
def create_interview():
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Create Interview sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        category = request.form.get('category')
        logging.info(f"Yeni mülakat oluşturma isteği: Kategori = {category}")
        if category:
            return redirect(url_for('interview_question', question_num=1, category=category))
        else:
            error_message = "Lütfen bir mülakat kategorisi seçin."
            return render_template('create_interview.html', error=error_message)

    return render_template('create_interview.html')

# Mülakat Soru Sayfası Rotası

# Logout Rotası
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_profile', None)
    logging.info("Kullanıcı çıkış yaptı.")
    return redirect(url_for('index'))

# Geçmiş Mülakatlarım Rotası (Placeholder)
@app.route('/my_interviews')
def my_interviews():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    logging.info("Geçmiş Mülakatlarım sayfasına erişildi.")
    return render_template('my_interviews.html')

# Hata Sayfası (Opsiyonel)
@app.route('/error')
def error_page():
    # message parametresiyle hata mesajı gönderilebilir.
    return render_template('error.html', message="Beklenmedik bir hata oluştu.")

# Uygulamayı çalıştırmak için
if __name__ == '__main__':
    if app.config['SECRET_KEY'] == 'varsayilan_cok_gizli_bir_anahtar_degistirmeli':
        logging.warning("FLASK_SECRET_KEY ortam değişkeni ayarlanmamış. Güvenlik için derhal değiştirin!")

    app.run(debug=True)