import logging
import os
from get_videos import get_video_ids, get_video_statistics

# Настройка логирования (п. 4.2 и раздел 5 ТЗ)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    logging.info("Запуск модуля сбора данных YouTube...")

    if not os.getenv("YOUTUBE_API_KEY"):
        logging.error("Переменная окружения YOUTUBE_API_KEY не установлена!")
        return

    try:
        videos = get_video_ids()
        if not videos:
            logging.warning("Список видео пуст.")
            return

        stats = get_video_statistics(videos)
        logging.info(f"Успешно собраны метрики для {len(stats)} видео.")

        print("\n" + "=" * 50)
        for i, video in enumerate(stats, start=1):
            print(f"Видео #{i}: {video['title']}")
            print(f"  Просмотры:   {video['views']}")
            print(f"  Лайки:       {video['likes']}")
            print(f"  Комментарии: {video['comments']}")
            print("-" * 50)

    except Exception as e:
        logging.error(f"Критическая ошибка при выполнении модуля: {e}")

if __name__ == "__main__":
    main()