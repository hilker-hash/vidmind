from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.oauth2.credentials


def get_liked_videos(credentials_dict, max_results=200):
    """YouTube beğenilen videoları çeker."""
    creds = google.oauth2.credentials.Credentials(
        token=credentials_dict["token"],
        refresh_token=credentials_dict.get("refresh_token"),
        token_uri=credentials_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=credentials_dict["client_id"],
        client_secret=credentials_dict["client_secret"],
        scopes=credentials_dict.get("scopes", []),
    )

    youtube = build("youtube", "v3", credentials=creds)
    videos = []
    next_page_token = None

    try:
        while len(videos) < max_results:
            request = youtube.videos().list(
                part="snippet,contentDetails",
                myRating="like",
                maxResults=min(50, max_results - len(videos)),
                pageToken=next_page_token,
            )
            response = request.execute()

            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                thumbnails = snippet.get("thumbnails", {})
                thumb = (
                    thumbnails.get("maxres", {}).get("url")
                    or thumbnails.get("high", {}).get("url")
                    or thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("default", {}).get("url")
                    or ""
                )
                videos.append({
                    "id": item["id"],
                    "title": snippet.get("title", "Başlıksız"),
                    "description": snippet.get("description", "")[:500],
                    "thumbnail": thumb,
                    "channel": snippet.get("channelTitle", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "liked_at": snippet.get("publishedAt", ""),
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

    except HttpError as e:
        print(f"YouTube API hatası: {e}")

    return videos


def get_video_transcript(video_id):
    """Video transkriptini almaya çalışır (YouTube API ile doğrudan mümkün değil)."""
    return None
