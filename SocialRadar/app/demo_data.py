"""Prepared test posts for POST /api/demo/seed.

These are NOT real posts from Bluesky or Threads. They are invented for
demonstration, stored with source="demo", and their links point to
example.com on purpose.
"""

DEMO_POSTS: list[dict] = [
    {
        "platform": "bluesky",
        "external_id": "demo-bsky-01",
        "author": "demo_anna",
        "text": "Всем привет! Мне НУЖЕН САЙТ для небольшого цветочного магазина. Кто может помочь?",
        "url": "https://example.com/demo/bluesky/01",
    },
    {
        "platform": "bluesky",
        "external_id": "demo-bsky-02",
        "author": "demo_mark",
        "text": "Looking for a website developer to rebuild our restaurant booking page. Paid project.",
        "url": "https://example.com/demo/bluesky/02",
    },
    {
        "platform": "bluesky",
        "external_id": "demo-bsky-03",
        "author": "demo_timur",
        "text": "Ищу разработчика на стажировку, бесплатно, зато опыт в стартапе.",
        "url": "https://example.com/demo/bluesky/03",
    },
    {
        "platform": "bluesky",
        "external_id": "demo-bsky-04",
        "author": "demo_julia",
        "text": "Finally finished reading Dune. What should I read next?",
        "url": "https://example.com/demo/bluesky/04",
    },
    {
        "platform": "bluesky",
        "external_id": "demo-bsky-05",
        "author": "demo_dana",
        "text": "Ищу Python разработчика для бота, который принимает заказы. Бюджет обсуждаем.",
        "url": "https://example.com/demo/bluesky/05",
    },
    {
        "platform": "threads",
        "external_id": "demo-threads-01",
        "author": "demo_aigerim",
        "text": "Кто может сделать интернет-магазин для одежды? Нужен сайт до конца месяца.",
        "url": "https://example.com/demo/threads/01",
    },
    {
        "platform": "threads",
        "external_id": "demo-threads-02",
        "author": "demo_oliver",
        "text": "Our studio needs a new portfolio. Any website developer available in December?",
        "url": "https://example.com/demo/threads/02",
    },
    {
        "platform": "threads",
        "external_id": "demo-threads-03",
        "author": "demo_serik",
        "text": "Нужен сайт, но бесплатно. Могу заплатить отзывом :)",
        "url": "https://example.com/demo/threads/03",
    },
    {
        "platform": "threads",
        "external_id": "demo-threads-04",
        "author": "demo_maria",
        "text": "Погода в Алматы сегодня отличная, идём в горы.",
        "url": "https://example.com/demo/threads/04",
    },
    {
        "platform": "threads",
        "external_id": "demo-threads-05",
        "author": "demo_ivan",
        "text": "Срочно ищу разработчика: нужно доделать лендинг для курса по дизайну.",
        "url": "https://example.com/demo/threads/05",
    },
]
