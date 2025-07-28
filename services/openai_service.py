import os
import logging
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv

load_dotenv()

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
    

import json

# ... (mevcut importlarınız ve fonksiyonlarınız) ...

def evaluate_answer_with_ai(question, user_answer):
    """
    Bir soruyu ve kullanıcı cevabını alıp, AI ile değerlendirir.
    Değerlendirme sonucunu JSON formatında döndürür.
    """
    try:
        # AI'a rolünü, görevini ve istediğimiz çıktı formatını net bir şekilde anlatıyoruz.
        prompt = f"""
        Sen bir teknik mülakat değerlendirme uzmanısın. Görevin, sana verilen bir soruyu ve bu soruya verilen bir kullanıcı cevabını analiz etmektir.
        Cevabın doğruluğunu, eksikliğini ve kalitesini değerlendir.
        
        Değerlendirme sonucunu SADECE ve SADECE aşağıdaki gibi bir JSON formatında döndür:
        {{
          "is_correct": true veya false,
          "feedback": "Kullanıcının cevabının neden doğru veya yanlış olduğuna dair kısa ve yapıcı bir geri bildirim."
        }}

        Soru: "{question}"
        Kullanıcı Cevabı: "{user_answer}"
        """
        
        # Bu, daha önce kullandığınız OpenAI çağırma fonksiyonu olmalı
        # generate_single_openai_question veya benzeri bir fonksiyon olabilir.
        # Önemli olan, bu prompt'u AI'a göndermektir.
        response_text = generate_single_openai_question(prompt) # Kendi OpenAI çağırma fonksiyonunuzu kullanın
        
        # AI'dan gelen metni JSON olarak ayrıştırmaya çalış
        evaluation_json = json.loads(response_text)
        
        # Beklenen anahtarların olup olmadığını kontrol et
        if 'is_correct' not in evaluation_json or 'feedback' not in evaluation_json:
            # AI beklenen formatta cevap vermezse, varsayılan bir değer döndür
            logging.error(f"AI değerlendirmesi beklenen formatta değil: {response_text}")
            return {"is_correct": None, "feedback": "AI cevabı otomatik olarak değerlendiremedi."}
            
        return evaluation_json

    except json.JSONDecodeError:
        # AI geçerli bir JSON döndürmezse
        logging.error(f"AI geçerli bir JSON döndürmedi: {response_text}")
        return {"is_correct": None, "feedback": "AI değerlendirmesi ayrıştırılamadı."}
    except Exception as e:
        logging.error(f"AI değerlendirmesi sırasında bir hata oluştu: {e}")
        return {"is_correct": None, "feedback": "Değerlendirme sırasında bir hata oluştu."}