import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

supabase: Client | None = None
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    logging.error("HATA: Supabase URL veya Anon Key ortam değişkenleri ayarlanmamış.")
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logging.info("Supabase bağlantısı kuruldu.")
    except Exception as e:
        logging.error(f"Supabase bağlantısı kurulamadı: {e}")

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