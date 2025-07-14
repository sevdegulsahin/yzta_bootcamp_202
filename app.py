from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client
import logging
from dotenv import load_dotenv
import os
import openai # OpenAI kütüphanesini import ettik
from openai import OpenAI # Yeni sürüm için OpenAI sınıfını import ettik
from openai import RateLimitError # Kota hatasını yakalamak için

# --- Ortam Değişkenlerini Yükleme ve Ayarlar ---
load_dotenv()

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# OpenAI API Anahtarı ve Client Oluşturma
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = None # Başlangıçta None
if not openai_api_key:
    logging.error("HATA: OPENAI_API_KEY ortam değişkeni ayarlanmamış.")
else:
    try:
        # OpenAI client'ını başlatıyoruz. OpenAI 1.0.0 ve sonrası sürümler için geçerli
        openai_client = OpenAI(api_key=openai_api_key)
        logging.info("OpenAI API başarıyla başlatıldı.")
    except Exception as e:
        logging.error(f"OpenAI API başlatılamadı: {e}")

# Supabase bağlantı bilgileri
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

# Supabase client'ını global olarak tanımla ve başlat
supabase: Client | None = None
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

# Flask Uygulaması Başlatma
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'varsayilan_cok_gizli_bir_anahtar_degistirmeli')
if app.config['SECRET_KEY'] == 'varsayilan_cok_gizli_bir_anahtar_degistirmeli':
    logging.warning("FLASK_SECRET_KEY ortam değişkeni ayarlanmamış. Güvenlik için derhal değiştirin!")

# --- Yardımcı Fonksiyonlar ---
def generate_openai_response(messages_history):
    """OpenAI modelinden (örn. gpt-3.5-turbo) yanıt üretir."""
    if not openai_client:
        logging.error("OpenAI client başlatılamadığı için yanıt üretilemiyor.")
        return "Üzgünüm, şu anda yanıt üretemiyorum (OpenAI client başlatılamadı)."
    try:
        # OpenAI API çağrısı (openai>=1.0.0 sürümü için güncellendi)
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages_history,
            max_tokens=300,
            temperature=0.7,
        )
        # Yanıtın içeriğini alırken .content attribute'u kullanılıyor
        return response.choices[0].message.content.strip()
    except RateLimitError as e: # Kota aşımı hatasını yakala
        logging.error(f"OpenAI Kota Aşıldı: {e}")
        return "Üzgünüm, şu anda hizmetimiz yoğun veya kota limitinizi aştınız. Lütfen biraz bekleyip tekrar deneyin."
    except Exception as e:
        logging.error(f"OpenAI yanıtı üretilemedi: {e}")
        return "Üzgünüm, şu anda bir yanıt üretemiyorum."

def generate_single_openai_question(prompt):
    """Tek bir soru üretmek için OpenAI'yi kullanır."""
    if not openai_client:
        logging.error("OpenAI client başlatılamadığı için soru üretilemiyor.")
        return "Şu anda yapay zeka destekli soru üretilemiyor (OpenAI client başlatılamadı)."
    try:
        # OpenAI API çağrısı (openai>=1.0.0 sürümü için güncellendi)
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen bir teknik mülakat sorusu üreten asistansın. Sadece soruyu ver, ek açıklama yapma."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7,
        )
        # Yanıtın içeriğini alırken .content attribute'u kullanılıyor
        return response.choices[0].message.content.strip()
    except RateLimitError as e: # Kota aşımı hatasını yakala
        logging.error(f"OpenAI Kota Aşıldı (Soru Üretimi): {e}")
        return "Üzgünüm, şu anda hizmetimiz yoğun veya kota limitinizi aştınız. Lütfen biraz bekleyip tekrar deneyin."
    except Exception as e:
        logging.error(f"YZ ile mülakat sorusu üretilemedi: {e}")
        return "Şu anda yapay zeka destekli soru üretilemiyor."


# --- Rotalar ---
ALLOWED_CATEGORIES = [
    "frontend",
    "backend",
    "mobile",
    "devops",
    "data_science",
    "general"
]

@app.route('/interview', methods=['GET', 'POST'])
def interview():
    """Mülakat simülasyonu ana sayfası."""
    # Eğer oturumda chat_history yoksa, varsayılan başlangıç mesajlarını ayarla
    if 'chat_history' not in session:
        session['chat_history'] = [
            {"role": "system", "content": "Sen bir iş görüşmesi yapan uzman bir mülakatçı gibisin. Adaya nazikçe ve profesyonelce yaklaş."},
            {"role": "assistant", "content": "Merhaba! Mülakat simülasyonuna hoş geldiniz. Bana biraz kendinizden bahseder misiniz?"}
        ]

    # POST isteği (kullanıcı mesaj gönderdiğinde)
    if request.method == 'POST':
        user_input = request.form.get('user_input')
        if user_input: # Eğer boş mesaj gönderilmediyse
            # Kullanıcının girdisini oturuma ekle
            session['chat_history'].append({"role": "user", "content": user_input})

            # OpenAI'den yanıt al
            ai_reply = generate_openai_response(session['chat_history'])

            # Yapay zekanın yanıtını oturuma ekle
            session['chat_history'].append({"role": "assistant", "content": ai_reply})
            session.modified = True # Oturumu güncellemek için önemli

        else:
             # Boş mesaj gönderildiyse, sayfayı yeniden yönlendir (değişiklik yok)
             return redirect(url_for('interview'))

    # GET isteği veya POST sonrası sayfayı render et
    return render_template('interview.html', chat_history=session.get('chat_history', []))


@app.route('/interview/reset')
def reset_interview():
    """Mülakat oturumunu sıfırlar."""
    session.pop('chat_history', None) # Oturumdaki mülakat geçmişini sil
    logging.info("Mülakat oturumu sıfırlandı.")
    return redirect(url_for('interview')) # Mülakat sayfasına geri yönlendir

# Belirli bir kategori ve soru numarası için soru üretme rotası
@app.route('/interview/<category>/<int:question_num>')
def interview_question_route(category, question_num):
    """Belirli bir kategoriye ait rastgele mülakat sorusu üretir."""
    user_id = session.get('user_id')
    # Eğer kullanıcı giriş yapmamışsa, giriş sayfasına yönlendir
    if not user_id:
        logging.warning("Mülakat sorusu sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('login'))

    # Geçerli kategoriyi kontrol et
    if category not in ALLOWED_CATEGORIES:
        logging.error(f"Geçersiz mülakat kategorisi istendi: {category}")
        return render_template('error.html', message="Geçersiz mülakat kategorisi."), 404

    try:
        # OpenAI için prompt oluştur
        prompt = f"'{category}' alanında bir iş mülakatı için {question_num}. soru olarak sormak üzere düşündürücü ve teknik bir soru üret."

        # OpenAI API'den soruyu al
        ai_question = generate_single_openai_question(prompt)

        # Eğer soru üretilemediyse hata mesajı göster
        if "Üzgünüm" in ai_question or "üretilemiyor" in ai_question:
            return render_template('error.html', message=ai_question)

        # Soruyu gösteren şablona yönlendir (interview_question.html)
        return render_template('interview_question.html',
                               question_num=question_num,
                               total_questions=5, # Toplam soru sayısını varsayılan olarak 5 alıyoruz, bunu değiştirebilirsiniz
                               question_text=ai_question,
                               category=category)
    except Exception as e:
        logging.exception("YZ ile mülakat sorusu üretilemedi")
        return render_template('error.html', message="Yapay zeka soruyu oluşturamadı.")


@app.route('/')
def index():
    """Ana sayfa rotası."""
    # Kullanıcı giriş yapmışsa, profiline yönlendir
    if 'user_id' in session:
        profile = session.get('user_profile')
        if profile and 'name' in profile:
            return redirect(url_for('profile', username=profile['name']))
        else:
            # Profil bilgisi yoksa oturumu temizle ve giriş yapmasını iste
            session.clear()
            return redirect(url_for('login'))
    # Giriş yapmamışsa ana sayfa şablonunu göster
    return render_template('index.html')


# Login Sayfası Rotası
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        logging.info(f"Login POST isteği alındı: E-posta={email}")

        # Gerekli alanların doldurulup doldurulmadığını kontrol et
        if not email or not password:
            error_message = "Lütfen e-posta ve şifrenizi girin."
            return render_template('login.html', error=error_message)

        # Supabase bağlantısı kontrolü
        if not supabase:
            error_message = "Sunucu hatası: Supabase bağlantısı kurulamadı."
            return render_template('login.html', error=error_message)

        try:
            # Supabase ile kullanıcı girişi yap
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})

            user_id = None
            user_email = None
            user_profile = None

            # Giriş başarılıysa user bilgilerini al
            if response and hasattr(response, 'user') and response.user:
                user_id = response.user.id
                user_email = response.user.email
                logging.info(f"Oturum açma başarılı. User ID: {user_id}, E-posta: {user_email}")
            else:
                error_message = "Hatalı e-posta veya şifre. Lütfen tekrar deneyin."
                logging.warning("Oturum açma başarısız. Kullanıcı nesnesi bulunamadı.")
                return render_template('login.html', error=error_message)

            # Kullanıcı ID'si alındıysa, profil bilgilerini Supabase'den çek
            if user_id:
                profile_data_response = supabase.table("users").select("*").eq("auth_id", user_id).execute()
                profile_data = profile_data_response.data

                # Profil verisi varsa, user_profile'ı güncelle
                if profile_data and isinstance(profile_data, list) and len(profile_data) > 0 and isinstance(profile_data[0], dict):
                    user_profile = profile_data[0]
                    logging.info(f"Profil bilgileri başarıyla çekildi. User ID: {user_id}")
                else:
                    logging.warning(f"Profil bilgileri çekilemedi veya eksik. Supabase yanıtı: {profile_data}")
                    user_profile = None # Profil yoksa None olarak bırak

                # Oturum değişkenlerini ayarla
                session['user_id'] = user_id
                session['user_email'] = user_email
                session['user_profile'] = user_profile

                # Profildeki isme göre yönlendir, yoksa email'den türetilmiş bir isim kullan
                display_name = user_profile.get('name', user_email.split('@')[0].capitalize() if user_email else 'Kullanici')
                return redirect(url_for('profile', username=display_name))

            else:
                # Kullanıcı ID alınamadıysa hata mesajı göster
                error_message = "Kullanıcı bilgileri alınamadı. Lütfen tekrar deneyin."
                return render_template('login.html', error=error_message)

        except Exception as e:
            # Giriş sırasında oluşan hataları yakala ve logla
            logging.error(f"Supabase oturum açma hatası: {e}")
            error_str = str(e)
            # Hata mesajlarına göre daha spesifik geri bildirimler ver
            if "invalid login credentials" in error_str or "invalid grant" in error_str:
                error_message = "Hatalı e-posta veya şifre. Lütfen tekrar deneyin."
            else:
                error_message = f"Giriş sırasında bir hata oluştu: {e}"
            return render_template('login.html', error=error_message)

    # GET isteği için login şablonunu göster
    return render_template('login.html')


# Register Sayfası Rotası
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Formdan kullanıcı bilgilerini al
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Alanların doldurulmasını kontrol et
        if not name or not email or not password or not confirm_password:
            error_message = "Lütfen tüm alanları doldurun."
            return render_template('register.html', error=error_message)

        # Şifrelerin eşleşip eşleşmediğini kontrol et
        if password != confirm_password:
            error_message = "Şifreler uyuşmuyor."
            return render_template('register.html', error=error_message)

        # Supabase bağlantısını kontrol et
        if not supabase:
            error_message = "Sunucu hatası: Supabase bağlantısı kurulamadı."
            return render_template('register.html', error=error_message)

        try:
            # 1. Kullanıcıyı Supabase Authentication ile kaydet
            response = supabase.auth.sign_up({"email": email, "password": password})

            user_id = None
            user_email_from_response = None

            # Kayıt başarılıysa kullanıcı bilgilerini al
            if response and hasattr(response, 'user') and response.user:
                user_id = response.user.id
                user_email_from_response = response.user.email
                logging.info(f"Supabase Auth kaydı başarılı. User ID: {user_id}")
            else:
                # Kayıt başarısızsa hata mesajı göster
                logging.warning(f"Supabase Auth kaydı başarısız veya beklenmedik yanıt. Response: {response}")
                error_message = "Kayıt sırasında bir sorun oluştu. Lütfen bilgilerinizi kontrol edin."
                return render_template('register.html', error=error_message)

            # Kullanıcı ID alındıysa, ek bilgileri kendi 'users' tablosuna kaydet
            if user_id:
                user_profile_data = {"auth_id": user_id, "name": name, "email": email}
                # Supabase'e veri ekle
                insert_response, _ = supabase.table("users").insert(user_profile_data).execute()

                # Ekleme başarılıysa kullanıcıyı login sayfasına yönlendir
                if insert_response and len(insert_response) > 0 and insert_response[0]:
                    logging.info("Kullanıcı bilgileri veritabanına eklendi.")
                    return redirect(url_for('login'))
                else:
                    # Veritabanına ekleme başarısız olursa hata mesajı göster ve Auth'dan kullanıcıyı sil
                    error_message = "Kullanıcı bilgileri veritabanına kaydedilirken bir sorun oluştu. Lütfen tekrar deneyin."
                    logging.error(f"Hata: Kullanıcı bilgileri veritabanına eklenemedi. Response: {insert_response}")
                    try:
                        supabase.auth.delete_user(user_id) # Hata durumunda kullanıcıyı sil
                        logging.info(f"Hata sonrası silinen kullanıcı (Auth ID): {user_id}")
                    except Exception as auth_del_e:
                        logging.error(f"Hata sonrası Auth kullanıcısı silinemedi: {auth_del_e}")
                    return render_template('register.html', error=error_message)
            else:
                # Kullanıcı ID alınamadıysa hata mesajı göster
                error_message = "Kayıt sırasında bir sorun oluştu (Kullanıcı bilgisi alınamadı). Lütfen tekrar deneyin."
                return render_template('register.html', error=error_message)

        except Exception as e:
            # Kayıt sırasında oluşan hataları yakala ve logla
            error_str = str(e)
            logging.error(f"Supabase kayıt hatası: {error_str}")
            # Hata mesajlarına göre kullanıcıya özel geri bildirimler
            if "duplicate key value violates unique constraint" in error_str or "User already registered" in error_str or "duplicate email" in error_str:
                 error_message = "Bu e-posta adresiyle zaten bir hesap mevcut."
            elif "Password should be at least 8 characters long" in error_str:
                 error_message = "Şifre en az 8 karakter uzunluğunda olmalı."
            else:
                 error_message = f"Kayıt sırasında bir hata oluştu: {e}"
            return render_template('register.html', error=error_message)

    # GET isteği için register şablonunu göster
    return render_template('register.html')

# Profile Sayfası Rotası
@app.route('/profile/<username>')
def profile(username):
    user_id = session.get('user_id')
    # Kullanıcı giriş yapmamışsa giriş sayfasına yönlendir
    if not user_id:
        logging.warning("Profil sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('login'))

    user_profile = session.get('user_profile')

    # Oturumdaki profil bilgisi eksikse veya hatalıysa Supabase'den tekrar çek
    if not isinstance(user_profile, dict) or not user_profile or user_profile.get("auth_id") != user_id:
        logging.warning(f"Session'daki profil bilgisi hatalı veya eksik. User ID: {user_id}. Supabase'den tekrar çekiliyor...")
        try:
            # Supabase'den kullanıcı profilini çek
            profile_data_response = supabase.table("users").select("*").eq("auth_id", user_id).execute()
            profile_data = profile_data_response.data

            # Profil verisi varsa, oturumu güncelle
            if profile_data and isinstance(profile_data, list) and len(profile_data) > 0 and isinstance(profile_data[0], dict):
                user_profile = profile_data[0]
                session['user_profile'] = user_profile
                logging.info(f"Profil bilgileri Supabase'den yeniden çekildi. User ID: {user_id}")
            else:
                # Profil verisi çekilemezse hata logla ve user_profile'ı None yap
                logging.error(f"Profil bilgileri Supabase'den tekrar çekilemedi. User ID: {user_id}, Response: {profile_data}")
                user_profile = None
        except Exception as e:
            # Veri çekme sırasında hata olursa logla ve user_profile'ı None yap
            logging.error(f"Profil verisi Supabase'den çekilirken hata: {e}")
            user_profile = None

    # Profil bilgileri başarıyla çekildiyse, şablonu render et
    if user_profile and isinstance(user_profile, dict):
        # Gösterilecek adı belirle (profildeki isim veya URL'den alınan isim)
        display_name = user_profile.get('name', username.capitalize())
        # Şablona gönderilecek verileri hazırla
        user_data_for_template = {
            'name': display_name,
            'role': user_profile.get('role', 'Rol Bilgisi Yok'), # Örnek alanlar
            'score': user_profile.get('score', 'N/A'),
            'progress_data': [ # Örnek ilerleme grafiği verileri
                {'item': 'Frontend Bilgisi', 'value': user_profile.get('frontend_score', 0)},
                {'item': 'Backend Bilgisi', 'value': user_profile.get('backend_score', 0)},
                {'item': 'Mobile Bilgisi', 'value': user_profile.get('mobile_score', 0)},
            ]
        }
        return render_template('profile.html', user=user_data_for_template)
    else:
        # Profil bilgisi alınamadıysa oturumu temizle ve ana sayfaya yönlendir
        logging.warning(f"Profil bilgileri yüklenemedi. Kullanıcıyı ana sayfaya yönlendiriliyor. User ID: {user_id}")
        session.clear()
        return redirect(url_for('index'))


# Yeni Mülakat Oluşturma Sayfası Rotası
@app.route('/create_interview', methods=['GET', 'POST'])
def create_interview():
    user_id = session.get('user_id')
    # Kullanıcı giriş yapmamışsa giriş sayfasına yönlendir
    if not user_id:
        logging.warning("Create Interview sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        category = request.form.get('category') # Seçilen kategori
        logging.info(f"Yeni mülakat oluşturma isteği: Kategori = {category}")
        if category:
            # Kategori seçildiyse, mülakatı başlatmak için ilk soruya yönlendir
            return redirect(url_for('interview_question_route', question_num=1, category=category))
        else:
            # Kategori seçilmediyse hata mesajı göster
            error_message = "Lütfen bir mülakat kategorisi seçin."
            return render_template('create_interview.html', error=error_message, categories=ALLOWED_CATEGORIES)

    # GET isteği için create_interview şablonunu göster
    return render_template('create_interview.html', categories=ALLOWED_CATEGORIES)


# Logout Rotası
@app.route('/logout')
def logout():
    """Kullanıcının oturumunu kapatır."""
    session.pop('user_id', None) # User ID'yi oturumdan kaldır
    session.pop('user_profile', None) # Profil bilgilerini oturumdan kaldır
    session.pop('chat_history', None) # Mülakat geçmişini de temizle
    logging.info("Kullanıcı çıkış yaptı.")
    return redirect(url_for('login')) # Çıkış sonrası login sayfasına yönlendir

# Geçmiş Mülakatlarım Rotası (Placeholder)
@app.route('/my_interviews')
def my_interviews():
    user_id = session.get('user_id')
    # Kullanıcı giriş yapmamışsa giriş sayfasına yönlendir
    if not user_id:
        return redirect(url_for('login'))
    logging.info("Geçmiş Mülakatlarım sayfasına erişildi.")
    # Bu sayfada kullanıcının geçmiş mülakatlarını Supabase'den çekip listelemek gerekir.
    # Şimdilik sadece bir placeholder mesajı döndürelim.
    return render_template('my_interviews.html', user_id=user_id)

# Hata Sayfası (Opsiyonel)
@app.route('/error')
def error_page():
    """Genel hata mesajı gösterir."""
    # message parametresiyle gönderilen hata mesajını şablona aktar
    return render_template('error.html', message="Beklenmedik bir hata oluştu.")

# Uygulamayı çalıştırmak için ana blok
if __name__ == '__main__':
    # Geliştirme ortamında gizli anahtarın ayarlanmadığına dair uyarı
    if app.config['SECRET_KEY'] == 'varsayilan_cok_gizli_bir_anahtar_degistirmeli':
        logging.warning("FLASK_SECRET_KEY ortam değişkeni ayarlanmamış. Güvenlik için derhal değiştirin!")
    # API anahtarlarının eksikliği durumunda uyarılar
    if not openai_api_key:
        logging.error("OPENAI_API_KEY ayarlı değil, OpenAI özellikleri çalışmayacaktır.")
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        logging.error("Supabase URL veya Anon Key ayarlı değil, Supabase özellikleri çalışmayacaktır.")

    # Flask uygulamasını çalıştır (debug=True geliştirme için kullanışlıdır)
    app.run(debug=True)