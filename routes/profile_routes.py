from flask import Blueprint, render_template, request, redirect, url_for, session
from services.supabase_service import supabase
import logging
from werkzeug.utils import secure_filename
import os
from flask import current_app
from routes.interview_routes import ALLOWED_CATEGORIES

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile')
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = {
        "name": session.get('user_profile', {}).get('name', 'Kullanıcı'),
        "email": session.get('user_profile', {}).get('email', ''),
        "role": session.get('user_profile', {}).get('role', ''),
        "avatar_url": session.get('user_profile', {}).get('avatar_url', None),
    }

    # Tüm cevapları çek
    answers_response = supabase.table("interview_answers") \
        .select("score, question_id, answered_at, is_correct") \
        .eq("user_id", str(user_id)) \
        .execute()
    answers = answers_response.data if answers_response and hasattr(answers_response, "data") else []

    # Toplam mülakat sayısı (farklı session_id veya farklı interview_id varsa ona göre güncelleyebilirsin)
    total_interviews = len(set([a.get("question_id") for a in answers if a.get("question_id")]))
    user["total_interviews"] = total_interviews

    # Başarı oranı (doğru cevap sayısı / toplam cevap sayısı)
    correct_answers = [a for a in answers if a.get("is_correct") == 1.0]
    success_count = len(correct_answers)
    total_answers = len(answers)
    success_rate = round((success_count / total_answers) * 100, 1) if total_answers else 0
    user["success_rate"] = success_rate

    # Toplam süre (örnek: cevaplar arasındaki süre farkı, ya da answered_at alanı varsa toplayabilirsin)
    # answered_at alanı datetime string ise, süreyi hesapla
    total_seconds = 0
    timestamps = [a.get("answered_at") for a in answers if a.get("answered_at")]
    from datetime import datetime
    if timestamps:
        try:
            times = [datetime.fromisoformat(ts) for ts in timestamps]
            times.sort()
            if len(times) > 1:
                total_seconds = int((times[-1] - times[0]).total_seconds())
        except Exception:
            total_seconds = 0
    user["total_time"] = total_seconds

    # Yetenek analizi (kategori bazlı ortalama puan)
    question_ids = [a["question_id"] for a in answers if a.get("question_id")]
    categories = {}
    if question_ids:
        questions_response = supabase.table("interview_questions") \
            .select("id, category") \
            .in_("id", question_ids) \
            .execute()
        question_map = {q["id"]: q["category"] for q in questions_response.data if "id" in q and "category" in q}
        for a in answers:
            cat = question_map.get(a.get("question_id"))
            score = a.get("score")
            try:
                score_val = float(score)
            except (TypeError, ValueError):
                score_val = None
            if cat and score_val is not None:
                categories.setdefault(cat, []).append(score_val)

    progress_data = []
    for cat in ALLOWED_CATEGORIES:
        scores = categories.get(cat, [])
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        progress_data.append({"item": cat, "value": avg_score})

    user["progress_data"] = progress_data

    return render_template("profile.html", user=user)

@profile_bp.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')  # Tek rol seçimi alınıyor

        avatar_file = request.files.get('avatar')
        avatar_url = None

        if avatar_file and avatar_file.filename != '':
            filename = secure_filename(avatar_file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static/uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            avatar_file.save(file_path)
            avatar_url = url_for('static', filename=f'uploads/{filename}') 


        try:
            update_data = {
                "name": name,
                "role": role,
            }
            if avatar_url:
                update_data["avatar_url"] = avatar_url

            supabase.table("users").update(update_data).eq("auth_id", user_id).execute()

            # Session güncelle
            user_profile = session.get('user_profile', {})
            user_profile.update(update_data)
            session['user_profile'] = user_profile

            return redirect(url_for('profile.profile', username=name))
        except Exception as e:
            logging.error(f"Profil güncellenemedi: {e}", exc_info=True)
            return f"Profil güncellenirken hata oluştu: {str(e)}", 500

    user_profile = session.get('user_profile', {})

    # user_profile içindeki 'role' zaten string olmalı, direkt gönderiyoruz
    return render_template('edit_profile.html', user=user_profile)

