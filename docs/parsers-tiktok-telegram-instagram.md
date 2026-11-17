# Парсеры TikTok, Telegram и Instagram (issue #6)

Прототип по задаче [#6](https://github.com/alexanderqwerty/Media-metrics/issues/6):
собрать доступные показатели публикации, сохранить их в объекты Python и
вывести в консоль. Twenty CRM, PostgreSQL и планировщик в этот этап не
входят — формат результата промежуточный (`schema_version: 0.1`), чтобы
позже привести его к единой JSON-схеме проекта.

## Быстрый запуск

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

python main.py \
  'https://www.tiktok.com/@nasa/video/7685144199716408589' \
  'https://t.me/UniversitetMIET/6062' \
  'https://www.instagram.com/reel/DeTUk4sDSp-/'
```

Только JSON:

```bash
python main.py --json-only '<url1>' '<url2>' > metrics.json
```

`--strict` возвращает код `1`, если были ошибки сбора или
неподдерживаемые адреса. Без `--strict` ошибки видны в статусах, но не
ломают общий запуск.

## Что собирается

| Площадка | Просмотры | Лайки | Комментарии | Репосты | Реакции |
|---|---|---|---|---|---|
| TikTok | да (`playCount`) | да (`diggCount`) | да (`commentCount`) | да (`shareCount`) | — |
| Telegram | да (виджет) | — | — | да, если показаны | да (сумма реакций) |
| Instagram | — | да (`og:description`) | да (`og:description`) | — | — |

`None` означает «показатель не получен», а не ноль. Это принципиально:
ТЗ (п. 4.2) запрещает подменять отсутствующие данные нулём или значением
из предыдущего сеанса.

### TikTok

Публичная страница видео содержит JSON в
`<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">`. Нужные поля:

```text
__DEFAULT_SCOPE__ → webapp.video-detail → itemInfo → itemStruct
  stats.playCount      — просмотры
  stats.diggCount      — лайки
  stats.commentCount   — комментарии
  stats.shareCount     — репосты
  stats.collectCount   — сохранения (в meta.saves)
  desc, createTime, author.uniqueId, video.duration, music.title
```

Если вместо данных пришла заглушка/капча, используется публичный oEmbed
(`https://www.tiktok.com/oembed?url=...`). oEmbed не отдаёт счётчики,
поэтому результат получает статус `no_data`; выдумывать числа нельзя.

Ограничения:

* короткие ссылки `vm.tiktok.com/...` нужно предварительно развернуть —
  парсер ожидает полный адрес `/@user/video/<id>`;
* TikTok может ответить `statusCode 10204` («видео не существует») для
  ролика, недоступного в регионе запроса; это трактуется как `no_data`;
* антибот-заглушки возможны при частых запросах.

### Telegram

Публичный embed-виджет поста:

```text
GET https://t.me/<channel>/<post>?embed=1&mode=tme
```

Разбираются:

* `.tgme_widget_message_views` — просмотры (`2.38K`);
* `.tgme_reaction` — реакции, по элементу на эмодзи (сумма и разбивка);
* `.tgme_widget_message_forwards` — пересылки, если виджет их показывает;
* `time[datetime]` — дата публикации;
* `.tgme_widget_message_text` — текст (сохраняется только превью).

Если пост удалён или канал закрыт, виджет содержит `Post not found` —
статус `no_data`. Тексты комментариев не запрашиваются и не сохраняются
(ТЗ, п. 4.7).

### Instagram

Публичная страница поста/Reels без входа отдаёт заглушку. Если запросить
её user-agent'ом бота-превью (`MediaMetricsBot/0.1`), Instagram возвращает
`og:description` вида:

```text
783K likes, 7,947 comments - nasa on October 9, 2026: "POV: you're watching ..."
```

Из него извлекаются лайки, комментарии, автор, дата и подпись.
Просмотры Instagram в публичном описании не отдаёт — `views = null`.
Счётчики могут быть округлены (`783K` → `783000`); точные значения
доступны только через авторизованный API.

Если Instagram вернул страницу входа или описание без счётчиков, сборщик
возвращает `unavailable`, а не нули. Это осознанное ограничение: парсер
не обходит авторизацию и не использует чужие токены.

## Формат результата

```json
[
  {
    "schema_version": "0.1",
    "platform": "telegram",
    "url": "https://t.me/UniversitetMIET/6062",
    "status": "ok",
    "collected_at": "2026-11-17T10:50:46+00:00",
    "publication": {
      "id": "UniversitetMIET/6062",
      "title": "💫 Начинаем новую жизнь с.... со вторника? ...",
      "author": "НИУ МИЭТ",
      "published_at": "2024-11-05T07:19:27+00:00"
    },
    "metrics": {
      "views": 2380,
      "likes": null,
      "comments": null,
      "shares": null,
      "reactions": 67
    },
    "source": "t.me/embed",
    "meta": {
      "channel": "UniversitetMIET",
      "post_id": 6062,
      "reactions_breakdown": [
        {"emoji": "🔥", "count": 36},
        {"emoji": "👍", "count": 13}
      ]
    },
    "warnings": []
  }
]
```

Статусы:

* `ok` — сбор прошёл, хотя бы часть показателей получена;
* `no_data` — публикация найдена, но площадка не отдала показатели;
* `parse_error` — структура страницы изменилась, ответ не разобрался;
* `unavailable` — сеть/HTTP/вход/лимиты; значения не записываются.

## Тесты

```bash
pip install -r requirements-dev.txt
pytest -q
```

Тесты не ходят в сеть: реальные ответы сохранены в `tests/fixtures/`.
Проверяются разбор чисел (`2.38K`, `3,004`), Telegram-виджет, JSON TikTok,
oEmbed-фолбэк, Instagram `og:description`, отсутствие подмены `None` нулём
и повторы HTTP.

## Ограничения прототипа

* Нет Twenty CRM, БД и расписания — по условию issue #6.
* TikTok: короткие ссылки не разворачиваются; возможны региональные
  блокировки и капча.
* Instagram: лайки/комментарии округлены, просмотры недоступны без
  авторизованного API; страница может потребовать вход.
* Telegram: пересылки отображаются не для всех постов; реакции — сумма
  по эмодзи, а не «лайки».
* Формат `schema_version: 0.1` промежуточный; при появлении единой схемы
  меняется только `MetricRecord.to_dict()`.
