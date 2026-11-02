import json
from parsers.rutube import RutubeCollector
from parsers.max import MaxCollector


def main():
    # Тестовые URL
    urls = [
        "https://rutube.ru/video/6790928c5b1d07e50b71df24957c29ad/",
        "https://max.ru/channel/some_post_id"  # Ссылка для примера
    ]

    collectors = {
        "rutube": RutubeCollector(),
        "max": MaxCollector(),
    }

    results = []

    for url in urls:
        if "rutube.ru" in url:
            collector = collectors["rutube"]
        elif "max.ru" in url:
            collector = collectors["max"]
        else:
            print(f"Пропуск: площадка не поддерживается — {url}")
            continue

        try:
            # Сохраняем локально в переменную
            metrics = collector.collect(url)
            # Приводим к словарю для будущего JSON
            results.append(metrics.to_dict())
        except Exception as e:
            print(f"Ошибка при сборе {url}: {e}")

    # Вывод в консоль в едином формате JSON
    print("\n=== РЕЗУЛЬТАТЫ СБОРА ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()