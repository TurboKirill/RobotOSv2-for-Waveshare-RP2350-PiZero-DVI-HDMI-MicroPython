# app_games.py - Игровой центр Xbox Game Pass для RobotOS (DVI 320x240)
# Полноэкранная библиотека игр, постеры, управление пакетами и запуск
import time
import math
import struct
import gc
import sys
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar
import apps_reg

W, H = 320, 240
VIS = 3                      # сколько карточек помещается на экране
TB_H = 22
WIN_H = H - TB_H  # 218px

# Фирменная палитра Xbox Game Pass
C_BG         = rgb(16, 18, 24)       # Тёмный фон Xbox
C_HEADER     = rgb(24, 28, 38)       # Шапка окна
C_CARD_BG    = rgb(26, 30, 42)       # Карточки игр
C_CARD_HOV   = rgb(36, 44, 62)       # Выбранная карточка
C_BORDER     = rgb(48, 56, 76)       # Границы
C_XBOX_GREEN = rgb(16, 185, 75)      # Неоново-зеленый Xbox
C_WHITE      = 0xFFFF
C_GRAY       = rgb(140, 150, 170)
C_DARK_GRAY  = rgb(90, 100, 120)

# Встроенные игры (для них нарисованы обложки). Остальные игры берутся из реестра apps_reg.
GAMES_CATALOG = [
    {
        "id": 0,
        "title": "Арканоид",
        "genre": "Аркада",
        "size": "14 KB",
        "module": "app_arkanoid",
        "app_class": "ArkanoidApp",
        "status": "Установлено"
    },
    {
        "id": 1,
        "title": "Змейка",
        "genre": "Аркада",
        "size": "10 KB",
        "module": "app_snake",
        "app_class": "SnakeApp",
        "status": "Установлено"
    },
    {
        "id": 2,
        "title": "DOOM 3D",
        "genre": "Шутер",
        "size": "22 KB",
        "module": "app_doom",
        "app_class": "DoomApp",
        "status": "Установлено"
    },
]

class GamesApp:
    def __init__(self, tft, audio, inputs, config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False, "hour": 20, "minute": 45}
        self.sel = 0
        self.top = 0
        self.games = []
        self.load_games()

    def load_games(self):
        """Встроенные игры + установленные через установщик (только если файл есть)."""
        games = []
        have = set()
        for g in GAMES_CATALOG:
            have.add(g["module"])
            p = apps_reg.path_of(g["module"])
            if p:
                d = {}
                d.update(g)
                d["size"] = "%d KB" % ((apps_reg.size_of(p) + 1023) // 1024)
                games.append(d)
        for e in apps_reg.menu_entries("game"):
            if e[0] in have:
                continue
            games.append({"id": 100 + len(games), "title": e[3], "genre": "Игра",
                          "size": "%d KB" % ((apps_reg.size_of(e[6]) + 1023) // 1024),
                          "module": e[0], "app_class": e[1], "status": "Установлено"})
        self.games = games
        if self.sel >= len(games):
            self.sel = max(0, len(games) - 1)

    def beep(self, freq=1200, ms=15):
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

    def show_dialog(self, title, lines):
        dw, dh = 240, 96
        dx = (W - dw) // 2
        dy = (WIN_H - dh) // 2
        t = self.tft

        t.fill_rect(dx, dy, dw, dh, rgb(28, 32, 44))
        t.rect(dx, dy, dw, dh, C_XBOX_GREEN)
        t.fill_rect(dx + 2, dy + 2, dw - 4, 18, rgb(38, 44, 60))
        draw_text(t, title, dx + 8, dy + 6, C_WHITE)

        yy = dy + 28
        for line in lines:
            draw_text(t, line[:28], dx + 12, yy, C_WHITE)
            yy += 15

        t.fill_rect(dx + (dw - 50) // 2, dy + dh - 22, 50, 16, C_XBOX_GREEN)
        t.text("OK", dx + (dw - 50) // 2 + 18, dy + dh - 18, C_WHITE)
        t.show()

        self.beep(1200, 15)
        while True:
            ev = self.inputs.get_event()
            if ev in ("ENTER", "BACK", "ESC", " "):
                self.beep(900, 15)
                break
            time.sleep_ms(20)

    # ------------------------------------------------------------ Иллюстрации обложек
    def draw_poster(self, game_id, px, py, pw, ph):
        t = self.tft

        if game_id == 0:
            # 1. Арканоид (Космос, цветные кирпичи, ракетка и мяч)
            t.fill_rect(px, py, pw, ph, rgb(10, 14, 26))
            cols = [rgb(255, 50, 70), rgb(255, 140, 20), rgb(255, 220, 20), rgb(0, 230, 100)]
            for r, c in enumerate(cols):
                for b in range(5):
                    t.fill_rect(px + 4 + b * 16, py + 8 + r * 7, 13, 5, c)
            t.fill_rect(px + 24, py + ph - 14, 36, 5, rgb(0, 220, 255))
            t.fill_rect(px + 40, py + ph - 24, 4, 4, C_WHITE)

        elif game_id == 1:
            # 2. Змейка (Неоновый киберпанк)
            t.fill_rect(px, py, pw, ph, rgb(6, 18, 12))
            for gx in range(px + 10, px + pw, 14):
                t.vline(gx, py, ph, rgb(12, 30, 20))
            for gy in range(py + 10, py + ph, 14):
                t.hline(px, gy, pw, rgb(12, 30, 20))
            s_col = rgb(0, 255, 80)
            t.fill_rect(px + 12, py + 45, 30, 7, s_col)
            t.fill_rect(px + 35, py + 25, 7, 27, s_col)
            t.fill_rect(px + 35, py + 25, 24, 7, s_col)
            t.fill_rect(px + 54, py + 26, 2, 2, C_WHITE)
            t.fill_rect(px + 64, py + 44, 7, 7, rgb(255, 40, 40))
            t.fill_rect(px + 66, py + 42, 2, 2, rgb(0, 230, 80))

        elif game_id == 2:
            # 3. DOOM 3D (Кроваво-красный адский коридор)
            t.fill_rect(px, py, pw, ph, rgb(50, 10, 10))
            t.fill_rect(px, py, 14, ph, rgb(110, 30, 30))
            t.fill_rect(px + pw - 14, py, 14, ph, rgb(110, 30, 30))
            t.fill_rect(px + 14, py + 12, 10, ph - 24, rgb(80, 20, 20))
            t.fill_rect(px + pw - 24, py + 12, 10, ph - 24, rgb(80, 20, 20))
            t.fill_rect(px + 24, py + ph - 20, pw - 48, 20, rgb(24, 20, 20))
            draw_text(t, "DOOM", px + 28, py + 22, rgb(255, 220, 0))
            t.fill_rect(px + pw // 2 - 4, py + ph - 16, 8, 16, rgb(160, 165, 175))

    def draw_generic_poster(self, seed, px, py, pw, ph):
        """Обложка для установленных игр: цветной фон (от названия) и геймпад."""
        t = self.tft
        h = 0
        for ch in seed:
            h += ord(ch)
        t.fill_rect(px, py, pw, ph, rgb(20 + (h * 7) % 60, 20 + (h * 13) % 60, 40 + (h * 5) % 80))
        bx = px + pw // 2 - 22
        by = py + ph // 2 - 10
        body = rgb(190, 195, 210)
        t.fill_rect(bx, by, 44, 22, body)
        t.fill_rect(bx - 5, by + 6, 6, 16, body)
        t.fill_rect(bx + 43, by + 6, 6, 16, body)
        t.fill_rect(bx + 8, by + 8, 10, 3, rgb(40, 44, 56))      # крестовина
        t.fill_rect(bx + 11, by + 5, 4, 9, rgb(40, 44, 56))
        t.fill_rect(bx + 28, by + 7, 4, 4, C_XBOX_GREEN)         # кнопки
        t.fill_rect(bx + 34, by + 11, 4, 4, rgb(255, 80, 80))

    # ------------------------------------------------------------ Отрисовка витрины
    def draw_catalog(self):
        t = self.tft

        # 1. Шапка окна Xbox (Y = 0..19)
        t.fill_rect(0, 0, W, 20, C_HEADER)
        t.line(0, 19, W, 19, C_BORDER)
        draw_text(t, "Xbox Games", 10, 6, C_WHITE)
        t.text("Esc", 294, 6, C_WHITE)

        # 2. Фон рабочей области
        t.fill_rect(0, 20, W, 198, C_BG)

        # Подзаголовок витрины
        draw_text(t, "БИБЛИОТЕКА ИГР", 14, 25, C_WHITE)
        draw_text(t, "Game Pass", 145, 25, C_XBOX_GREEN)

        # 3. Карточки игр
        card_w = 92
        card_h = 144
        start_x = 12
        card_y = 40

        n = len(self.games)
        if self.sel < self.top:
            self.top = self.sel
        if self.sel >= self.top + VIS:
            self.top = self.sel - VIS + 1
        if n > VIS:
            draw_text(t, "%d/%d" % (self.sel + 1, n), 250, 6, C_GRAY)
            if self.top > 0:
                t.text("<", 2, 104, C_XBOX_GREEN)
            if self.top + VIS < n:
                t.text(">", 311, 104, C_XBOX_GREEN)

        for i in range(self.top, min(n, self.top + VIS)):
            game = self.games[i]
            cx = start_x + (i - self.top) * (card_w + 10)
            is_sel = (i == self.sel)

            # Фон карточки
            bg = C_CARD_HOV if is_sel else C_CARD_BG
            t.fill_rect(cx, card_y, card_w, card_h, bg)
            # Подсветка неоновым зеленым для выбранной игры
            t.rect(cx, card_y, card_w, card_h, C_XBOX_GREEN if is_sel else C_BORDER)

            # Постер
            if game["id"] < 100:
                self.draw_poster(game["id"], cx + 4, card_y + 4, card_w - 8, 72)
            else:
                self.draw_generic_poster(game["module"], cx + 4, card_y + 4, card_w - 8, 72)
            t.rect(cx + 4, card_y + 4, card_w - 8, 72, rgb(45, 52, 70))

            # Название и жанр
            draw_text(t, game["title"][:10], cx + 6, card_y + 82, C_WHITE if is_sel else rgb(200, 205, 215))
            draw_text(t, game["genre"][:10], cx + 6, card_y + 96, C_GRAY)

            # Кнопка действия [ИГРАТЬ]
            btn_y = card_y + 116
            if is_sel:
                t.fill_rect(cx + 6, btn_y, card_w - 12, 18, C_XBOX_GREEN)
                draw_text(t, "ИГРАТЬ", cx + 20, btn_y + 5, C_WHITE)
            else:
                t.fill_rect(cx + 6, btn_y, card_w - 12, 18, rgb(20, 24, 32))
                t.rect(cx + 6, btn_y, card_w - 12, 18, C_BORDER)
                draw_text(t, "Готово", cx + 22, btn_y + 5, C_GRAY)

        # 4. Панель подсказок снизу
        t.fill_rect(0, 194, W, 24, rgb(14, 16, 22))
        t.line(0, 194, W, 194, C_BORDER)
        draw_text(t, "СТРЕЛКИ:Выбор  ENTER:Играть  I:Инфо", 10, 202, rgb(140, 150, 170))

        # 5. Системная панель задач с зеленой плиткой Xbox
        draw_system_taskbar(t, self.cfg, active_tab="Xbox", tab_icon="xbox")

        t.show()

    # ------------------------------------------------------------ Запуск игр
    def launch_selected_game(self):
        g = self.games[self.sel]
        mod_name = g["module"]
        mod = None
        game_instance = None

        # 1. Принудительно вычищаем память ПЕРЕД импортом тяжелого 3D-движка!
        gc.collect()

        try:
            mod = __import__(mod_name)
            gc.collect() # 2. Подчищаем хвосты после компиляции
            app_cls = getattr(mod, g["app_class"])
            game_instance = app_cls(self.tft, self.audio, self.inputs, self.cfg)
            game_instance.run()
        except Exception as e:
            self.show_dialog("Ошибка запуска", [f"Не удалось запустить {g['title']}:", str(e)[:24]])
        finally:
            mod = None
            game_instance = None
            if mod_name in sys.modules:
                del sys.modules[mod_name]
            gc.collect()

    def run(self):
        self.load_games()
        if not self.games:
            self.show_dialog("Xbox Games", ["Игр не найдено.", "Установите их в Параметры -", "Игры."])
            return
        while True:
            self.draw_catalog()

            ev = self.inputs.get_event()
            if not ev:
                time.sleep_ms(20)
                continue

            if ev in ('BACK', 'ESC'):
                self.beep(600, 25)
                return

            elif ev == 'LEFT':
                self.sel = (self.sel - 1) % len(self.games)
                self.beep(900, 10)

            elif ev == 'RIGHT':
                self.sel = (self.sel + 1) % len(self.games)
                self.beep(900, 10)

            elif ev in ('ENTER', ' '):
                self.beep(1400, 25)
                self.launch_selected_game()

            elif ev in ('i', 'I', 'ш', 'Ш'):
                # Просмотр информации об игре
                g = self.games[self.sel]
                self.show_dialog("Свойства игры", [
                    f"Название: {g['title']}",
                    f"Жанр:     {g['genre']}",
                    f"Размер:   {g['size']}",
                    f"Статус:   {g['status']}"
                ])