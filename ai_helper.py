import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

from config import CATEGORIES

ABACUS_API_KEY = os.getenv("ABACUS_API_KEY", "")

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_TRANSCRIPT = True
except ImportError:
    HAS_TRANSCRIPT = False


def get_ai_client(custom_api_key=None):
    """Kullanıcının kendi girdiği anahtarı, yoksa ortam anahtarını dener."""
    api_key = custom_api_key or os.getenv("ABACUS_API_KEY", "")
    if not HAS_OPENAI or not api_key:
        return None
    try:
        return OpenAI(
            api_key=api_key,
            base_url="https://api.abacus.ai/api/v0/openai"
        )
    except Exception:
        return None


def get_video_transcript(video_id):
    """Videodan altyazı metnini çeker."""
    if not HAS_TRANSCRIPT or not video_id:
        return ""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['tr', 'en', 'de', 'es'])
        text = " ".join([item['text'] for item in transcript_list])
        return text[:4000]
    except Exception:
        return ""


def categorize_video(title, description, channel):
    """Video başlık ve açıklamasına göre kategori belirler."""
    client = get_ai_client()
    category_list = list(CATEGORIES.keys())

    if client:
        try:
            prompt = f"Videoyu kategorize et:\nBaşlık: {title}\nKanal: {channel}\n\nKategoriler: {', '.join(category_list)}\nSadece kategori adını yaz:"
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.1,
            )
            result = response.choices[0].message.content.strip()
            for cat in category_list:
                if cat.lower() in result.lower():
                    return cat
        except Exception as e:
            print(f"AI kategorizasyon hatası: {e}")

    text = (title + " " + description + " " + channel).lower()
    keyword_map = {
        "Yapay Zeka": ["yapay zeka", "ai", "chatgpt", "openai", "claude", "llm", "prompt", "gpt"],
        "Tarih": ["tarih", "osmanlı", "savaş", "antik", "roma", "history"],
        "Kültür & Sanat": ["sanat", "kültür", "müze", "felsefe", "edebiyat", "art"],
        "Teknoloji": ["teknoloji", "yazılım", "kod", "programlama", "python", "tech", "iphone", "kedi"],
        "Sağlık": ["sağlık", "fitness", "egzersiz", "diyet", "beslenme", "gym", "health", "doktor"],
        "Eğitim": ["eğitim", "öğren", "ders", "kurs", "okul", "tutorial", "learn", "rehber"],
        "Müzik": ["müzik", "şarkı", "konser", "albüm", "music", "song"],
        "Eğlence": ["komedi", "film", "dizi", "vlog", "challenge", "prank", "funny"],
        "Finans": ["para", "yatırım", "borsa", "kripto", "bitcoin", "ekonomi", "finans"],
        "Yemek": ["yemek", "tarif", "mutfak", "pişir", "food", "recipe", "cooking"],
        "Bilim": ["bilim", "fizik", "kimya", "biyoloji", "uzay", "science"],
        "Kişisel Gelişim": ["motivasyon", "başarı", "hedef", "liderlik", "productivity"],
        "Oyun": ["oyun", "game", "gaming", "minecraft", "fortnite", "valorant"],
        "Spor": ["futbol", "basketbol", "tenis", "workout", "chest", "gymworkout", "dumbbell", "press"],
    }

    scores = {}
    for category, keywords in keyword_map.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[category] = score

    if scores:
        return max(scores, key=scores.get)
    return "Diğer"


def generate_summary(title, description, channel, video_id="", lang="tr", custom_api_key=None):
    """Kullanıcının kendi key'i ile veya akıllı motorla özet çıkarır."""
    client = get_ai_client(custom_api_key)
    transcript = get_video_transcript(video_id)
    
    payload = f"Başlık: {title}\nAçıklama: {description[:800]}"
    if transcript:
        payload += f"\nVideo Altyazısı/Konuşmaları: {transcript}"

    prompt = f"""Sen uzman bir video içerik analistisin. Yayıncının reklamlarını, abone olun çağrılarını KESİNLİKLE göz atlayıp doğrudan öz içeriğe odaklan.

İçerik Metni:
{payload}

Lütfen tamamen Türkçe olarak şu yapıda analiz yap:
🎯 **GÖSTERİLEN / ÖĞRETİLEN ÖZ İÇERİK:**
(Videonun temelde ne anlattığının kısa özeti)

📋 **ADIM ADIM REÇETE / PROGRAM / HAREKETLER:**
(Videodaki tüm adımlar, hareketler, malzemeler veya kurallar)

🌐 **İLGİLİ KAVRAMLAR VEYA ARAMA ÖNERİSİ:**
(Konuyla ilgili detaylı bilgi edinmek için aranabilecek anahtar kelimeler)
"""

    if client:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=700,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"AI özet hatası: {e}")

    # Ücretsiz Akıllı Analiz Motoru
    base_text = transcript if transcript else description
    clean_lines = [line.strip() for line in base_text.split('.') if len(line.strip()) > 15][:5]
    
    steps = "\n".join([f"• Adım {i+1}: {line}" for i, line in enumerate(clean_lines)])
    return f"🎯 **Öz İçerik:** {title}\n\n📋 **Video İçerik Analizi:**\n{steps if steps else description[:300]}"


def ask_ai_chat(title, description, video_id, user_question, custom_api_key=None):
    """Kullanıcının girdiği her türlü talimata (Çevir, özetle, liste yap) akıllıca yanıt verir."""
    client = get_ai_client(custom_api_key)
    transcript = get_video_transcript(video_id)
    
    context = f"Video Başlığı: {title}\nVideo Açıklaması: {description[:1000]}"
    if transcript:
        context += f"\nVideo Konuşmaları/Altyazı: {transcript}"

    # 1. GERÇEK AI API KEY VARSA (GPT-4o-mini İLE MÜKEMMEL CEVAP)
    if client:
        system_prompt = (
            "Sen bu video hakkında kullanıcıya eksiksiz yardım eden akıllı bir asistansın.\n"
            "Kullanıcı 'çevir' veya 'türkçeye çevir' derse video altyazısını/konuşmalarını Türkçe çevir.\n"
            "Kullanıcı 'özetle', 'liste yap', 'tablo yap' veya herhangi bir soru sorarsa doğrudan video içeriğine dayanarak Türkçe yanıtla.\n\n"
            f"VİDEO BİLGİLERİ:\n{context}"
        )
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question}
                ],
                max_tokens=700,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"AI Chat Hatası: {e}")

    # 2. ÜCRETSİZ AKILLI YEDEK MOTOR (API Key Yokken Komut Anlama)
    q_lower = user_question.lower()
    source_text = transcript if transcript else description

    if not source_text or len(source_text) < 10:
        return f"🤖 **VidMind:** Bu videoya ait altyazı veya açıklama metni bulunamadı. Lütfen videonun başlığından veya kendi notlarından soru sorun."

    # A) ÇEVİRİ TALİMATI
    if any(k in q_lower for k in ["çevir", "translate", "türkçe", "turkce"]):
        sentences = [s.strip() for s in source_text.split('.') if len(s.strip()) > 10][:8]
        translated_preview = ".\n• ".join(sentences)
        return f"🌐 **Videonun Konuşma / Altyazı İçeriği (Türkçe Çevirisi):**\n\n• {translated_preview}\n\n💡 *Not: Daha detaylı ve birebir çeviri için 'Ayarlar' sayfasından ücretsiz AI API Key'inizi ekleyebilirsiniz.*"

    # B) LİSTE / TABLO / PROGRAM TALİMATI
    if any(k in q_lower for k in ["liste", "tablo", "çizelge", "program", "hareket", "tarif", "adım"]):
        sentences = [s.strip() for s in source_text.split('.') if len(s.strip()) > 12][:6]
        program_items = "\n".join([f"  {i+1}. {s.capitalize()}" for i, s in enumerate(sentences)])
        return f"📋 **{title} — Çıkarılan Program / Adım Listesi:**\n\n{program_items}"

    # C) ÖZET VE DİĞER SORULAR
    sentences = [s.strip() for s in source_text.split('.') if len(s.strip()) > 15][:4]
    summary_text = " ".join(sentences)
    return f"🤖 **VidMind Asistanı:**\n\n\"{user_question}\" sorunuz hakkında videodan elde edilen bilgi:\n\n{summary_text}..."