# sites_data.py - База данных сайтов для веб-браузера RobotOS (GTA Web Style)

HOME_URL = "http://robotos.com"

SITES = {
    # 1. ОФИЦИАЛЬНЫЙ САЙТ СИСТЕМЫ
    "http://robotos.com": {
        "title": "RobotOS Official Portal",
        "content": [
            ("h1", "=== ПОРТАЛ ROBOTOS ==="),
            ("p", "Официальная ОС 2026 года для платформы RP2350 DVI."),
            ("p", "Создатель: Кирилл Дмитриев."),
            ("hr", ""),
            ("link", ">> Новости и обновления системы", "http://robotos.com/news"),
            ("link", ">> Скачать 32 ГБ ОЗУ бесплатно", "http://robotos.com/ram"),
            ("link", ">> Магазин роботов и железа", "http://robotos.com/shop"),
            ("link", ">> База данных Пентагона (Утечки)", "http://pentagon.gov/leaks"),
        ]
    },

    "http://robotos.com/news": {
        "title": "RobotOS Новости",
        "content": [
            ("h1", "НОВОСТИ ТЕХНОЛОГИЙ"),
            ("p", "* Вышел браузер Explorer!"),
            ("p", "* DOOM 3D и Арканоид."),
            ("p", "* Кризис довел людей до 520КБ."),
            ("hr", ""),
            ("link", "<< Вернуться на главную", "http://robotos.com"),
        ]
    },

    # 2. ПОИСКОВИК GOOGLE
    "http://google.com": {
        "title": "Google Поиск",
        "content": [
            ("h1", "G o o g l e"),
            ("p", "Поиск информации в сети:"),
            ("box", "[ Искать в Интернете... ]"),
            ("link", "[ Поиск в Google ]", "http://google.com/results"),
            ("link", "[ Мне повезет! ]", "http://robotos.com/ram"),
            ("hr", ""),
            ("p", "Популярные запросы сегодня:"),
            ("link", "* Как разбогатеть на микропитоне", "http://robotos.com"),
            ("link", "* Исходный код Windows 10", "http://youtube.com"),
            ("link", "* Нейронка на RP Pico2", "http://robotos.com/shop"),
        ]
    },

    "http://google.com/results": {
        "title": "Результаты поиска Google",
        "content": [
            ("h1", "Результаты поиска (0.02 сек):"),
            ("link", "1. RobotOS - Лучшая ОС для микрокомпьютеров", "http://robotos.com"),
            ("p", "  Официальный сайт, новости, игры и приложения."),
            ("link", "2. YouTube - Смешные видео", "http://youtube.com"),
            ("p", "  Миллионы часов контента."),
            ("link", "3. Секретные архивы ЦРУ", "http://pentagon.gov/leaks"),
            ("hr", ""),
            ("link", "<< Назад в Google", "http://google.com"),
        ]
    },

    # 3. ВИДЕОХОСТИНГ YouTube (YOUTUBE)
    "http://youtube.com": {
        "title": "YouTube: Видеохостинг",
        "content": [
            ("h1", "YouTube: Тренды"),
            ("box", "[▶] Обзор RobotOS на мониторе 20 (1.2M просм.)"),
            ("link", "  -> Смотреть видео", "http://youtube.com/watch1"),
            ("box", "[▶] Запуск ComfyUI на Pico2 (850k просм.)"),
            ("link", "  -> Смотреть видео", "http://youtube.com/watch2"),
            ("box", "[▶] 10 часов звука дисковода"),
            ("link", "  -> Смотреть видео", "http://youtube.com/watch1"),
            ("hr", ""),
            ("link", "<< На главную RobotOS", "http://robotos.com"),
        ]
    },

    "http://youtube.com/watch1": {
        "title": "Просмотр видео - YouTube",
        "content": [
            ("box", "[===========================]"),
            ("box", "|   ( o )   ( o )  [60 FPS] |"),
            ("box", "|           ---             |"),
            ("box", "[===========================]"),
            ("h1", "Обзор RobotOS DVI Edition"),
            ("p", "Канал: Кибер-Инженер"),
            ("p", "Лайков: 45 000   Дизлайков: 0"),
            ("p", "Комментарии (1):"),
            ("p", "- Бот: Это лучшая прошивка в мире!"),
            ("hr", ""),
            ("link", "<< Назад в YouTube", "http://youtube.com"),
        ]
    },

    "http://youtube.com/watch2": {
        "title": "Запуск ComfyUI на Pico2",
        "content": [
            ("box", "[======== ВИДЕОПОТОК =======]"),
            ("box", "|    /\\_/\\                  |"),
            ("box", "|   ( o.o )  *шмяк по кнопке*|"),
            ("box", "[===========================]"),
            ("h1", "Запуск ComfyUI на Pico2"),
            ("p", "Просмотров: 850 000"),
            ("p", "Кот не раскаялся в содеянном."),
            ("hr", ""),
            ("link", "<< Назад в YouTube", "http://youtube.com"),
        ]
    },

    # 4. ШУТОЧНЫЙ САЙТ "СКАЧАТЬ ОЗУ"
    "http://robotos.com/ram": {
        "title": "Download RAM Free!",
        "content": [
            ("h1", "АКЦИЯ: Скачайте 32 ГБ ОЗУ!"),
            ("p", "Ваш RP2350 работает медленно?"),
            ("p", "Наш сервис бесплатно увеличит ваш SRAM до 32 ГБ через нано-технологии!"),
            ("link", "[ СКАЧАТЬ 32 ГБ ОЗУ СЕЙЧАС ]", "http://robotos.com/ram_ok"),
            ("hr", ""),
            ("link", "<< На главную", "http://robotos.com"),
        ]
    },

    "http://robotos.com/ram_ok": {
        "title": "ОЗУ успешно установлено!",
        "content": [
            ("h1", "ПОЗДРАВЛЯЕМ!"),
            ("p", "Вы успешно скачали 32 ГБ оперативной памяти прямо в микроконтроллер!"),
            ("p", "Теперь ваш калькулятор мощнее суперкомпьютера NASA."),
            ("link", "[ Скачать видеокарту RTX 4090 Ti ]", "http://google.com"),
            ("hr", ""),
            ("link", "<< На главную", "http://robotos.com"),
        ]
    },

    # 5. УТЕЧКИ ПЕНТАГОНА
    "http://pentagon.gov/leaks": {
        "title": "TOP SECRET ARCHIVE",
        "content": [
            ("h1", "СЕКРЕТНЫЕ АРХИВЫ ЦРУ"),
            ("p", "Внимание! Вы вошли под учетной записью ROOT."),
            ("link", "* Angela_Merkel_nude_photos.zip", "http://robotos.com"),
            ("link", "* Epstein_island_guests2024.pdf", "http://robotos.com"),
            ("link", "* otkuda_na_Belarus_gotovilos_napadeniye.png", "http://robotos.com"),
            ("hr", ""),
            ("link", "[ Срочно стереть логи и выйти ]", "http://google.com"),
        ]
    },

    # 6. МАГАЗИН ЖЕЛЕЗА
    "http://robotos.com/shop": {
        "title": "RobotShop Hardware",
        "content": [
            ("h1", "МАГАЗИН ЖЕЛЕЗА"),
            ("p", "* Плата RP2350-PiZero - 1200 руб."),
            ("p", "* Сервопривод ковша MG996R - 350 руб."),
            ("p", "* Датчик температуры DHT22 - 250 руб."),
            ("p", "* Монитор 20 дюймов - Бесценно"),
            ("hr", ""),
            ("link", "<< На главную", "http://robotos.com"),
        ]
    }
}