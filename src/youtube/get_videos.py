
import os
import requests

API_KEY = os.getenv("YOUTUBE_API_KEY")
BASE_URL = "https://www.googleapis.com/youtube/v3"

# Плейлист всех загруженных видео канала МИЭТ
UPLOADS_PLAYLIST_ID = "UUheXK8TJadYHM_fOzFM-a7Q"


def get_video_ids():
    """Получаем ID первых 10 видео канала."""

    url = f"{BASE_URL}/playlistItems"

    params = {
        "part": "snippet,contentDetails",
        "playlistId": UPLOADS_PLAYLIST_ID,
        "maxResults": 10,
        "key": API_KEY
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    data = response.json()

    videos = []

    for item in data.get("items", []):
        videos.append({
            "video_id": item["contentDetails"]["videoId"],
            "title": item["snippet"]["title"],
            "published_at": item["contentDetails"].get(
                "videoPublishedAt",
                item["snippet"]["publishedAt"]
            )
        })

    return videos


def get_video_statistics(videos):
    """Получаем статистику видео."""

    video_ids = [video["video_id"] for video in videos]

    url = f"{BASE_URL}/videos"

    params = {
        "part": "snippet,statistics",
        "id": ",".join(video_ids),
        "key": API_KEY
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    data = response.json()

    statistics = []

    for item in data.get("items", []):
        stats = item.get("statistics", {})
        snippet = item["snippet"]

        statistics.append({
            "video_id": item["id"],
            "title": snippet["title"],
            "published_at": snippet["publishedAt"],
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "views": stats.get("viewCount", "Нет данных"),
            "likes": stats.get("likeCount", "Нет данных"),
            "comments": stats.get("commentCount", "Нет данных")
        })

    return statistics


if __name__ == "__main__":

    if not API_KEY:
        print("Ошибка: API-ключ YOUTUBE_API_KEY не найден.")
    else:
        try:
            videos = get_video_ids()

            if not videos:
                print("Видео не найдены.")
            else:
                results = get_video_statistics(videos)

                print("\n========== СТАТИСТИКА YOUTUBE ==========")
                print(f"Получено видео: {len(results)}\n")

                for number, video in enumerate(results, start=1):
                    print(f"========== ВИДЕО №{number} ==========")
                    print("Название:", video["title"])
                    print("ID:", video["video_id"])
                    print("Дата публикации:", video["published_at"])
                    print("Ссылка:", video["url"])
                    print("Просмотры:", video["views"])
                    print("Лайки:", video["likes"])
                    print("Комментарии:", video["comments"])
                    print()

        except requests.exceptions.HTTPError as error:
            print("Ошибка HTTP:", error)
            print(error.response.text)

        except requests.exceptions.RequestException as error:
            print("Ошибка соединения:", error)
