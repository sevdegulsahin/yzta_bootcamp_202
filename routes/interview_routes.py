from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from services.openai_service import generate_openai_response, generate_single_openai_question
from services.supabase_service import save_question_to_supabase, save_answer_to_supabase, supabase
import logging
from services.openai_service import evaluate_answer_with_ai
import uuid
from datetime import datetime
import json

interview_bp = Blueprint('interview', __name__)

ALLOWED_CATEGORIES = [
    "frontend",
    "backend",
    "mobile",
    "devops",
    "data_science",
    "general"
]


@interview_bp.route('/interview', methods=['GET', 'POST'])
def interview():
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Chatbot mülakatına erişim denemesi, oturum yok.")
        # Eğer istek AJAX ile geldiyse, JSON formatında hata döndür
        if request.is_json:
            return jsonify({"error": "Oturum bulunamadı."}), 401
        # Normal bir sayfa isteğiyse, giriş sayfasına yönlendir
        return redirect(url_for('auth.login'))
    
    duration_minutes = session.get('selected_duration')

    # Eğer süre seçilmemişse (örn: sayfa yenilendi), kullanıcıyı ayar sayfasına geri yolla.
    if not duration_minutes:
        logging.warning("Mülakat sayfasına 'selected_duration' olmadan erişildi. Yönlendiriliyor.")
        flash("Lütfen mülakat ayarlarını yaparak başlayın.", "error") # Kullanıcıya bilgi ver
        return redirect(url_for('interview.create_interview'))

    try:
        # Süreyi saniyeye çevir
        duration_seconds = int(duration_minutes) * 60
    except (ValueError, TypeError):
        # Eğer session'daki değer bozuksa (olmamalı ama önlem amaçlı) hata ver ve yönlendir.
        logging.error(f"Geçersiz süre değeriyle karşılaşıldı: {duration_minutes}")
        flash("Geçersiz süre ayarı. Lütfen tekrar deneyin.", "error")
        return redirect(url_for('interview.create_interview'))
    

    # ----- POST İSTEĞİ İŞLEME (Kullanıcı mesaj gönderdiğinde) -----
    # Bu blok, AJAX (fetch) ile gelen asenkron mesajları yakalar.
    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"error": "Geçersiz istek formatı, JSON bekleniyor."}), 400

        user_input = request.json.get('user_input')
        if user_input:
            # Sohbet geçmişi zaten mevcut olmalı (GET isteğinde oluşturuldu).
            if 'chat_history' not in session:
                 # Bu durum normalde olmamalı, ama bir güvenlik önlemi olarak eklenebilir.
                 return jsonify({"error": "Sohbet oturumu bulunamadı, lütfen sayfayı yenileyin."}), 400

            session['chat_history'].append({"role": "user", "content": user_input})

            # OpenAI'den cevap al ve session'a ekle
            ai_reply = generate_openai_response(session['chat_history'])
            session['chat_history'].append({"role": "assistant", "content": ai_reply})
            session.modified = True

            # Sadece yapay zekanın cevabını JSON olarak ön yüze (JavaScript'e) döndür.
            return jsonify({'ai_reply': ai_reply})
        else:
            # Boş mesaj gönderilirse hata döndür.
            return jsonify({'ai_reply': "Lütfen bir mesaj girin."})

    # ----- GET İSTEĞİ İŞLEME (Kullanıcı sayfayı ilk açtığında) -----
    # Bu blok, sayfa ilk yüklendiğinde veya yenilendiğinde çalışır.
    
    # Eğer bu mülakat için bir sohbet geçmişi yoksa, yeni bir tane oluştur.
    if 'chat_history' not in session:
        category = session.get('current_interview_category')

        # Eğer session'da bir kategori belirtilmişse, bu bir teknik mülakattır.
        if category and category in ALLOWED_CATEGORIES:
            logging.info(f"Teknik chatbot mülakatı başlatılıyor. Kategori: {category}")
            system_prompt = f"Sen, '{category}' alanında uzmanlaşmış bir teknik mülakatçısın. Görevin, adayın bu alandaki bilgi ve tecrübesini ölçmek için derinlemesine ve zorlayıcı teknik sorular sormaktır. Lütfen profesyonel bir dil kullan ve adayın cevaplarına göre takip soruları sor."
            opening_message = f"Merhaba! '{category}' alanı üzerine yapacağımız teknik mülakat simülasyonuna hoş geldiniz. Hazır olduğunuzda ilk teknik soruyla başlayabiliriz. Hazır mısınız?"
            
            session['chat_history'] = [
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": opening_message}
            ]
        # Eğer kategori belirtilmemişse, bu bir genel yetenek mülakatıdır.
        else:
            logging.info("Genel yetenek chatbot mülakatı başlatılıyor.")
            session['chat_history'] = [
                {"role": "system", "content": "Sen bir iş görüşmesi yapan uzman bir mülakatçı gibisin. Adaya nazikçe ve profesyonelce yaklaş."},
                {"role": "assistant", "content": "Merhaba! Mülakat simülasyonuna hoş geldiniz. Bana biraz kendinizden bahseder misiniz?"}
            ]
        
        # Her yeni mülakat başlangıcında soru ID'sini temizle
        session['current_question_id'] = None 

    # Son olarak, sohbet geçmişini içeren HTML sayfasını render et.
    return render_template('interview.html',
                           chat_history=session.get('chat_history', []),
                           duration=duration_seconds)

@interview_bp.route('/interview/reset')
def reset_interview():
    session.pop('chat_history', None)
    session.pop('current_question_id', None)
    session.pop('current_interview_category', None) # Kategoriyi de temizle
    logging.info("Chatbot mülakat oturumu, soru ID'si ve kategori sıfırlandı.")
    return redirect(url_for('interview.interview'))

@interview_bp.route('/interview/<category>/<int:question_num>')
def interview_question_route(category, question_num):
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Mülakat sorusu sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('auth.login'))
    duration_minutes = session.get('selected_duration')
    if not duration_minutes:
        logging.warning("Mülakat soru sayfasına 'selected_duration' olmadan erişildi. Yönlendiriliyor.")
        flash("Lütfen mülakat ayarlarını yaparak başlayın.", "error")
        return redirect(url_for('interview.create_interview'))
    reset_timer_flag = session.pop('written_test_timer_reset', False)
    try:
        duration_seconds = int(duration_minutes) * 60
    except (ValueError, TypeError):
        logging.error(f"Geçersiz süre değeriyle karşılaşıldı: {duration_minutes}")
        flash("Geçersiz süre ayarı. Lütfen tekrar deneyin.", "error")
        return redirect(url_for('interview.create_interview'))
    if category not in ALLOWED_CATEGORIES:
        logging.error(f"Geçersiz mülakat kategorisi istendi: {category}")
        return render_template('error.html', message="Geçersiz mülakat kategorisi."), 404

    # YENİ: Eğer bu ilk soru ise, yeni bir test oturumu başlat
    if question_num == 1:
        # Yeni, benzersiz bir test oturum kimliği oluştur ve session'a kaydet
        new_interview_id = str(uuid.uuid4())
        session['current_interview_id'] = new_interview_id
        logging.info(f"Yeni test oturumu başlatıldı. ID: {new_interview_id}")
        
        # Artık session'da büyük veri biriktirmeyeceğimiz için bu listeye gerek yok.
        # Yine de eski verilerden kalmış olabilecekleri temizlemek iyi bir pratiktir.
        session.pop('completed_test_questions_data', None)

    try:
        prompt = f"'{category}' alanında bir iş mülakatı için düşündürücü ve teknik bir soru üret. Sadece soruyu ver, ek açıklama veya formatlama yapma."
        ai_question = generate_single_openai_question(prompt)

        if "Üzgünüm" in ai_question or "üretilemiyor" in ai_question:
            logging.error(f"OpenAI soru üretme hatası: {ai_question}")
            return render_template('error.html', message=ai_question)

        new_question_id = save_question_to_supabase(
            category,
            ai_question,
            user_id,
            question_type='chatbot_technical',
        )

        if not new_question_id:
            logging.error("Soru Supabase'e kaydedilemedi veya ID'si alınamadı.")
            return render_template('error.html', message="Soru kaydedilirken bir hata oluştu.")

        logging.info(f"Soru ID {new_question_id}, {question_num}. soru olarak session'a kaydedildi.")
        session['current_test_question_id'] = new_question_id
        session['current_test_question_num'] = question_num
        session['current_test_category'] = category
        session['current_test_question_data'] = {'question': ai_question}
        session['current_test_question_type'] = 'open_ended'
        session.modified = True
        
        return render_template('interview_question.html',
                               question_num=question_num,
                               total_questions=5, # Bu değeri dinamik hale getirebilirsiniz
                               question_text=ai_question,
                               category=category,
                               duration=duration_seconds,
                               reset_timer=reset_timer_flag)
    except Exception as e:
        logging.exception("YZ ile mülakat sorusu üretilemedi veya kaydedilemedi")
        return render_template('error.html', message="Yapay zeka soruyu oluşturamadı veya kaydedemedi.")

@interview_bp.route('/create_interview', methods=['GET', 'POST'])
def create_interview():
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Create Interview sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        mode_choice = request.form.get('mode_choice')
        interview_type = request.form.get('interview_type')
        technical_area = request.form.get('technical_area')
        difficulty = request.form.get('difficulty')
        duration_in_minutes = request.form.get('duration')

        session['selected_interview_type'] = interview_type
        session['selected_mode'] = mode_choice
        session['selected_technical_area'] = technical_area
        session['selected_difficulty'] = difficulty
        session['selected_duration'] = duration_in_minutes


        if not interview_type:
            error_message = "Lütfen bir mülakat türü seçin (Asistan veya Yazılı Mülakat)."
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
                session.pop('chat_history', None)
                return redirect(url_for('interview.interview'))
            elif mode_choice == 'technical':
                session['current_interview_category'] = technical_area
                session.pop('chat_history', None)
                return redirect(url_for('interview.interview'))

        elif interview_type == 'written_test':
            logging.info("Yeni bir yazılı mülakat başlatılıyor. Eski test verileri temizleniyor.")
            session.pop('completed_test_questions_data', None)
            session.pop('current_test_question_data', None)
            session.pop('current_test_question_id', None)
            session.pop('current_test_question_num', None)
            session.pop('current_test_question_type', None)
            session.pop('current_test_category', None)
            session['selected_written_test_types'] = ['open_ended']
            session['total_written_test_questions'] = 5
            session['written_test_timer_reset'] = True

            if mode_choice == 'general':
                session['selected_category_for_test'] = 'general'
                return redirect(url_for('interview.interview_question_route', category='general', question_num=1))
            elif mode_choice == 'technical':
                session['selected_category_for_test'] = technical_area 
                return redirect(url_for('interview.interview_question_route', category=technical_area, question_num=1))

    selected_interview_type = session.get('selected_interview_type', None)
    selected_mode = session.get('selected_mode', None)
    selected_technical_area = session.get('selected_technical_area', None)

    return render_template('create_interview.html',
                           categories=ALLOWED_CATEGORIES,
                           selected_interview_type=selected_interview_type,
                           selected_mode=selected_mode,
                           selected_technical_area=selected_technical_area)

@interview_bp.route('/submit_written_answer', methods=['POST'])
def submit_written_answer():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    # Session'dan sadece o anki soru ve test ile ilgili ID'leri alıyoruz
    question_id = session.get('current_test_question_id')
    category = session.get('current_test_category')
    question_num = session.get('current_test_question_num')
    total_questions = session.get('total_written_test_questions', 5) # toplam soru sayısını senkronize ettim
    
    # YENİ: O anki testin benzersiz ID'sini session'dan alıyoruz
    interview_session_id = session.get('current_interview_id')
    user_answer_input = request.form.get('user_answer')

    if not all([question_id, interview_session_id]):
        logging.error("Cevap gönderilemedi: Soru veya Test Oturum ID'si session'da bulunamadı.")
        return render_template('error.html', message="Cevap gönderilemedi: Oturum bilgisi eksik.")

    # AI puanını ve değerlendirmesini al
    evaluation = evaluate_answer_with_ai(
        session.get('current_test_question_data', {}).get('question'),
        user_answer_input
    )
    score = evaluation.get('score')
    is_correct = evaluation.get('is_correct')
    feedback = evaluation.get('feedback')
    is_correct_numeric = 1.0 if is_correct else 0.0 if is_correct is not None else None

    # Veritabanına kaydetme işlemi (save_answer_to_supabase yerine doğrudan yazıldı)
    response_ok = False
    try:
        # Not: 'question_text' sütununuzun interview_answers tablonuzda olması gerekir.
        supabase.table("interview_answers").insert({
            "question_id": str(question_id),
            "user_id": str(user_id),
            "user_answer": user_answer_input,
            "is_correct": is_correct_numeric,
            "score": score,
            "ai_response": feedback,
            "question_text": session.get('current_test_question_data', {}).get('question'),
            # YENİ: Test kimliğini veritabanına ekliyoruz
            "interview_session_id": interview_session_id 
        }).execute()
        response_ok = True
    except Exception as e:
        logging.error(f"Supabase kaydı başarısız: {e}")
        response_ok = False
    
    # Session'a büyük veri ekleme bloğu TAMAMEN KALDIRILDI.

    if response_ok:
        next_question_num = question_num + 1

        if next_question_num > total_questions:
            logging.info(f"Test tamamlandı. ID: {interview_session_id}. Sonuç sayfasına yönlendiriliyor.")
            # Sonuçlar sayfasına o teste ait ID'yi URL parametresi olarak gönderiyoruz
            return redirect(url_for('interview.test_results', category=category, interview_id=interview_session_id))
        else:
            return redirect(url_for('interview.interview_question_route', category=category, question_num=next_question_num))
    else:
        logging.error(f"Cevap Supabase'e kaydedilemedi. Soru ID: {question_id}")
        return render_template('error.html', message="Cevabınız kaydedilemedi. Lütfen tekrar deneyin.")
    
@interview_bp.route('/test_results')
def test_results():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    category = request.args.get('category')
    # YENİ: Session yerine URL'den gelen test kimliğini alıyoruz
    interview_id = request.args.get('interview_id')

    if not interview_id:
        logging.error("Sonuçlar sayfası 'interview_id' olmadan çağrıldı.")
        return render_template('error.html', message="Sonuçları göstermek için geçerli bir test kimliği gereklidir.")

    # YENİ: Veritabanından o teste ait TÜM cevapları tek bir sorgu ile çekiyoruz
    answers_response = supabase.table("interview_answers") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("interview_session_id", interview_id) \
        .order("answered_at", desc=False) \
        .execute()
    
    answers = answers_response.data if answers_response and hasattr(answers_response, "data") else []

    # Veri işleme mantığı aynı kalıyor
    detailed_answers = []
    correct_answers_count = 0
    for a in answers:
        is_correct = a.get('is_correct')
        if is_correct == 1.0:
            correct_answers_count += 1
        detailed_answers.append({
            'question_text': a.get('question_text', ''),
            'user_response': a.get('user_answer', ''),
            'is_correct': is_correct,
            'feedback': a.get('ai_response', '')
        })

    total_questions_in_test = len(answers)
    incorrect_answers_count = total_questions_in_test - correct_answers_count
    
    # Test bittiği için o teste ait session verilerini temizliyoruz
    session.pop('current_interview_id', None)
    session.pop('current_test_question_id', None)
    session.pop('current_test_question_data', None)
    session.modified = True

    return render_template('test_results.html',
                           username=session.get('user_profile', {}).get('name', 'Kullanıcı'),
                           category=category,
                           total_questions_asked=total_questions_in_test,
                           correct_answers_count=correct_answers_count,
                           incorrect_answers_count=incorrect_answers_count, 
                           score=correct_answers_count * 20,
                           detailed_answers=detailed_answers,
                           is_open_ended_test=True)

# @interview_bp.route('/my_interviews')
# def my_interviews():
#     user_id = session.get('user_id')
#     if not user_id:
#         logging.warning("Geçmiş mülakatlar sayfasına erişim denemesi, oturum yok.")
#         return redirect(url_for('auth.login'))

#     if not supabase:
#         logging.error("Supabase bağlantısı yok, geçmiş mülakatlar gösterilemiyor.")
#         return render_template('error.html', message="Supabase bağlantısı kurulamadı.")

#     try:
#         logging.info(f"Geçmiş mülakatlar için user_id: {user_id}") 

#         questions_response = supabase.table("interview_questions") \
#                                      .select("id, category, question_text, created_at, question_type") \
#                                      .eq("user_id", str(user_id)) \
#                                      .order("created_at", desc=True) \
#                                      .execute()
        
#         questions = questions_response.data
#         logging.info(f"interview_questions tablosundan çekilen soru sayısı: {len(questions) if questions else 0}")

#         mullakatlar_detayli = []
#         if questions:
#             for q in questions:
#                 question_id = q.get('id')
#                 logging.info(f"İşlenen soru ID: {question_id}, Kategori: {q.get('category')}") 
#                 if question_id:
#                     answers_response = supabase.table("interview_answers") \
#                                                .select("id, user_answer, ai_response, selected_option, is_correct, answered_at") \
#                                                .eq("question_id", str(question_id)) \
#                                                .order("answered_at", desc=False) \
#                                                .execute()
                    
#                     answers = answers_response.data if answers_response and answers_response.data else []
#                     logging.info(f"Soru ID {question_id} için çekilen cevap sayısı: {len(answers)}") 
                    
#                     mullakat_detay = q.copy()
#                     mullakat_detay['answers'] = answers
#                     mullakatlar_detayli.append(mullakat_detay)
#                 else:
#                     logging.warning(f"Soru ID'si alınamadı, cevaplar çekilemedi: {q}")
        
#         logging.info(f"Toplam işlenen mülakat detayı: {len(mullakatlar_detayli)}") 
        
#         return render_template('my_interviews.html', mülakatlar=mullakatlar_detayli)

#     except Exception as e:
#         logging.error(f"Supabase'den geçmiş mülakatlar çekilirken hata: {e}", exc_info=True)
#         return render_template('error.html', message="Geçmiş mülakatlar getirilemedi.")

@interview_bp.route('/my_interviews')
def my_interviews():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    # Kullanıcının tüm sorularını çek
    questions_response = supabase.table("interview_questions") \
        .select("id, category, question_text, created_at, question_type") \
        .eq("user_id", str(user_id)) \
        .order("created_at", desc=True) \
        .execute()
    questions = questions_response.data if questions_response and hasattr(questions_response, "data") else []

    # Her soru için cevapları ekle
    interviews = []
    for q in questions:
        answers_response = supabase.table("interview_answers") \
            .select("id, question_id, user_answer, is_correct, ai_evaluation, answered_at") \
            .eq("question_id", str(q["id"])) \
            .eq("user_id", str(user_id)) \
            .order("answered_at", desc=False) \
            .execute()
        answers = answers_response.data if answers_response and hasattr(answers_response, "data") else []
        q["answers"] = answers
        interviews.append(q)

    return render_template('my_interviews.html', interviews=interviews)


# Gerekli importları dosyanızın en üstüne eklediğinizden emin olun
from services.openai_service import evaluate_answer_with_ai

@interview_bp.route('/interview/<question_id>/details')
def interview_details(question_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    try:
        # ... (kodunuzun başındaki SELECT sorguları aynı kalabilir) ...
        # Soru detayını çek
        question_response = supabase.table("interview_questions") \
            .select("id, category, question_text, created_at, question_type") \
            .eq("id", question_id) \
            .single() \
            .execute()
    
        interview = question_response.data if question_response and hasattr(question_response, "data") else None

        if not interview:
            return "Soru bulunamadı.", 404

        # Cevapları çek
        answers_response = supabase.table("interview_answers") \
            .select("id, question_id, user_answer, is_correct, ai_evaluation, answered_at") \
            .eq("question_id", str(question_id)) \
            .eq("user_id", str(user_id)) \
            .order("answered_at", desc=False) \
            .execute()
        answers = answers_response.data if answers_response and hasattr(answers_response, "data") else []

        question_text = interview.get('question_text')
        
        for answer in answers:
            if question_text and not answer.get('ai_evaluation'):
                logging.info(f"Cevap ID {answer['id']} için AI değerlendirmesi başlatılıyor...")
                
                evaluation = evaluate_answer_with_ai(question_text, answer['user_answer'])
                
                # --- ÇÖZÜMÜN OLDUĞU YER BURASI ---
                is_correct_bool = evaluation.get('is_correct')
                
                # Veritabanına göndermeden önce boolean değeri sayıya dönüştür.
                # Eğer is_correct_bool True ise 1, False ise 0, None ise None olur.
                is_correct_numeric = int(is_correct_bool) if is_correct_bool is not None else None
                
                # Değerlendirme sonucunu veritabanına kaydet
                update_data = {
                    "is_correct": is_correct_numeric, # <<< Sayısal değeri gönderiyoruz
                    "ai_evaluation": evaluation.get('feedback')
                }
                supabase.table("interview_answers") \
                    .update(update_data) \
                    .eq("id", answer['id']) \
                    .execute()

                # Şablona göndereceğimiz veriyi boolean olarak tutmaya devam edelim
                # çünkü Jinja şablonumuz `is true` kontrolü yapıyor.
                answer['is_correct'] = is_correct_bool 
                answer['ai_evaluation'] = evaluation.get('feedback')

        interview["answers"] = answers
        return render_template('interview_details.html', interview=interview)

    except Exception as e:
        logging.exception(f"Mülakat detayları getirilirken veya değerlendirilirken KRİTİK HATA:")
        return render_template('error.html', message="Detaylar getirilirken bir hata oluştu.")

# interview_routes.py dosyanızdaki diğer kodlar aynı kalacak.
# Sadece aşağıdaki fonksiyonu bulun ve değiştirin.

@interview_bp.route('/assistant_results')
def assistant_results():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    chat_history = session.get('chat_history', [])
    if len(chat_history) < 3:
        flash("Değerlendirilecek bir sohbet geçmişi bulunamadı.", "error")
        return redirect(url_for('interview.create_interview'))

    # Kategori 'None' ise 'Genel Yetenek' olarak ayarla
    category = session.get('current_interview_category')
    if category is None:
        category = "Genel Yetenek"
    
    username = session.get('user_profile', {}).get('name', 'Kullanıcı')
    ai_feedback = "Değerlendirme oluşturulurken bir hata oluştu." # Varsayılan hata mesajı

    try:
        # ADIM 1: "Geçmiş Mülakatlarım" için ana kaydı oluştur.
        question_text_for_db = f"AI Asistan Mülakatı - {category.replace('_', ' ').title()}"
        
        question_response = supabase.table("interview_questions").insert({
            "user_id": str(user_id),
            "category": category,
            "question_text": question_text_for_db,
            "question_type": "assistant_interview"
        }).execute()

        if not (hasattr(question_response, 'data') and len(question_response.data) > 0):
            raise Exception(f"Supabase 'interview_questions' tablosuna kayıt yapılamadı.")
        
        new_question_id = question_response.data[0]['id']
        logging.info(f"AI mülakatı için ana kayıt oluşturuldu: ID {new_question_id}")

        # --- DÜZELTİLMİŞ PROMPT VE SAĞLAMLAŞTIRILMIŞ İŞLEME ---

        # ADIM 2: OpenAI'den özeti ve puanı al.
        # Prompt'taki sabit "85" değeri kaldırıldı ve talimatlar netleştirildi.
        summary_prompt = [
            {
                "role": "system", 
                "content": "Sen, bir mülakat dökümünü analiz eden uzman bir IK yöneticisisin. Görevin, adayın iletişim becerilerini, cevap kalitesini, güçlü yönlerini ve gelişime açık alanlarını değerlendiren profesyonel bir geri bildirim raporu oluşturmak ve 100 üzerinden genel bir puan vermektir. TÜM ÇIKTIN, BAŞINDA VEYA SONUNDA BAŞKA HİÇBİR METİN OLMADAN SADECE YORUMUN VE PUANININ OLSUN."
            }
        ] + chat_history[1:]
        
        ai_evaluation_raw = generate_openai_response(summary_prompt)
        logging.info(f"OpenAI'den ham değerlendirme alındı: {ai_evaluation_raw}")
        
        ai_score = None # Puan için varsayılan değer
        try:
            # Sadece '{' ile '}' arasındaki kısmı alarak AI'ın eklediği fazlalıkları temizle
            start_index = ai_evaluation_raw.find('{')
            end_index = ai_evaluation_raw.rfind('}') + 1
            if start_index == -1 or end_index == 0:
                raise json.JSONDecodeError("Yanıt içinde JSON nesnesi bulunamadı.", ai_evaluation_raw, 0)
            
            json_part = ai_evaluation_raw[start_index:end_index]
            evaluation_data = json.loads(json_part)
            
            ai_feedback = evaluation_data.get('feedback', "AI'dan geçerli bir geri bildirim metni alınamadı.")
            ai_score = evaluation_data.get('score')

        except (json.JSONDecodeError, TypeError) as e:
            logging.warning(f"AI değerlendirmesi JSON olarak işlenemedi: {e}. Ham metin kullanılıyor.")
            ai_feedback = ai_evaluation_raw # JSON işlenemezse, gelen ham metni geri bildirim olarak kullan

        # --- DÜZELTME BİTTİ ---

        # ADIM 3: Özeti veritabanına kaydet.
        user_responses_text = "\n\n---\n\n".join([msg['content'] for msg in chat_history if msg['role'] == 'user'])
        answer_response = supabase.table("interview_answers").insert({
            "question_id": new_question_id,
            "user_id": str(user_id),
            "user_answer": user_responses_text if user_responses_text else "Kullanıcı cevap vermedi.",
            "ai_response": ai_feedback,
            "score": ai_score
        }).execute()
        
        if not (hasattr(answer_response, 'data') and len(answer_response.data) > 0):
             raise Exception(f"Supabase 'interview_answers' tablosuna kayıt yapılamadı.")

        logging.info(f"AI Asistan mülakat özeti başarıyla kaydedildi.")

    except Exception as e:
        logging.error(f"AI Asistan sonuçları kaydedilirken KRİTİK HATA: {e}", exc_info=True)
        flash("Mülakat sonuçları veritabanına kaydedilirken bir hata oluştu.", "error")
        ai_feedback = "Mülakat özeti oluşturulurken veya kaydedilirken bir hata meydana geldi."

    # ADIM 4: Geçici session verilerini temizle.
    session.pop('chat_history', None)
    session.pop('current_interview_category', None)
    session.pop('selected_duration', None)

    return render_template(
        'assistant_results.html',
        username=username,
        category=category,
        chat_history=chat_history,
        ai_feedback=ai_feedback
    )
# --- SİLME FONKSİYONU ---
@interview_bp.route('/interview/delete/<interview_id>', methods=['POST'])
def delete_interview(interview_id):
    """
    Belirtilen ID'ye sahip mülakatı (soruyu) ve ona bağlı tüm cevapları siler.
    Güvenlik için sadece oturum açmış kullanıcının kendi mülakatını silebilmesini sağlar.
    """
    user_id = session.get('user_id')
    if not user_id:
        # Oturum yoksa yetkisiz hatası döndür
        return jsonify({'status': 'error', 'message': 'Bu işlemi yapmak için giriş yapmalısınız.'}), 401

    logging.info(f"Kullanıcı {user_id}, mülakat {interview_id}'i silme talebinde bulundu.")

    try:
        # 1. Adım: Mülakatın gerçekten bu kullanıcıya ait olup olmadığını kontrol et.
        question_to_delete_response = supabase.table("interview_questions") \
            .select("id") \
            .eq("id", str(interview_id)) \
            .eq("user_id", str(user_id)) \
            .single() \
            .execute()

        if not (question_to_delete_response.data):
            logging.warning(f"Yetkisiz silme denemesi: Kullanıcı {user_id}, mülakat {interview_id}")
            return jsonify({'status': 'error', 'message': 'Mülakat bulunamadı veya silme yetkiniz yok.'}), 404

        # 2. Adım: Mülakata bağlı tüm cevapları sil (Cascading Delete)
        # Bu adım, veritabanında "orphaned" (sahipsiz) kayıt kalmasını engeller.
        supabase.table("interview_answers") \
            .delete() \
            .eq("question_id", str(interview_id)) \
            .execute()
        
        logging.info(f"Mülakat {interview_id} için bağlı cevaplar silindi.")

        # 3. Adım: Ana mülakat kaydını (soruyu) sil
        supabase.table("interview_questions") \
            .delete() \
            .eq("id", str(interview_id)) \
            .execute()
            
        logging.info(f"Mülakat {interview_id} başarıyla silindi.")

        # Başarılı olursa frontend'e onay mesajı gönder
        return jsonify({'status': 'success', 'message': 'Mülakat başarıyla silindi.'}), 200

    except Exception as e:
        logging.error(f"Mülakat silinirken hata oluştu (ID: {interview_id}): {e}", exc_info=True)
        # Hata olursa işlemi geri al (veritabanı transaction yönetimi varsa) ve hata mesajı gönder
        return jsonify({'status': 'error', 'message': f'Sunucu hatası: Mülakat silinemedi. Hata: {str(e)}'}), 500