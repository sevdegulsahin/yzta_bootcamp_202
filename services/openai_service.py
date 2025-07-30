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
    Soruyu ve kullanıcı cevabını alıp, AI ile 0-100 arası bir puan döndürür.
    """
    try:
        prompt = f"""
        Sen bir kıdemli teknik mülakat değerlendirme uzmanısın. Sana bir teknik soru ve bu soruya verilen bir aday cevabı verilecek.
        Cevabı değerlendirirken yalnızca teknik doğruluk, ifade kalitesi, konuya uygunluk, derinlik ve profesyonellik açısından objektif bir puan ver.

        Aşağıdaki puanlama sistemini kesin şekilde uygula:

        0: Cevap saçma, alakasız, rastgele karakter dizisi, anlam içermeyen kelimeler, konu dışı cümleler, boş ifadeler veya otomatik üretilmiş gibi (örnek: “asdasd”, “evet”, “hayır”, “bilmiyorum”, “çok güzel soru”, vs.). Bu tür cevaplar her durumda 0 puan alır.

        1–20: Cevap teknik olarak yetersiz, çok eksik veya hatalı. Bazı anahtar kelimeler geçse de anlamlı veya doğru bir açıklama yapılmamış.

        21–40: Temel kavramlara değinilmiş ama bilgi eksik, yüzeysel ya da kısmen yanlış.

        41–60: Doğru bilgiler var ama sınırlı derinlikte. Açıklama orta seviyede.

        61–80: Teknik olarak doğru, iyi açıklanmış, ancak ufak eksikler olabilir.

        81–100: Eksiksiz, detaylı, teknik olarak hatasız, iyi yapılandırılmış ve profesyonel cevap.

        Lütfen sadece bu puanlama sistemine göre tek bir TAM SAYI döndür.
        Hiçbir açıklama, gerekçe, yorum ya da fazladan metin yazma.

        Soru: "{question}"
        Kullanıcı Cevabı: "{user_answer}"
        """

        response_text = generate_single_openai_question(prompt)
        # Gelen cevabı float'a çevir
        score = None
        try:
            score = float(response_text.strip())
        except Exception:
            logging.error(f"AI puan cevabı sayı formatında değil: {response_text}")
            score = None

        # is_correct ve feedback üretmek için ek mantık ekle
        is_correct = None
        if score is not None:
            is_correct = score >= 60  # Örneğin 60 ve üzeri doğru kabul edilsin

        feedback = f"Cevabınız {score} puan aldı." if score is not None else "Değerlendirme yapılamadı."

        return {
            "score": score,
            "is_correct": is_correct,
            "feedback": feedback
        }

    except Exception as e:
        logging.error(f"AI puanlama sırasında hata: {e}")
        return None
