import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-change-this")
ABACUS_API_KEY = os.getenv("ABACUS_API_KEY", "")

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/youtube.readonly",
]

CATEGORIES = {
    "Teknoloji": {"icon": "💻", "color": "#3B82F6"},
    "Yapay Zeka": {"icon": "🤖", "color": "#8B5CF6"},
    "Tarih": {"icon": "📜", "color": "#D97706"},
    "Kültür & Sanat": {"icon": "🎨", "color": "#EC4899"},
    "Sağlık": {"icon": "🏥", "color": "#10B981"},
    "Eğitim": {"icon": "📚", "color": "#6366F1"},
    "Eğlence": {"icon": "🎭", "color": "#F59E0B"},
    "Müzik": {"icon": "🎵", "color": "#F43F5E"},
    "Spor": {"icon": "⚽", "color": "#EF4444"},
    "Finans": {"icon": "💰", "color": "#06B6D4"},
    "Yemek": {"icon": "🍽️", "color": "#F97316"},
    "Bilim": {"icon": "🔬", "color": "#14B8A6"},
    "Kişisel Gelişim": {"icon": "🌱", "color": "#84CC16"},
    "Oyun": {"icon": "🎮", "color": "#7C3AED"},
    "Diğer": {"icon": "📌", "color": "#6B7280"},
}