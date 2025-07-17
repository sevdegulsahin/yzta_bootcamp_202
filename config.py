import os

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'varsayilan_cok_gizli_bir_anahtar_degistirmeli')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY') 