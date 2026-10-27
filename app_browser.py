# app_browser.py - Веб-браузер Internet Explorer для RobotOS (DVI 320x240)
# GTA-Style Fake Web, закладки, адресная строка, интерактивные гиперссылки
import time
import math
import struct
import gc
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar
import sites_data

W, H = 320, 240
TB_H = 22
WIN_H = H - TB_H  # 218px

# Палитра классического Internet Explorer
C_HEADER     = rgb(28, 32, 44)       # Тёмно-графитовая шапка окна
C_TOOLBAR    = rgb(40, 46, 60)       # Панель инструментов
C_ADDRESS_BG = rgb(16, 20, 28)       # Поле адреса
C_PAGE_BG    = rgb(14, 16, 24)       # Фон веб-страницы
C_BORDER     = rgb(55, 65, 85)       # Рамки
C_IE_BLUE    = rgb(0, 160, 255)      # Фирменный синий Explorer
C_LINK       = rgb(0, 220, 255)      # Цвет ссылок
C_LINK_HOV   = rgb(255, 220, 0)      # Цвет выбранной ссылки (жёлтый)
C_WHITE      = 0xFFFF
C_GRAY       = rgb(150, 160, 175)
C_DARK_GRAY  = rgb(100, 110, 130)

QUICK_BOOKMARKS = [
    ("RobotOS",  "http://robotos.com"),
    ("Google",   "http://google.com"),
    ("YouTube", "http://youtube.com"),
    ("Архивы",   "http://pentagon.gov/leaks"),
]

class BrowserApp:
    def __init__(self, tft, audio, inputs, config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False, "hour": 20, "minute": 45}

        # История переходов
        self.cur_url = sites_data.HOME_URL
        self.history = [self.cur_url]
        self.hist_idx = 0

        # Ссылки на текущей странице
        self.links = []     # [(y_pos, text, target_url)]
        self.link_sel = 0

        self.scroll_y = 0
        self.loading = False

    def click_sound(self, freq=1400, ms=8):
        """Классический щелчок перехода по ссылке Internet Explorer"""
        if self.cfg.get("mute") or self.cfg.get("vol_ui", 30) == 0:
            return
        rate = 22050
        samples = max(2, int(rate / freq))
        cycle = bytearray(samples * 2)
        amp = int(800 * (self.cfg.get("vol_ui", 30) / 100))
        for i in range(samples):
            v = int(amp * math.sin(2 * math.pi * i / samples))
            struct.pack_into("<h", cycle, i * 2, v)
        for _ in range(int((ms / 1000) * freq)):
            self.audio.write(cycle)

    def navigate_to(self, url):
        """Переход по новому адресу с имитацией загрузки"""
        self.click_sound(1600, 10)
        self.cur_url = url
        self.history = self.history[:self.hist_idx + 1]
        self.history.append(url)
        self.hist_idx = len(self.history) - 1
        self.link_sel = 0
        self.scroll_y = 0

        # Эффект быстрой загрузки
        self.loading = True
        self.draw_browser()
        time.sleep_ms(150)
        self.loading = False
        self.draw_browser()

    def go_back(self):
        if self.hist_idx > 0:
            self.click_sound(1200, 10)
            self.hist_idx -= 1
            self.cur_url = self.history[self.hist_idx]
            self.link_sel = 0
            self.scroll_y = 0

    def go_forward(self):
        if self.hist_idx < len(self.history) - 1:
            self.click_sound(1200, 10)
            self.hist_idx += 1
            self.cur_url = self.history[self.hist_idx]
            self.link_sel = 0
            self.scroll_y = 0

    def draw_browser(self):
        t = self.tft

        page = sites_data.SITES.get(self.cur_url, None)
        page_title = page["title"] if page else "404 Not Found"

        # 1. Шапка окна (Y = 0..19)
        t.fill_rect(0, 0, W, 20, C_HEADER)
        t.line(0, 19, W, 19, C_BORDER)
        draw_text(t, f"IE - {page_title[:26]}", 8, 6, C_WHITE)
        t.text("Esc", 294, 6, C_WHITE)

        # 2. Панель управления и адресная строка (Y = 20..42)
        t.fill_rect(0, 20, W, 24, C_TOOLBAR)
        t.line(0, 43, W, 43, C_BORDER)

        # Кнопки < >
        can_back = self.hist_idx > 0
        can_fwd = self.hist_idx < len(self.history) - 1
        t.fill_rect(6, 23, 14, 16, C_ADDRESS_BG)
        t.rect(6, 23, 14, 16, C_BORDER)
        draw_text(t, "<", 10, 27, C_WHITE if can_back else C_DARK_GRAY)

        t.fill_rect(24, 23, 14, 16, C_ADDRESS_BG)
        t.rect(24, 23, 14, 16, C_BORDER)
        draw_text(t, ">", 28, 27, C_WHITE if can_fwd else C_DARK_GRAY)

        # Поле адреса
        t.fill_rect(44, 23, 230, 16, C_ADDRESS_BG)
        t.rect(44, 23, 230, 16, C_BORDER)
        disp_url = self.cur_url if len(self.cur_url) <= 26 else self.cur_url[:24] + ".."
        draw_text(t, disp_url, 48, 27, rgb(200, 225, 255))

        # Вращающийся индикатор загрузки
        if self.loading:
            t.fill_rect(280, 23, 16, 16, C_IE_BLUE)
            draw_text(t, "*", 285, 27, C_WHITE)
        else:
            t.fill_rect(280, 23, 16, 16, rgb(30, 36, 48))
            t.rect(280, 23, 16, 16, C_BORDER)
            draw_text(t, "e", 285, 27, C_IE_BLUE)

        # 3. Панель быстрых закладок (Y = 44..59)
        t.fill_rect(0, 44, W, 16, rgb(20, 24, 34))
        t.line(0, 59, W, 59, C_BORDER)
        bx = 8
        for b_name, b_url in QUICK_BOOKMARKS:
            is_cur = (self.cur_url == b_url)
            draw_text(t, f"[{b_name}]", bx, 48, C_IE_BLUE if is_cur else C_GRAY)
            bx += len(b_name) * 8 + 22

        # 4. Область веб-страницы (Y = 60..203)
        t.fill_rect(0, 60, W, 144, C_PAGE_BG)

        self.links = []

        if not page:
            # Страница 404
            draw_text(t, "ОШИБКА 404: СТРАНИЦА НЕ НАЙДЕНА", 20, 80, rgb(255, 75, 75))
            draw_text(t, "Проверьте сетевой кабель или", 20, 105, C_WHITE)
            draw_text(t, "позвоните провайдеру RobotNet.", 20, 120, C_WHITE)
            self.links.append((150, ">> Вернуться на главную", sites_data.HOME_URL))
            draw_text(t, ">> Вернуться на главную", 20, 150, C_LINK_HOV)
        else:
            # Отрисовка контента страницы
            y = 66
            for elem in page["content"]:
                etype = elem[0]
                text = elem[1]

                if etype == "h1":
                    draw_text(t, text[:36], 12, y, rgb(255, 215, 0))
                    y += 15
                elif etype == "p":
                    draw_text(t, text[:36], 12, y, C_WHITE)
                    y += 13
                elif etype == "hr":
                    t.line(10, y + 4, W - 10, y + 4, rgb(45, 54, 75))
                    y += 10
                elif etype == "box":
                    t.fill_rect(10, y, W - 20, 14, rgb(24, 30, 44))
                    t.rect(10, y, W - 20, 14, rgb(60, 75, 105))
                    draw_text(t, text[:34], 16, y + 3, rgb(0, 240, 255))
                    y += 18
                elif etype == "link":
                    target = elem[2]
                    self.links.append((y, text, target))
                    y += 15

            # Отрисовка ссылок с подсветкой выбранной
            for idx, (ly, ltext, ltarget) in enumerate(self.links):
                is_sel = (idx == self.link_sel)
                if is_sel:
                    t.fill_rect(8, ly - 2, len(ltext) * 8 + 8, 13, rgb(0, 80, 160))
                    t.rect(8, ly - 2, len(ltext) * 8 + 8, 13, C_IE_BLUE)
                    draw_text(t, ltext, 12, ly, C_LINK_HOV)
                else:
                    draw_text(t, ltext, 12, ly, C_LINK)

        # 5. Строка состояния браузера (Y = 204..217)
        t.fill_rect(0, 204, W, 14, rgb(28, 32, 44))
        t.line(0, 204, W, 204, C_BORDER)
        draw_text(t, "Зона: RobotNet 100 Мбит/с", 8, 207, C_DARK_GRAY)
        draw_text(t, "Готово", 260, 207, rgb(0, 230, 120))

        # 6. Системная панель задач с буквой 'e'
        draw_system_taskbar(t, self.cfg, active_tab="Explorer", tab_icon="explorer")

        t.show()

    def run(self):
        self.draw_browser()

        while True:
            ev = self.inputs.get_event()
            if not ev:
                time.sleep_ms(25)
                continue

            if ev in ('BACK', 'ESC'):
                self.click_sound(600, 20)
                return

            # Навигация между ссылками на странице
            elif ev == 'DOWN':
                if self.links:
                    self.link_sel = (self.link_sel + 1) % len(self.links)
                    self.click_sound(900, 8)
                    self.draw_browser()

            elif ev == 'UP':
                if self.links:
                    self.link_sel = (self.link_sel - 1) % len(self.links)
                    self.click_sound(900, 8)
                    self.draw_browser()

            # Переход по выбранной ссылке
            elif ev in ('ENTER', ' '):
                if self.links:
                    target_url = self.links[self.link_sel][2]
                    self.navigate_to(target_url)

            # Быстрые клавиши:
            elif ev in ('b', 'B', 'и', 'И', 'LEFT'):
                self.go_back()
                self.draw_browser()

            elif ev in ('f', 'F', 'а', 'А', 'RIGHT'):
                self.go_forward()
                self.draw_browser()

            elif ev in ('h', 'H', 'р', 'Р'):
                self.navigate_to(sites_data.HOME_URL)

            # Быстрый переход по цифрам 1..4 по закладкам!
            elif ev in ('1', '2', '3', '4'):
                b_idx = int(ev) - 1
                if b_idx < len(QUICK_BOOKMARKS):
                    self.navigate_to(QUICK_BOOKMARKS[b_idx][1])