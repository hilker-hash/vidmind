os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
import os
import json
import secrets
from flask import (Flask, render_template, redirect, url_for,
                   session, request, jsonify, flash)
from google_auth_oauthlib.flow import Flow
import google.oauth2.credentials
from googleapiclient.discovery import build

import database as db
from youtube_api import get_liked_videos
from ai_helper import categorize_video, generate_summary, ask_ai_chat
from config import (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
                    GOOGLE_SCOPES, CATEGORIES)

# Geliştirme ortamı için HTTP uyarısını devre dışı bırak
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
# Sabit ve güvenli oturum anahtarı
app.secret_key = "youtube-analiz-sabit-gizli-anahtar-12345"

# Veritabanını başlat
db.init_db()

# Google OAuth akış ayarları
CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:5000/callback"],
    }
}


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def get_lang():
    return session.get("lang", "tr")


# ──────────────────────────────────────────────
# ANA SAYFA
# ──────────────────────────────────────────────
@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ──────────────────────────────────────────────
# GİRİŞ / ÇIKIŞ
# ──────────────────────────────────────────────
@app.route("/login")
def login():
    return render_template("login.html", lang=get_lang())


@app.route("/google-login")
def google_login():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=GOOGLE_SCOPES,
        redirect_uri="http://localhost:5000/callback"
    )
    
    verifier = flow.code_verifier or secrets.token_urlsafe(64)
    session["code_verifier"] = verifier
    flow.code_verifier = verifier

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    session["oauth_state"] = state
    return redirect(auth_url)


@app.route('/callback')
def callback():
    if request.headers.get('X-Forwarded-Proto') == 'https':
        request.environ['wsgi.url_scheme'] = 'https'
        
    state = session.get('state')
    if not state or state != request.args.get('state'):
        session.pop('state', None)

    flow = get_google_oauth_flow()
    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:
        flash(f"Giriş hatası: {e}", "danger")
        return redirect(url_for('login'))

    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

    user_info = get_user_info(credentials)
    session['user'] = user_info
    init_db()

    flash("Başarıyla giriş yapıldı!", "success")
    return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f"Giriş hatası: {str(e)}", "error")
        return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/set-lang/<lang>")
def set_lang(lang):
    if lang in ("tr", "en"):
        session["lang"] = lang
    return redirect(request.referrer or url_for("dashboard"))


# ──────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    user = session["user"]
    category = request.args.get("category", "Tümü")
    search = request.args.get("search", "")

    videos = db.get_videos(user["email"], category if category != "Tümü" else None, search or None)
    stats = db.get_category_stats(user["email"])
    total = db.count_videos(user["email"])

    return render_template(
        "dashboard.html",
        user=user,
        videos=videos,
        stats=stats,
        categories=CATEGORIES,
        selected_category=category,
        search=search,
        total=total,
        lang=get_lang(),
    )


@app.route("/fetch-videos")
@login_required
def fetch_videos():
    """YouTube'dan beğenilen videoları çekip kategorize eder ve otomatik AI analizi üretir."""
    user = session["user"]
    credentials_dict = session.get("credentials")

    if not credentials_dict:
        flash("Oturum süresi dolmuş. Lütfen tekrar giriş yapın.", "error")
        return redirect(url_for("login"))

    try:
        videos = get_liked_videos(credentials_dict, max_results=50)
        user_key = db.get_user_api_key(user["email"])

        for v in videos:
            v["category"] = categorize_video(v["title"], v["description"], v["channel"])
            v["summary"] = generate_summary(
                v["title"], 
                v["description"], 
                v["channel"], 
                video_id=v["id"], 
                lang=get_lang(),
                custom_api_key=user_key
            )

        db.save_videos(user["email"], videos)

        conn = db.get_db()
        c = conn.cursor()
        for v in videos:
            c.execute(
                "UPDATE videos SET category = ?, summary = ? WHERE id = ? AND user_email = ?",
                (v["category"], v["summary"], v["id"], user["email"])
            )
        conn.commit()
        conn.close()

        flash(f"{len(videos)} video başarıyla yüklendi, kategorize edildi ve AI analizi hazırlandı! ✅", "success")
    except Exception as e:
        flash(f"Hata oluştu: {str(e)}", "error")

    return redirect(url_for("dashboard"))


# ──────────────────────────────────────────────
# VİDEO DETAY & AI SOHBET
# ──────────────────────────────────────────────
@app.route("/video/<video_id>")
@login_required
def video_detail(video_id):
    user = session["user"]
    video = db.get_video(video_id, user["email"])

    if not video:
        flash("Video bulunamadı.", "error")
        return redirect(url_for("dashboard"))

    notes = []
    conn = db.get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM notes WHERE user_email = ? AND video_id = ? ORDER BY created_at DESC",
              (user["email"], video_id))
    notes = [dict(r) for r in c.fetchall()]
    conn.close()

    return render_template(
        "video_detail.html",
        user=user,
        video=video,
        notes=notes,
        categories=CATEGORIES,
        lang=get_lang(),
    )


@app.route("/video/<video_id>/summarize", methods=["POST"])
@login_required
def summarize_video(video_id):
    user = session["user"]
    video = db.get_video(video_id, user["email"])

    if not video:
        return jsonify({"error": "Video bulunamadı"}), 404

    user_key = db.get_user_api_key(user["email"])
    summary = generate_summary(
        video["title"], 
        video["description"], 
        video["channel"], 
        video_id=video_id, 
        lang=get_lang(),
        custom_api_key=user_key
    )
    db.update_video_summary(video_id, user["email"], summary)

    return jsonify({"summary": summary})


@app.route("/video/<video_id>/chat", methods=["POST"])
@login_required
def chat_with_video(video_id):
    """Kullanıcının kendi API key'i varsa onu kullanır, yoksa genel motor çalışır."""
    user = session["user"]
    video = db.get_video(video_id, user["email"])

    if not video:
        return jsonify({"error": "Video bulunamadı"}), 404

    data = request.get_json() or {}
    user_question = data.get("question", "").strip()

    if not user_question:
        return jsonify({"error": "Soru boş olamaz"}), 400

    user_key = db.get_user_api_key(user["email"])
    answer = ask_ai_chat(video["title"], video["description"], video_id, user_question, custom_api_key=user_key)

    return jsonify({"answer": answer})


@app.route("/video/<video_id>/category", methods=["POST"])
@login_required
def change_category(video_id):
    user = session["user"]
    new_category = request.form.get("category")
    if new_category in CATEGORIES:
        db.update_video_category(video_id, user["email"], new_category)
        flash("Kategori güncellendi ✅", "success")
    return redirect(url_for("video_detail", video_id=video_id))


# ──────────────────────────────────────────────
# NOTLAR & AYARLAR
# ──────────────────────────────────────────────
@app.route("/notes")
@login_required
def notes():
    user = session["user"]
    all_notes = db.get_notes(user["email"])
    return render_template("notes.html", user=user, notes=all_notes, lang=get_lang())


@app.route("/notes/add", methods=["POST"])
@login_required
def add_note():
    user = session["user"]
    content = request.form.get("content", "").strip()
    video_id = request.form.get("video_id", "")
    video_title = request.form.get("video_title", "")

    if content:
        db.save_note(user["email"], content, video_id or None, video_title or None)
        flash("Not kaydedildi ✅", "success")
    else:
        flash("Not boş olamaz.", "error")

    if video_id:
        return redirect(url_for("video_detail", video_id=video_id))
    return redirect(url_for("notes"))


@app.route("/notes/delete/<int:note_id>", methods=["POST"])
@login_required
def delete_note(note_id):
    user = session["user"]
    db.delete_note(note_id, user["email"])
    flash("Not silindi.", "info")
    return redirect(request.referrer or url_for("notes"))


@app.route("/notes/edit/<int:note_id>", methods=["POST"])
@login_required
def edit_note(note_id):
    user = session["user"]
    content = request.form.get("content", "").strip()
    if content:
        db.update_note(note_id, user["email"], content)
        flash("Not güncellendi ✅", "success")
    return redirect(url_for("notes"))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Kullanıcının kendi API key'ini kaydedebileceği alan."""
    user = session["user"]
    if request.method == "POST":
        custom_key = request.form.get("api_key", "").strip()
        db.save_user_api_key(user["email"], custom_key)
        flash("API Anahtarınız başarıyla kaydedildi! ✅", "success")
        return redirect(url_for("settings"))

    current_key = db.get_user_api_key(user["email"])
    return render_template("settings.html", user=user, current_key=current_key, lang=get_lang())


# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 VidMind Akıllı Video Analiz Uygulaması Başlatılıyor...")
    print("📌 Tarayıcıdan açın: http://localhost:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
