from flask import Blueprint, render_template, request, redirect, url_for, session
from services.openai_service import generate_openai_response, generate_single_openai_question
from services.supabase_service import save_question_to_supabase, save_answer_to_supabase, supabase
import logging

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
        return redirect(url_for('auth.login'))

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
            return redirect(url_for('interview.interview'))

    return render_template('interview.html', chat_history=session.get('chat_history', []))

@interview_bp.route('/interview/reset')
def reset_interview():
    session.pop('chat_history', None)
    session.pop('current_question_id', None)
    logging.info("Chatbot mülakat oturumu ve soru ID'si sıfırlandı.")
    return redirect(url_for('interview.interview'))

@interview_bp.route('/interview/<category>/<int:question_num>')
def interview_question_route(category, question_num):
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Mülakat sorusu sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('auth.login'))

    if category not in ALLOWED_CATEGORIES:
        logging.error(f"Geçersiz mülakat kategorisi istendi: {category}")
        return render_template('error.html', message="Geçersiz mülakat kategorisi."), 404

    try:
        prompt = f"'{category}' alanında bir iş mülakatı için düşündürücü ve teknik bir soru üret. Sadece soruyu ver, ek açıklama veya formatlama yapma."
        ai_question = generate_single_openai_question(prompt)

        if "Üzgünüm" in ai_question or "üretilemiyor" in ai_question:
            logging.error(f"OpenAI soru üretme hatası: {ai_question}")
            return render_template('error.html', message=ai_question)

        new_question_id = save_question_to_supabase(category, ai_question, user_id, question_type='chatbot_technical')

        if not new_question_id:
            logging.error("Soru Supabase'e kaydedilemedi veya ID'si alınamadı.")
            return render_template('error.html', message="Soru kaydedilirken bir hata oluştu.")

        session['current_question_id'] = new_question_id
        logging.info(f"Teknik soru kaydedildi. ID: {new_question_id}. Kullanıcıdan cevap bekleniyor.")

        return render_template('interview_question.html',
                               question_num=question_num,
                               total_questions=5,
                               question_text=ai_question,
                               category=category)
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
                return redirect(url_for('interview.interview'))
            elif mode_choice == 'technical':
                session['current_interview_category'] = technical_area
                session['current_question_id'] = None
                return redirect(url_for('interview.interview_question_route', category=technical_area, question_num=1)) 
        elif interview_type == 'written_test':
            session['selected_written_test_types'] = ['open_ended']
            session['total_written_test_questions'] = 10 

            if mode_choice == 'general':
                session['selected_category_for_test'] = None 
                return redirect(url_for('interview.start_written_test', category=None, question_num=1))
            elif mode_choice == 'technical':
                session['selected_category_for_test'] = technical_area 
                return redirect(url_for('interview.start_written_test', category=technical_area, question_num=1))

    selected_interview_type = session.get('selected_interview_type', None)
    selected_mode = session.get('selected_mode', None)
    selected_technical_area = session.get('selected_technical_area', None)

    return render_template('create_interview.html',
                           categories=ALLOWED_CATEGORIES,
                           selected_interview_type=selected_interview_type,
                           selected_mode=selected_mode,
                           selected_technical_area=selected_technical_area)

@interview_bp.route('/start_written_test', methods=['GET', 'POST'])
def start_written_test():
    user_id = session.get('user_id')
   
    category_from_request = request.args.get('category')
    question_num = int(request.args.get('question_num', 1))

    total_questions_in_session = session.get('total_written_test_questions', 10) 

    if not user_id:
        logging.warning("Yazılı test başlatma denemesi, oturum yok.")
        return redirect(url_for('auth.login'))

    if question_num > total_questions_in_session:
        logging.info(f"Tüm {total_questions_in_session} test soruları tamamlandı. Sonuç sayfasına yönlendiriliyor.")

        current_category_for_result = category_from_request if category_from_request is not None else session.get('selected_category_for_test', 'general')
        return redirect(url_for('interview.test_results', category=current_category_for_result)) 

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

@interview_bp.route('/submit_written_answer', methods=['POST'])
def submit_written_answer():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

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
            'is_correct': ai_evaluation_result
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
            
            return redirect(url_for('interview.test_results', category=category))
        else:
            return redirect(url_for('interview.start_written_test', category=category, question_num=next_question_num))
    else:
        logging.error(f"Cevap Supabase'e kaydedilemedi. Soru ID: {question_id}")
        return render_template('error.html', message="Cevabınız kaydedilemedi. Lütfen tekrar deneyin.")

@interview_bp.route('/test_results')
def test_results():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
  
    category = request.args.get('category') 

    completed_test_questions_data = session.get('completed_test_questions_data', [])

    if not completed_test_questions_data:
        logging.warning("Test sonuçları getirilemedi: Tamamlanan test verileri eksik.")
        session.clear() 
        return redirect(url_for('main.index'))

    detailed_answers = []
    total_questions_in_test = len(completed_test_questions_data)

    for item in completed_test_questions_data:
        user_response_display = item.get('user_answer')
        if user_response_display is None or user_response_display.strip() == "":
            user_response_display = "Cevap verilmedi"

        detailed_answers.append({
            'question_text': item.get('question_text', 'Soru Metni Yok'),
            'user_response': user_response_display,
            'is_correct': item.get('is_correct')
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

@interview_bp.route('/my_interviews')
def my_interviews():
    user_id = session.get('user_id')
    if not user_id:
        logging.warning("Geçmiş mülakatlar sayfasına erişim denemesi, oturum yok.")
        return redirect(url_for('auth.login'))

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