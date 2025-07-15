import logging
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client
import os
import openai
from openai import OpenAI
from openai import RateLimitError
import uuid
import re 
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = None
if not openai_api_key:
    logging.error("HATA: OPENAI_API_KEY ortam değişkeni ayarlanmamış.")
else:
    try:
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


def generate_openai_response(messages_history):
    if not openai_client:
        logging.error("OpenAI client başlatılamadığı için yanıt üretilemiyor.")
        return "Üzgünüm, şu anda yanıt üretemiyorum (OpenAI client başlatılamadı)."
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages_history,
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except RateLimitError as e:
        logging.error(f"OpenAI Kota Aşıldı: {e}")
        return "Üzgünüm, şu anda hizmetimiz yoğun veya kota limitinizi aştınız. Lütfen biraz bekleyip tekrar deneyin."
    except Exception as e:
        logging.error(f"OpenAI yanıtı üretilemedi: {e}")
        return "Üzgünüm, şu anda bir yanıt üretemiyorum."

def generate_single_openai_question(prompt):
    if not openai_client:
        logging.error("OpenAI client başlatılamadığı için soru üretilemiyor.")
        return "Şu anda yapay zeka destekli soru üretilemiyor (OpenAI client başlatılamadı)."
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen bir teknik mülakat sorusu üreten asistansın. Sadece soruyu ver, ek açıklama yapma."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except RateLimitError as e:
        logging.error(f"OpenAI Kota Aşıldı (Soru Üretimi): {e}")
        return "Üzgünüm, şu anda hizmetimiz yoğun veya kota limitinizi aştınız. Lütfen biraz bekleyip tekrar deneyin."
    except Exception as e:
        logging.error(f"YZ ile mülakat sorusu üretilemedi: {e}")
        return "Şu anda yapay zeka destekli soru üretilemiyor."

def save_question_to_supabase(category, question_text, user_id, question_type=None):
    if not supabase:
        logging.error("Supabase bağlantısı yok, soru kaydedilemiyor.")
        return None
    try:
        if category is None:
            logging.warning("save_question_to_supabase fonksiyonuna category=None ile çağrı yapıldı. Varsayılan olarak 'general' kullanılıyor.")
            category = 'general' 

        question_data = {
            "category": category,
            "question_text": question_text,
            "user_id": str(user_id),
            "question_type": question_type
        }
        response = supabase.table("interview_questions").insert(question_data).execute()
        data = response.data

        if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            new_question_id = data[0].get('id')
            if new_question_id:
                logging.info(f"Soru başarıyla kaydedildi. ID: {new_question_id}, Kategori: {category}, Tür: {question_type}")
                return new_question_id
            else:
                logging.warning(f"Soru kaydedildi ancak ID bulunamadı: {data[0]}")
        else:
            logging.error(f"Supabase yanıtı boş veya beklenmeyen formatta: {data}")
        return None
    except Exception as e:
        logging.error(f"Supabase'e soru kaydederken hata: {e}")
        return None

def save_answer_to_supabase(question_id, user_id, user_answer, ai_response=None, selected_option=None, is_correct=None):
    if not supabase:
        logging.error("Supabase bağlantısı yok, cevap kaydedilemiyor.")
        return None
    try:
        answer_data = {
            "question_id": str(question_id),
            "user_id": str(user_id),
            "user_answer": user_answer,
            "ai_response": ai_response,
            "selected_option": selected_option,
            "is_correct": is_correct
        }
        response = supabase.table("interview_answers").insert(answer_data).execute()

        if response and response.data and isinstance(response.data, list) and len(response.data) > 0:
            logging.info(f"Cevap başarıyla Supabase'e kaydedildi. ID: {response.data[0].get('id')}")
            return response.data[0].get('id')
        else:
            logging.warning(f"Supabase insert yanıtı beklenenden farklı veya boş. Response: {response}")
            return None
    except Exception as e:
        logging.error(f"Supabase'e cevap kaydederken hata: {e}")
        return None


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
    """Mülakat simülasyonu ana sayfası (chatbot modu)."""
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Chatbot mülakatına erişim denemesi, oturum yok.")
        return redirect(url_for('login'))

    if 'chat_history' not in session:
        session['chat_history'] = [
            {"role": "system", "content": "Sen bir iş görüşmesi yapan uzman bir mülakatçı gibisin. Adaya nazikçe ve profesyonelce yaklaş."},
            {"role": "assistant", "content": "Merhaba! Mülakat simülasyonuna hoş geldiniz. Bana biraz kendinizden bahseder misiniz?"}
        ]
        session['current_question_id'] = None 

    if request.method == 'POST':
        user_input = request.form.get('user_input')
        if user_input:
            session['chat_history'].append({"role": "user", "content": user_input})

            ai_reply = generate_openai_response(session['chat_history'])
            session['chat_history'].append({"role": "assistant", "content": ai_reply})
            session.modified = True

            current_question_id = session.get('current_question_id')
            if current_question_id:
                pass 
            else:
                logging.warning("current_question_id yok, bu cevap interview_answers tablosuna kaydedilmedi (chatbot modu).")

        else:
             return redirect(url_for('interview'))

    return render_template('interview.html', chat_history=session.get('chat_history', []))


@app.route('/interview/reset')
def reset_interview():
    session.pop('chat_history', None)
    session.pop('current_question_id', None)
    logging.info("Chatbot mülakat oturumu ve soru ID'si sıfırlandı.")
    return redirect(url_for('interview'))

@app.route('/interview/<category>/<int:question_num>')
def interview_question_route(category, question_num):
    """Belirli bir kategoriye ait rastgele mülakat sorusu üretir (teknik chatbot modu için)."""
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Mülakat sorusu sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('login'))

    if category not in ALLOWED_CATEGORIES:
        logging.error(f"Geçersiz mülakat kategorisi istendi: {category}")
        return render_template('error.html', message="Geçersiz mülakat kategorisi."), 404

    try:
        prompt = f"'{category}' alanında bir iş mülakatı için düşündürücü ve teknik bir soru üret. Sadece soruyu ver, ek açıklama veya formatlama yapma."
        ai_question = generate_single_openai_question(prompt)

        if "Üzgünüm" in ai_question or "üretilemiyor" in ai_question:
            logging.error(f"OpenAI soru üretme hatası: {ai_question}")
            return render_template('error.html', message=ai_question)

        new_question_id = save_question_to_supabase(category, ai_question, user_id, question_type='chatbot_technical') # question_type'ı burada belirtiyoruz

        if not new_question_id:
            logging.error("Soru Supabase'e kaydedilemedi veya ID'si alınamadı.")
            return render_template('error.html', message="Soru kaydedilirken bir hata oluştu.")

        session['current_question_id'] = new_question_id
        logging.info(f"Teknik soru kaydedildi. ID: {new_question_id}. Kullanıcıdan cevap bekleniyor.")

        return render_template('interview_question.html',
                               question_num=question_num,
                               total_questions=5, # Bu sabit değerler güncellenebilir
                               question_text=ai_question,
                               category=category)
    except Exception as e:
        logging.exception("YZ ile mülakat sorusu üretilemedi veya kaydedilemedi")
        return render_template('error.html', message="Yapay zeka soruyu oluşturamadı veya kaydedemedi.")


@app.route('/')
def index():
    """Ana sayfa rotası."""
    if 'user_id' in session:
        profile = session.get('user_profile')
        if profile and 'name' in profile:
            return redirect(url_for('profile', username=profile['name']))
        else:
            session.clear()
            return redirect(url_for('login'))
    return render_template('index.html')


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
                    return redirect(url_for('login'))
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

@app.route('/profile/<username>')
def profile(username):
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Profil sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('login'))

    user_profile = session.get('user_profile')

    if not isinstance(user_profile, dict) or not user_profile or user_profile.get("auth_id") != user_id:
        logging.warning(f"Session'daki profil bilgisi hatalı veya eksik. User ID: {user_id}. Supabase'den tekrar çekiliyor...")
        try:
            profile_data_response = supabase.table("users").select("*").eq("auth_id", user_id).execute()
            profile_data = profile_data_response.data

            if profile_data and isinstance(profile_data, list) and len(profile_data) > 0 and isinstance(profile_data[0], dict):
                user_profile = profile_data[0]
                session['user_profile'] = user_profile
                logging.info(f"Profil bilgileri Supabase'den yeniden çekildi. User ID: {user_id}")
            else:
                logging.error(f"Profil bilgileri Supabase'den tekrar çekilemedi. User ID: {user_id}, Response: {profile_data}")
                user_profile = None
        except Exception as e:
            logging.error(f"Profil verisi Supabase'den çekilirken hata: {e}")
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
        logging.warning(f"Profil bilgileri yüklenemedi. Kullanıcıyı ana sayfaya yönlendiriliyor. User ID: {user_id}")
        session.clear()
        return redirect(url_for('index'))


@app.route('/create_interview', methods=['GET', 'POST'])
def create_interview():
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Create Interview sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        mode_choice = request.form.get('mode_choice') # Genel Yetenek / Teknik
        interview_type = request.form.get('interview_type') # Asistan / Yazılı Test
        technical_area = request.form.get('technical_area') # Sadece Teknik mod seçilirse

        session['selected_interview_type'] = interview_type
        session['selected_mode'] = mode_choice
        session['selected_technical_area'] = technical_area

        if not interview_type:
            error_message = "Lütfen bir mülakat türü seçin (Asistan veya Yazılı Test)."
            return render_template('create_interview.html', error=error_message, categories=ALLOWED_CATEGORIES)

        if not mode_choice:
            error_message = "Lütfen bir mülakat modu seçin (Genel Yetenek veya Teknik)."
            return render_template('create_interview.html', error=error_message, categories=ALLOWED_CATEGORIES, selected_interview_type=interview_type)

        if mode_choice == 'technical' and not technical_area:
            error_message = "Teknik mülakat/test için lütfen bir alan seçin."
            return render_template('create_interview.html', error=error_message, categories=ALLOWED_CATEGORIES, selected_interview_type=interview_type, selected_mode=mode_choice)

        if interview_type == 'assistant':
            if mode_choice == 'general':
                session['current_interview_category'] = None
                session['current_question_id'] = None
                return redirect(url_for('interview'))
            elif mode_choice == 'technical':
                session['current_interview_category'] = technical_area
                session['current_question_id'] = None
                return redirect(url_for('interview_question_route', category=technical_area, question_num=1)) 
        elif interview_type == 'written_test':
            session['selected_written_test_types'] = ['open_ended']
            session['total_written_test_questions'] = 10 

            if mode_choice == 'general':
                session['selected_category_for_test'] = None 
                return redirect(url_for('start_written_test', category=None, question_num=1))
            elif mode_choice == 'technical':
                session['selected_category_for_test'] = technical_area 
                return redirect(url_for('start_written_test', category=technical_area, question_num=1))

    selected_interview_type = session.get('selected_interview_type', None)
    selected_mode = session.get('selected_mode', None)
    selected_technical_area = session.get('selected_technical_area', None)

    return render_template('create_interview.html',
                           categories=ALLOWED_CATEGORIES,
                           selected_interview_type=selected_interview_type,
                           selected_mode=selected_mode,
                           selected_technical_area=selected_technical_area)


@app.route('/start_written_test', methods=['GET', 'POST'])
def start_written_test():
    user_id = session.get('user_id')
   
    category_from_request = request.args.get('category')
    question_num = int(request.args.get('question_num', 1))

    total_questions_in_session = session.get('total_written_test_questions', 10) 

    if not user_id:
        logging.warning("Yazılı test başlatma denemesi, oturum yok.")
        return redirect(url_for('login'))

    if question_num > total_questions_in_session:
        logging.info(f"Tüm {total_questions_in_session} test soruları tamamlandı. Sonuç sayfasına yönlendiriliyor.")

        current_category_for_result = category_from_request if category_from_request is not None else session.get('selected_category_for_test', 'general')
        return redirect(url_for('test_results', category=current_category_for_result)) 

    current_category = category_from_request
    if current_category is None:
        current_category = session.get('selected_category_for_test')
    if current_category is None:
        current_category = 'general' 

    logging.info(f"Mevcut kategori: {current_category}, Soru Numarası: {question_num}")

    question_type_to_generate = 'open_ended'
    category_desc = f"'{current_category}' alanı" if current_category else "genel yetenek"
    prompt = f"'{category_desc}' ile ilgili, yeni bir iş mülakatı için düşündürücü ve açıklayıcı bir açık uçlu soru üret. Sadece sorunun metnini ver. Sorunun zorluk seviyesi orta düzeyde olmalı."

    current_question_text = generate_single_openai_question(prompt)
    parsed_question_data = {'question': current_question_text}

    if not parsed_question_data or 'question' not in parsed_question_data:
        logging.error(f"AI soru çıktısı ayrıştırılamadı: {current_question_text}")
        return render_template('error.html', message="AI'dan gelen soru formatı bozuk.")

    current_question_text = parsed_question_data['question']
    
    new_question_id = save_question_to_supabase(current_category, current_question_text, user_id, question_type=question_type_to_generate)

    if not new_question_id:
        logging.error(f"Soru Supabase'e kaydedilemedi. Kategori: {current_category}")
        return render_template('error.html', message="Soru kaydedilirken bir hata oluştu.")

    session['current_test_question_data'] = parsed_question_data
    session['current_test_question_id'] = new_question_id 
    session['current_test_question_num'] = question_num 
    session['current_test_question_type'] = question_type_to_generate
    session['current_test_category'] = current_category
    session.modified = True

    return render_template('written_test_question.html',
                           question_num=question_num,
                           total_questions=total_questions_in_session, 
                           question_text=current_question_text,
                           category=current_category, 
                           question_type=question_type_to_generate,
                           parsed_data=parsed_question_data)


def parse_ai_question_response(ai_response, question_type):
    parsed = {'question': ai_response} 
    return parsed

@app.route('/submit_written_answer', methods=['POST'])
def submit_written_answer():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    question_id = session.get('current_test_question_id')
    question_type = session.get('current_test_question_type')
    category = session.get('current_test_category') 
    question_num = session.get('current_test_question_num')
    total_questions = session.get('total_written_test_questions', 10) 

    user_answer_input = request.form.get('user_answer') 

    if not question_id:
        logging.error("Cevap gönderilemedi: Mevcut soru ID'si session'da bulunamadı.")
        return render_template('error.html', message="Cevap gönderilemedi: Soru bilgisi bulunamadı.")

    ai_evaluation_result = None

    response = save_answer_to_supabase(
        question_id=str(question_id),
        user_id=str(user_id),
        user_answer=user_answer_input,
        is_correct=ai_evaluation_result
    )

    if response:
        completed_questions_data = session.get('completed_test_questions_data', [])
        completed_questions_data.append({
            'question_text': session.get('current_test_question_data', {}).get('question'),
            'user_answer': user_answer_input,
            'question_type': question_type,
            'is_correct': ai_evaluation_result # None
        })
        session['completed_test_questions_data'] = completed_questions_data
        session.modified = True

        next_question_num = question_num + 1

        if next_question_num > total_questions:
            logging.info(f"Tüm {total_questions} test soruları tamamlandı. Sonuç sayfasına yönlendiriliyor.")
            session.pop('current_test_question_data', None)
            session.pop('current_test_question_id', None)
            session.pop('current_test_question_num', None)
            session.pop('current_test_question_type', None)
            session.pop('current_test_category', None)
            session.modified = True
         
            return redirect(url_for('test_results', category=category))
        else:
         
            return redirect(url_for('start_written_test', category=category, question_num=next_question_num))
    else:
        logging.error(f"Cevap Supabase'e kaydedilemedi. Soru ID: {question_id}")
        return render_template('error.html', message="Cevabınız kaydedilemedi. Lütfen tekrar deneyin.")


@app.route('/test_results')
def test_results():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
  
    category = request.args.get('category') 

    completed_test_questions_data = session.get('completed_test_questions_data', [])

    if not completed_test_questions_data:
        logging.warning("Test sonuçları getirilemedi: Tamamlanan test verileri eksik.")
        session.clear() 
        return redirect(url_for('index'))

    detailed_answers = []
    total_questions_in_test = len(completed_test_questions_data)

    for item in completed_test_questions_data:
        user_response_display = item.get('user_answer')
        if user_response_display is None or user_response_display.strip() == "":
            user_response_display = "Cevap verilmedi"

        detailed_answers.append({
            'question_text': item.get('question_text', 'Soru Metni Yok'),
            'user_response': user_response_display,
            'is_correct': item.get('is_correct') # Bu None olacak
        })

    score = "Değerlendirilecek"
    success_rate = "Değerlendirilecek"
    correct_answers_count = "Değerlendirilecek" 

    results_data = {
        'total_questions': total_questions_in_test,
        'correct_answers': correct_answers_count,
        'success_rate': success_rate,
        'score': score,
        'detailed_answers': detailed_answers
    }

    session.pop('selected_written_test_types', None)
    session.pop('selected_category_for_test', None)
    session.pop('total_written_test_questions', None) 
    session.pop('current_test_question_index', None) 
    session.pop('current_test_question_data', None)
    session.pop('current_test_question_id', None)
    session.pop('current_test_question_num', None)
    session.pop('current_test_question_type', None)
    session.pop('current_test_category', None)
    session.pop('completed_test_questions_data', None)
    session.modified = True

    return render_template('test_results.html',
                           username=session.get('user_profile', {}).get('name', 'Kullanıcı'),
                           category=category, 
                           total_questions_asked=results_data['total_questions'],
                           correct_answers_count=results_data['correct_answers'],
                           score=results_data['score'],
                           detailed_answers=results_data['detailed_answers'],
                           is_open_ended_test=True) 

@app.route('/logout')
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
    return redirect(url_for('login'))

@app.route('/my_interviews')
def my_interviews():
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Geçmiş mülakatlar sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('login'))

    if not supabase:
        logging.error("Supabase bağlantısı yok, geçmiş mülakatlar gösterilemiyor.")
        return render_template('error.html', message="Supabase bağlantısı kurulamadı.")

    try:
        logging.info(f"Geçmiş mülakatlar için user_id: {user_id}") 

        questions_response = supabase.table("interview_questions") \
                                     .select("id, category, question_text, generated_at, question_type") \
                                     .eq("user_id", str(user_id)) \
                                     .order("generated_at.desc") \
                                     .execute()
        
        questions = questions_response.data
        logging.info(f"interview_questions tablosundan çekilen soru sayısı: {len(questions) if questions else 0}")

        mullakatlar_detayli = []
        if questions:
            for q in questions:
                question_id = q.get('id')
                logging.info(f"İşlenen soru ID: {question_id}, Kategori: {q.get('category')}") 
                if question_id:
                    answers_response = supabase.table("interview_answers") \
                                               .select("id, user_answer, ai_response, selected_option, is_correct, answered_at") \
                                               .eq("question_id", str(question_id)) \
                                               .order("answered_at.asc") \
                                               .execute()
                    
                    answers = answers_response.data if answers_response and answers_response.data else []
                    logging.info(f"Soru ID {question_id} için çekilen cevap sayısı: {len(answers)}") 
                    
                    mullakat_detay = q.copy()
                    mullakat_detay['answers'] = answers
                    mullakatlar_detayli.append(mullakat_detay)
                else:
                    logging.warning(f"Soru ID'si alınamadı, cevaplar çekilemedi: {q}")
        
        logging.info(f"Toplam işlenen mülakat detayı: {len(mullakatlar_detayli)}") 
        
        return render_template('my_interviews.html', mülakatlar=mullakatlar_detayli)

    except Exception as e:
        logging.error(f"Supabase'den geçmiş mülakatlar çekilirken hata: {e}", exc_info=True)
        return render_template('error.html', message="Geçmiş mülakatlar getirilemedi.")

@app.route('/error')
def error_page():
    return render_template('error.html', message="Beklenmedik bir hata oluştu.")

if __name__ == '__main__':
    if not openai_api_key:
        logging.error("OPENAI_API_KEY ayarlı değil, OpenAI özellikleri çalışmayacaktır.")
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        logging.error("Supabase URL veya Anon Key ayarlı değil, Supabase özellikleri çalışmayacaktır.")

    app.run(debug=True)