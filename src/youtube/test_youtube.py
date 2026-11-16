
import os
import requests
from pprint import pprint

API_KEY = os.getenv("YOUTUBE_API_KEY")

BASE_URL = "https://www.googleapis.com/youtube/v3"


def get_channel():

    url = f"{BASE_URL}/channels"

    params = {
        "part": "snippet,statistics,contentDetails",
        "forHandle": "@MIETuniversity",
        "key": API_KEY
    }

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("items"):
        print("Канал не найден")
        return None

    channel = data["items"][0]

    result = {
        "channel_id": channel["id"],
        "title": channel["snippet"]["title"],
        "subscribers": channel["statistics"].get(
            "subscriberCount"
        ),
        "total_views": channel["statistics"].get(
            "viewCount"
        ),
        "video_count": channel["statistics"].get(
            "videoCount"
        ),
        "uploads_playlist": channel["contentDetails"]
            ["relatedPlaylists"]["uploads"]
    }

    return result


if __name__ == "__main__":

    if not API_KEY:
        print("Ошибка: API-ключ не найден")
    else:
        try:
            channel = get_channel()

            print("\n===== ИНФОРМАЦИЯ О КАНАЛЕ =====")
            pprint(channel)

        except requests.exceptions.HTTPError as error:
            print("Ошибка HTTP:", error)
            print(error.response.text)

        except requests.exceptions.RequestException as error:
            print("Ошибка соединения:", error)
