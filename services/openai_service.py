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