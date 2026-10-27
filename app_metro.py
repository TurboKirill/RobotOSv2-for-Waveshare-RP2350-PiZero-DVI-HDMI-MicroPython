# app_metro.py - Живой плиточный рабочий стол Windows 10 / Metro UI (DVI 320x240)
# Минимальные щели 3px (Windows 10 Mosaic), плотная сетка, без обрезки текста
import time
import math
import struct
import random
import gc
import sys
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar, draw_xbox, START_MENU_ITEMS

W, H = 320, 240
TB_H = 22
TB_Y = H - TB_H  # 218px

# Палитра Metro UI
C_BG    = rgb(10, 12, 16)       # Глубокий тёмный фон (тонкие щели 3px)
C_WHITE = 0xFFFF
C_GRAY  = rgb(140, 145, 155)
C_DARK  = rgb(22, 26, 36)
C_CYAN  = rgb(0, 220, 255)      # Неоновый цвет глаз робота

# Сетка 11 плиток: плотная посадка с зазорами ровно 3px!
# Ряд 0: Y = 3..71  (H=68)
# Ряд 1: Y = 74..142 (H=68)
# Ряд 2: Y = 145..214 (H=69)
TILES = [
    # Ряд 0
    {"id": 0, "title": "Robot Core",  "x": 4,   "y": 3,   "w": 153, "h": 68, "color": rgb(0, 120, 215), "app": "robot"},
    {"id": 1, "title": "Xbox",        "x": 160, "y": 3,   "w": 76,  "h": 68, "color": rgb(16, 124, 65),  "app": "games"},
    {"id": 2, "title": "Explorer",    "x": 239, "y": 3,   "w": 77,  "h": 68, "color": rgb(0, 140, 240), "app": "browser"},
    # Ряд 1
    {"id": 3, "title": "Плеер",       "x": 4,   "y": 74,  "w": 75,  "h": 68, "color": rgb(215, 60, 40),  "app": "player"},
    {"id": 4, "title": "Файлы",       "x": 82,  "y": 74,  "w": 75,  "h": 68, "color": rgb(230, 140, 0), "app": "files"},
    {"id": 5, "title": "Галерея",     "x": 160, "y": 74,  "w": 76,  "h": 68, "color": rgb(140, 45, 200), "app": "gallery"},
    {"id": 6, "title": "Погода",      "x": 239, "y": 74,  "w": 77,  "h": 68, "color": rgb(0, 175, 120), "app": "weather"},
    # Ряд 2
    {"id": 7, "title": "Видео",       "x": 4,   "y": 145, "w": 75,  "h": 69, "color": rgb(240, 110, 20), "app": "video"},
    {"id": 8, "title": "Диспетчер",   "x": 82,  "y": 145, "w": 75,  "h": 69, "color": rgb(45, 55, 80),   "app": "htop"},
    {"id": 9, "title": "Опции",       "x": 160, "y": 145, "w": 76,  "h": 69, "color": rgb(65, 75, 90),   "app": "settings"},
    {"id": 10,"title": "Сон",         "x": 239, "y": 145, "w": 77,  "h": 69, "color": rgb(35, 45, 115),  "app": "sleep"},
]

NAV = {
    "RIGHT": {0: 1, 1: 2, 3: 4, 4: 5, 5: 6, 7: 8, 8: 9, 9: 10},
    "LEFT":  {1: 0, 2: 1, 4: 3, 5: 4, 6: 5, 8: 7, 9: 8, 10: 9},
    "DOWN":  {0: 3, 1: 5, 2: 6, 3: 7, 4: 8, 5: 9, 6: 10, 7: "TB_START", 8: "TB_START", 9: "TB_CLOCK", 10: "TB_CLOCK"},
    "UP":    {3: 0, 4: 0, 5: 1, 6: 2, 7: 3, 8: 4, 9: 5, 10: 6},
}

class MetroDesktop:
    def __init__(self, gui):
        self.gui = gui
        self.tft = gui.tft
        self.audio = gui.audio
        self.inputs = gui.inputs
        self.cfg = gui.cfg

        self.sel = 0
        self.flipped = [False] * len(TILES)
        self.active_flip = -1
        self.last_flip_time = time.ticks_ms()
        self.last_input = time.ticks_ms()
        
        # Моргание глазок робота
        self.last_blink_time = time.ticks_ms()
        self.is_blinking = False

    def draw_round_rect(self, x, y, w, h, r, color):
        if r <= 0 or h <= 2 * r or w <= 2 * r:
            self.tft.fill_rect(int(x), int(y), int(w), int(h), color)
            return
        self.tft.fill_rect(int(x), int(y + r), int(w), int(h - 2 * r), color)
        for dy in range(r):
            y_dist = r - dy
            dx = int(math.sqrt(r * r - y_dist * y_dist))
            line_w = w - 2 * r + 2 * dx
            self.tft.fill_rect(int(x + r - dx), int(y + dy), int(line_w), 1, color)
            self.tft.fill_rect(int(x + r - dx), int(y + h - 1 - dy), int(line_w), 1, color)

    def draw_tile_content(self, idx, x, y, w, h, is_back):
        t = TILES[idx]
        col = C_DARK if is_back else t["color"]
        self.tft.fill_rect(x, y, w, h, col)

        if w < t["w"] - 10:
            return

        # ---------------- ЛИЦЕВАЯ СТОРОНА ПЛИТКИ ----------------
        if not is_back:
            if idx == 0:
                # 🤖 Robot Core: Моргающие глазки
                eh = 6 if self.is_blinking else 30
                ey = y + 11 + (12 if self.is_blinking else 0)
                er = 2 if self.is_blinking else 7
                self.draw_round_rect(x + 14, ey, 22, eh, er, C_CYAN)
                self.draw_round_rect(x + 42, ey, 22, eh, er, C_CYAN)

                # Текст чётко помещается, ничего не режется
                draw_text(self.tft, "Robot Core", x + 72, y + 14, C_WHITE)
                draw_text(self.tft, "Мимика AI", x + 72, y + 28, C_CYAN)
                draw_text(self.tft, "Робототехника", x + 12, y + h - 15, rgb(200, 225, 245))

            elif idx == 1:
                # 🎮 Xbox
                draw_xbox(self.tft, x + w - 28, y + 8, 18)
                draw_text(self.tft, t["title"], x + 8, y + h - 15, C_WHITE)

            elif idx == 2:
                # 🌐 Буква 'e' в правом верхнем углу (как у всех плиток)
                ix = x + w - 26
                iy = y + 8
                bg = t["color"]

                # 1. Белое тело буквы 'e' (18х18 px)
                self.tft.fill_rect(ix + 1, iy, 16, 18, C_WHITE)

                # 2. Вырезы, формирующие букву 'e':
                self.tft.fill_rect(ix + 4, iy + 3, 10, 4, bg)      # верхняя дырочка глаза
                self.tft.fill_rect(ix + 1, iy + 7, 16, 3, C_WHITE) # перемычка буквы
                self.tft.fill_rect(ix + 7, iy + 11, 10, 4, bg)     # нижний правый вырез

                # Название внизу слева (как у всех плиток)
                draw_text(self.tft, t["title"], x + 8, y + h - 15, C_WHITE)
            elif idx == 3:
                # 🎵 Плеер
                ex, ey = x + w - 26, y + 10
                hs = [6, 14, 20, 10, 16]
                for i in range(5):
                    self.tft.fill_rect(ex + i * 4, ey + 20 - hs[i], 3, hs[i], C_WHITE)
                draw_text(self.tft, t["title"], x + 8, y + h - 15, C_WHITE)

            elif idx == 4:
                # 📁 Файлы
                fx, fy = x + w - 26, y + 10
                self.tft.fill_rect(fx, fy + 2, 6, 2, C_WHITE)
                self.tft.fill_rect(fx, fy + 4, 18, 12, rgb(255, 220, 80))
                self.tft.fill_rect(fx + 2, fy + 3, 14, 3, C_WHITE)
                self.tft.fill_rect(fx, fy + 6, 18, 10, C_WHITE)
                draw_text(self.tft, t["title"], x + 8, y + h - 15, C_WHITE)

            elif idx == 5:
                # 🖼️ Галерея
                gx, gy = x + w - 28, y + 8
                self.tft.fill_rect(gx, gy, 20, 16, rgb(40, 20, 60))
                self.tft.rect(gx, gy, 20, 16, C_WHITE)
                self.tft.fill_rect(gx + 12, gy + 3, 4, 4, rgb(255, 215, 0)) # солнце
                self.tft.fill_rect(gx + 3, gy + 11, 7, 4, rgb(0, 220, 120))  # гора
                self.tft.fill_rect(gx + 8, gy + 8, 9, 7, rgb(0, 180, 240))
                draw_text(self.tft, t["title"], x + 8, y + h - 15, C_WHITE)

            elif idx == 6:
                # ☀️ Погода: без знака вопроса, аккуратный градус!
                draw_text(self.tft, "+24", x + 8, y + 12, rgb(255, 220, 40))
                # Пиксельный кружок градуса °
                self.tft.rect(x + 34, y + 11, 4, 4, rgb(255, 220, 40))
                draw_text(self.tft, "C", x + 40, y + 12, rgb(255, 220, 40))
                draw_text(self.tft, "Ясно", x + 8, y + 28, rgb(200, 225, 245))

                # Солнце с облачком
                sx, sy = x + w - 26, y + 8
                self.tft.fill_rect(sx + 2, sy, 7, 7, rgb(255, 140, 0))
                self.tft.fill_rect(sx + 4, sy + 5, 10, 6, C_WHITE)
                draw_text(self.tft, t["title"], x + 8, y + h - 15, C_WHITE)

            elif idx == 7:
                # 🎬 Видео Play
                vx, vy = x + w - 24, y + 10
                self.tft.fill_rect(vx, vy, 16, 14, rgb(255, 160, 40))
                self.tft.fill_rect(vx + 4, vy + 3, 2, 8, C_WHITE)
                self.tft.fill_rect(vx + 6, vy + 4, 2, 6, C_WHITE)
                self.tft.fill_rect(vx + 8, vy + 5, 2, 4, C_WHITE)
                self.tft.fill_rect(vx + 10, vy + 6, 2, 2, C_WHITE)
                draw_text(self.tft, t["title"], x + 8, y + h - 15, C_WHITE)

            elif idx == 8:
                # 📊 Диспетчер задач HTOP
                hx, hy = x + w - 24, y + 10
                self.tft.fill_rect(hx, hy + 8, 4, 8, rgb(0, 230, 120))
                self.tft.fill_rect(hx + 5, hy + 4, 4, 12, rgb(255, 215, 0))
                self.tft.fill_rect(hx + 10, hy, 4, 16, rgb(255, 70, 70))
                draw_text(self.tft, t["title"][:7], x + 8, y + h - 15, C_WHITE)

            elif idx == 9:
                # ⚙️ Настройки: чёткая шестерёнка
                sx, cy_s = x + w - 22, y + 18
                self.tft.fill_rect(sx - 5, cy_s - 5, 11, 11, C_WHITE)
                self.tft.fill_rect(sx - 2, cy_s - 2, 5, 5, t["color"]) # дырочка
                self.tft.fill_rect(sx - 2, cy_s - 8, 5, 3, C_WHITE)
                self.tft.fill_rect(sx - 2, cy_s + 6, 5, 3, C_WHITE)
                self.tft.fill_rect(sx - 8, cy_s - 2, 3, 5, C_WHITE)
                self.tft.fill_rect(sx + 6, cy_s - 2, 3, 5, C_WHITE)
                draw_text(self.tft, t["title"], x + 8, y + h - 15, C_WHITE)

            elif idx == 10:
                # 🌙 Настоящий серп месяца в правом верхнем углу (концы обрезаны и заострены)
                mx = x + w - 27
                my = y + 8
                m_col = rgb(255, 235, 120) # Тёплый лунный свет

                # Рисуем гладкий серп со скошенными концами:
                self.tft.fill_rect(mx + 6, my,      3, 2, m_col) # верхний острый кончик
                self.tft.fill_rect(mx + 4, my + 2,  4, 2, m_col)
                self.tft.fill_rect(mx + 2, my + 4,  5, 2, m_col)
                self.tft.fill_rect(mx + 1, my + 6,  5, 6, m_col) # пузико месяца слева
                self.tft.fill_rect(mx + 2, my + 12, 5, 2, m_col)
                self.tft.fill_rect(mx + 4, my + 14, 4, 2, m_col)
                self.tft.fill_rect(mx + 6, my + 16, 3, 2, m_col) # нижний острый кончик

                # Две сияющие звёздочки в правом пространстве
                self.tft.fill_rect(mx + 12, my + 5, 3, 1, C_WHITE)
                self.tft.fill_rect(mx + 13, my + 4, 1, 3, C_WHITE)
                self.tft.fill_rect(mx + 15, my + 12, 2, 2, rgb(255, 255, 180))

                # Название внизу слева
                draw_text(self.tft, t["title"], x + 8, y + h - 15, C_WHITE)
        # ---------------- ОБОРОТНАЯ СТОРОНА (LIVE ДАННЫЕ) ----------------
        else:
            if idx == 0:
                eh = 4 if self.is_blinking else 20
                ey = y + 10 + (8 if self.is_blinking else 0)
                self.draw_round_rect(x + 14, ey, 16, eh, 4, C_CYAN)
                self.draw_round_rect(x + 36, ey, 16, eh, 4, C_CYAN)
                draw_text(self.tft, "RP2350 DVI", x + 62, y + 10, rgb(0, 210, 255))
                draw_text(self.tft, "SRAM:520KB", x + 62, y + 26, C_WHITE)
                draw_text(self.tft, "9 анимаций", x + 14, y + 46, rgb(0, 230, 120))
            elif idx == 1:
                draw_text(self.tft, "XBOX HUB", x + 6, y + 10, rgb(16, 210, 80))
                draw_text(self.tft, "DOOM 3D", x + 6, y + 26, C_WHITE)
                draw_text(self.tft, "Арканоид", x + 6, y + 42, C_GRAY)
            elif idx == 2:
                draw_text(self.tft, "WEB NET", x + 6, y + 10, rgb(0, 210, 255))
                draw_text(self.tft, "YouTube", x + 6, y + 26, C_WHITE)
                draw_text(self.tft, "Онлайн", x + 6, y + 42, rgb(0, 230, 120))
            elif idx == 3:
                draw_text(self.tft, "АУДИО", x + 8, y + 10, C_WHITE)
                draw_text(self.tft, "I2S MONO", x + 8, y + 26, rgb(255, 90, 70))
                draw_text(self.tft, "22050Гц", x + 8, y + 42, C_GRAY)
            elif idx == 4:
                draw_text(self.tft, "ДИСК", x + 8, y + 10, C_WHITE)
                draw_text(self.tft, "/sd Card", x + 8, y + 26, rgb(255, 180, 0))
                draw_text(self.tft, "Flash: /", x + 8, y + 42, C_GRAY)
            elif idx == 5:
                draw_text(self.tft, "ФОТО", x + 8, y + 10, C_WHITE)
                draw_text(self.tft, "BMP/RAW", x + 8, y + 26, rgb(200, 100, 255))
                draw_text(self.tft, "320x240", x + 8, y + 42, C_GRAY)
            elif idx == 6:
                draw_text(self.tft, "КЛИМАТ", x + 6, y + 10, rgb(0, 210, 255))
                draw_text(self.tft, "Влаж:45%", x + 6, y + 26, C_WHITE)
                draw_text(self.tft, "340 Люкс", x + 6, y + 42, rgb(255, 200, 40))
            elif idx == 7:
                draw_text(self.tft, "ВИДЕО", x + 8, y + 10, C_WHITE)
                draw_text(self.tft, "160x120", x + 8, y + 26, rgb(255, 140, 20))
                draw_text(self.tft, "SD Поток", x + 8, y + 42, C_GRAY)
            elif idx == 8:
                draw_text(self.tft, "ПАМЯТЬ", x + 8, y + 10, C_WHITE)
                draw_text(self.tft, "150 МГц", x + 8, y + 26, rgb(160, 100, 220))
                draw_text(self.tft, "GC: OK", x + 8, y + 42, rgb(0, 230, 120))
            else:
                draw_text(self.tft, "СИСТЕМА", x + 8, y + 14, rgb(0, 230, 120))
                draw_text(self.tft, "Готова", x + 8, y + 36, C_WHITE)

    def draw_tile(self, idx):
        p = TILES[idx]
        self.draw_tile_content(idx, p["x"], p["y"], p["w"], p["h"], self.flipped[idx])
        if idx == self.sel:
            self.tft.rect(p["x"] - 2, p["y"] - 2, p["w"] + 4, p["h"] + 4, 0xFFFF)
            self.tft.rect(p["x"] - 1, p["y"] - 1, p["w"] + 2, p["h"] + 2, rgb(0, 160, 255))

    def flip_tile_3d(self, idx):
        """Плавный переворот с 3D-сжатием по косинусу"""
        p = TILES[idx]
        x, y, w, h = p["x"], p["y"], p["w"], p["h"]
        cur = self.flipped[idx]

        for deg in (25, 55, 80, 90, 105, 130, 160, 180):
            draw_w = max(4, int(w * abs(math.cos(math.radians(deg)))))
            draw_x = x + (w - draw_w) // 2
            self.tft.fill_rect(x, y, w, h, C_BG)
            show_back = (not cur) if deg >= 90 else cur
            self.draw_tile_content(idx, draw_x, y, draw_w, h, show_back)
            self.tft.show()
            time.sleep_ms(12)

        self.flipped[idx] = not cur

    def flip_random_tile(self):
        candidates = [i for i in range(len(TILES)) if i != self.active_flip]
        if self.active_flip != -1 and self.flipped[self.active_flip]:
            self.flip_tile_3d(self.active_flip)
            time.sleep_ms(25)

        self.active_flip = random.choice(candidates)
        self.flip_tile_3d(self.active_flip)
        self.render_all()

    def render_all(self):
        self.tft.fill(C_BG)
        for i in range(len(TILES)):
            self.draw_tile(i)

        tb_active = "START" if self.sel == 11 else None
        draw_system_taskbar(self.tft, self.cfg, active_tab=tb_active)

        if self.sel == 12:
            self.tft.fill_rect(273, TB_Y, 47, TB_H, rgb(48, 52, 64))
            clock_str = "%02d:%02d" % (self.cfg.get("hour", 20), self.cfg.get("minute", 45))
            self.tft.text(clock_str, 276, TB_Y + 7, rgb(0, 220, 255))

        self.tft.show()

    def launch_app(self, app_key):
        self.gui.click_sound(1400, 25)
        if self.active_flip != -1:
            self.flipped[self.active_flip] = False
            self.active_flip = -1

        try:
            if app_key == "robot":
                self.gui.menu_robot()
            elif app_key == "games":
                self.gui.menu_games()
            elif app_key == "browser":
                import app_browser
                self.gui.launch(lambda: app_browser.BrowserApp(self.tft, self.audio, self.inputs, self.cfg))
                del sys.modules["app_browser"]
            elif app_key == "player":
                import app_player
                self.gui.launch(lambda: app_player.MusicPlayerApp(self.tft, self.audio, self.inputs, self.cfg))
                del sys.modules["app_player"]
            elif app_key == "files":
                import app_files
                self.gui.launch(lambda: app_files.FileManagerApp(self.tft, self.audio, self.inputs, self.cfg))
                del sys.modules["app_files"]
            elif app_key == "gallery":
                import app_gallery
                self.gui.launch(lambda: app_gallery.GalleryApp(self.tft, self.audio, self.inputs, self.cfg))
                del sys.modules["app_gallery"]
            elif app_key == "weather":
                import app_weather
                self.gui.launch(lambda: app_weather.WeatherApp(self.tft, self.audio, self.inputs, self.cfg))
                del sys.modules["app_weather"]
            elif app_key == "video":
                import app_video
                self.gui.launch(lambda: app_video.VideoPlayerApp(self.tft, self.audio, self.inputs, self.cfg))
                del sys.modules["app_video"]
            elif app_key == "htop":
                import app_htop
                self.gui.launch(lambda: app_htop.HtopApp(self.tft, self.audio, self.inputs, self.cfg))
                del sys.modules["app_htop"]
            elif app_key == "settings":
                import app_settings
                self.gui.launch(lambda: app_settings.SettingsApp(self.tft, self.audio, self.inputs, self.cfg))
                del sys.modules["app_settings"]
            elif app_key == "sleep":
                import app_sleep
                self.gui.launch(lambda: app_sleep.SleepApp(self.tft, self.audio, self.inputs, self.cfg, None))
                del sys.modules["app_sleep"]
        except Exception as e:
            self.gui.show_error(e)

        gc.collect()
        self.last_input = time.ticks_ms()
        self.render_all()

    def draw_bg_quiet(self):
        """Тихая отрисовка плиток под календарём без вызова show() (без мерцания!)"""
        self.tft.fill(C_BG)
        for i in range(len(TILES)):
            self.draw_tile(i)
        draw_system_taskbar(self.tft, self.cfg)
        # Подсвечиваем кнопку часов
        self.tft.fill_rect(273, TB_Y, 47, TB_H, rgb(48, 52, 64))
        clock_str = "%02d:%02d" % (self.cfg.get("hour", 20), self.cfg.get("minute", 45))
        self.tft.text(clock_str, 276, TB_Y + 7, rgb(0, 220, 255))
    
    def run_loop(self):
        self.render_all()

        while True:
            if self.cfg.get("desktop_mode", "classic") != "metro":
                return

            now = time.ticks_ms()

            # Часы на панели
            if self.gui.update_clock(now):
                draw_system_taskbar(self.tft, self.cfg)
                self.tft.show()

            # Моргание глазок робота
            if not self.is_blinking and time.ticks_diff(now, self.last_blink_time) >= 3500:
                self.is_blinking = True
                self.last_blink_time = now
                self.draw_tile(0)
                self.tft.show()
            elif self.is_blinking and time.ticks_diff(now, self.last_blink_time) >= 120:
                self.is_blinking = False
                self.draw_tile(0)
                self.tft.show()

            # Live Tiles: переворот случайной плитки раз в 4 секунды в покое
            if time.ticks_diff(now, self.last_flip_time) >= 4200 and time.ticks_diff(now, self.last_input) >= 2500:
                self.last_flip_time = now
                self.flip_random_tile()

            ev = self.inputs.get_event()
            if ev:
                self.last_input = now
                old_sel = self.sel

                # --- 1. Навигация по панели задач ---
                if self.sel == 11: # Пуск
                    if ev == 'RIGHT': self.sel = 12; self.gui.click_sound(950, 10)
                    elif ev == 'UP': self.sel = 8; self.gui.click_sound(850, 10)
                    elif ev in ('ENTER', ' '):
                        # Штатный запуск меню Пуск
                        self.gui.start_open = True
                        self.gui.start_sel = 0
                        self.gui.click_sound(1200, 20)
                        self.gui.draw_start_menu()
                        self.tft.show()
                        while self.gui.start_open:
                            sev = self.inputs.get_event()
                            if not sev:
                                time.sleep_ms(20); continue
                            if sev == 'UP':
                                self.gui.start_sel = (self.gui.start_sel - 1) % len(START_MENU_ITEMS)
                                self.gui.click_sound(900, 10)
                                self.gui.draw_start_menu()
                                self.tft.show()
                            elif sev == 'DOWN':
                                self.gui.start_sel = (self.gui.start_sel + 1) % len(START_MENU_ITEMS)
                                self.gui.click_sound(800, 10)
                                self.gui.draw_start_menu()
                                self.tft.show()
                            elif sev in ('BACK', 'ESC'):
                                self.gui.start_open = False
                                self.render_all()
                            elif sev == 'ENTER':
                                target = START_MENU_ITEMS[self.gui.start_sel][1]
                                self.gui.start_open = False
                                self.gui.open_section(target)
                                self.render_all()
                        continue

                elif self.sel == 12: # Часы
                    if ev == 'LEFT': self.sel = 11; self.gui.click_sound(950, 10)
                    elif ev == 'UP': self.sel = 10; self.gui.click_sound(850, 10)
                    elif ev in ('ENTER', ' '):
                        import app_calendar
                        # Передаём тихую отрисовку draw_bg_quiet!
                        self.gui.launch(lambda: app_calendar.CalendarApp(
                            self.tft, self.audio, self.inputs, self.cfg, bg_drawer=self.draw_bg_quiet))
                        del sys.modules["app_calendar"]
                        gc.collect()
                        self.render_all()
                        continue

                # --- 2. Навигация по сетке плиток ---
                elif ev in NAV:
                    target = NAV[ev].get(self.sel)
                    if target == "TB_START": self.sel = 11
                    elif target == "TB_CLOCK": self.sel = 12
                    elif target is not None: self.sel = target
                    self.gui.click_sound(900, 8)

                elif ev in ('ENTER', ' '):
                    self.launch_app(TILES[self.sel]["app"])
                    continue

                if old_sel != self.sel:
                    self.render_all()

            time.sleep_ms(20)