# gui.py - RobotOS: Windows 2000 Steel Blue Desktop + Dynamic Cyrillic Icons
# Waveshare RP2350-PiZero, DVI 320x240 (640x480@60Hz)
import time
import math
import struct
import gc
import sys
from dvi_display import color565 as rgb
import apps_reg

W, H = 320, 240
TB_H = 22                 # Высота панели задач
TB_Y = H - TB_H           # Верх панели задач (y = 218)

# ---------------------------------------------------------------- палитра
C_DESKTOP     = rgb(58, 110, 165)     # Windows 2000 Steel Blue
C_TASKBAR     = rgb(26, 28, 34)       # Тёмно-серая панель Windows 10
C_TASKBAR_SEP = rgb(48, 52, 62)       # Линия-разделитель панели
C_START_IDLE  = rgb(26, 28, 34)       # В покое сливается с панелью
C_START_HOVER = rgb(48, 52, 64)       # Подсветка кнопки и пунктов меню (светло-серый)
C_EYE_WHITE   = 0xFFFF                # Глазки робота в покое (белые)
C_EYE_CYAN    = rgb(0, 220, 255)      # Глазки при наведении (неоново-голубые)

C_SEL_BG      = rgb(0, 95, 180)       # Фон выделенного ярлыка
C_SEL_BORDER  = rgb(190, 235, 255)    # Нежно-голубая, почти белая рамка

C_MENU_BG     = rgb(30, 32, 40)       # Фон всплывающего меню Пуск
C_WHITE       = 0xFFFF
C_GRAY        = rgb(160, 165, 175)
C_DARK        = rgb(20, 22, 28)
C_LINE        = rgb(55, 60, 70)

BACK_KEYS = ("BACK", "ESC")

# ---------------------------------------------------------------- Полный русификатор для всей системы
CYR_TO_LATIN = {
    'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H',
    'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X',
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',
    'ё': 'e', 'Ё': 'E'
}

CYR_BITMAPS = {
    'Б': b'\x7e\x40\x7c\x42\x42\x42\x7c\x00', 'Г': b'\x7e\x42\x40\x40\x40\x40\x40\x00',
    'Д': b'\x1c\x24\x24\x24\x24\x7e\x42\x00', 'Ж': b'\x49\x49\x2a\x1c\x2a\x49\x49\x00',
    'З': b'\x3c\x42\x02\x1c\x02\x42\x3c\x00', 'И': b'\x42\x46\x4a\x52\x62\x42\x42\x00',
    'Й': b'\x34\x00\x42\x46\x4a\x52\x62\x00', 'Л': b'\x1e\x22\x42\x42\x42\x42\x42\x00',
    'П': b'\x7e\x42\x42\x42\x42\x42\x42\x00', 'У': b'\x42\x42\x42\x3e\x02\x04\x38\x00',
    'Ф': b'\x10\x7c\xd6\xd6\x7c\x10\x10\x00', 'Ц': b'\x44\x44\x44\x44\x44\x7e\x06\x00',
    'Ч': b'\x42\x42\x42\x3e\x02\x02\x02\x00', 'Ш': b'\x49\x49\x49\x49\x49\x7f\x00\x00',
    'Щ': b'\x49\x49\x49\x49\x7f\x01\x01\x00', 'Ъ': b'\x60\x20\x3c\x22\x22\x22\x3c\x00',
    'Ы': b'\x42\x42\x72\x4a\x4a\x72\x00\x00', 'Ь': b'\x40\x40\x7c\x42\x42\x42\x7c\x00',
    'Э': b'\x3c\x02\x02\x1e\x02\x02\x3c\x00', 'Ю': b'\x46\x49\x49\x79\x49\x49\x46\x00',
    'Я': b'\x3e\x42\x42\x3e\x12\x22\x42\x00',
    'б': b'\x3c\x40\x7c\x42\x42\x42\x7c\x00', 'в': b'\x00\x00\x7c\x42\x78\x42\x7c\x00',
    'г': b'\x00\x00\x7e\x40\x40\x40\x40\x00', 'д': b'\x00\x00\x1c\x24\x24\x7e\x42\x42',
    'ж': b'\x00\x00\x49\x2a\x1c\x2a\x49\x00', 'з': b'\x00\x00\x3c\x02\x1c\x02\x3c\x00',
    'и': b'\x00\x00\x42\x46\x4a\x52\x62\x00', 'й': b'\x34\x00\x42\x46\x4a\x52\x62\x00',
    'к': b'\x00\x00\x44\x48\x70\x48\x44\x00', 'л': b'\x00\x00\x1e\x22\x42\x42\x42\x00',
    'м': b'\x00\x00\x42\x66\x5a\x42\x42\x00', 'н': b'\x00\x00\x42\x42\x7e\x42\x42\x00',
    'п': b'\x00\x00\x7e\x42\x42\x42\x42\x00', 'т': b'\x00\x00\x7e\x10\x10\x10\x10\x00',
    'ф': b'\x00\x10\x7c\xd6\x7c\x10\x10\x00', 'ц': b'\x00\x44\x44\x44\x44\x7e\x06\x00',
    'ч': b'\x00\x00\x42\x42\x3e\x02\x02\x00', 'ш': b'\x00\x00\x49\x49\x49\x49\x7f\x00',
    'щ': b'\x00\x00\x49\x49\x49\x7f\x01\x01', 'ъ': b'\x00\x00\x60\x20\x3c\x22\x3c\x00',
    'ы': b'\x00\x00\x42\x42\x72\x4a\x72\x00', 'ь': b'\x00\x00\x40\x40\x7c\x42\x7c\x00',
    'э': b'\x00\x00\x3c\x02\x1e\x02\x3c\x00', 'ю': b'\x00\x00\x46\x49\x79\x49\x46\x00',
    'я': b'\x00\x00\x3e\x42\x3e\x12\x62\x00',
}

def draw_text(tft, text, x, y, color):
    """Единый безошибочный вывод текста во всей системе."""
    cx = x
    for ch in text:
        if ch in CYR_BITMAPS:
            bmp = CYR_BITMAPS[ch]
            for row in range(8):
                b = bmp[row]
                if b:
                    for col in range(8):
                        if b & (0x80 >> col):
                            tft.pixel(cx + col, y + row, color)
            cx += 8
        elif ch in CYR_TO_LATIN:
            tft.text(CYR_TO_LATIN[ch], cx, y, color)
            cx += 8
        elif ord(ch) < 128:
            tft.text(ch, cx, y, color)
            cx += 8
        else:
            tft.text('?', cx, y, color)
            cx += 8

# Иконки рабочего стола: по-русски сверху вниз
DESKTOP_ICONS = [
    {"id": 0, "title": "Мой компьютер", "x": 12, "y": 12},
    {"id": 1, "title": "Файлы",         "x": 12, "y": 62},
    {"id": 2, "title": "Игры",          "x": 12, "y": 112},
    {"id": 3, "title": "Корзина",       "x": 12, "y": 162},
]

# Пункты меню Пуск (чистые, без стрелок и цифр)
START_MENU_ITEMS = [
    ("Программы", 1),
    ("Игры",      2),
    ("Файлы",     4),
    ("Плеер",     3),
    ("Выполнить", 7),
    ("Настройки", 5),
    ("Сон",       6),
]

# ---------------------------------------------------------------- Логотип Xbox
C_XBOX = rgb(16, 124, 16)

XBOX_S16 = (
    0x07E0, 0x03C0, 0x0000, 0x781E,
    0x7C3E, 0xF81F, 0xF00F, 0xE3C7,
    0xE3C7, 0xC7E3, 0xCFF3, 0x5FFA,
    0x7FFE, 0x3FFC, 0x1FF8, 0x07E0,
)

def draw_xbox(t, x, y, size):
    """Логотип Xbox для рабочего стола и плиток."""
    bits, n = XBOX_S16, 16
    t.fill_rect(x, y + 2, size, size - 4, C_XBOX)
    t.fill_rect(x + 1, y + 1, size - 2, 1, C_XBOX)
    t.fill_rect(x + 1, y + size - 2, size - 2, 1, C_XBOX)
    t.fill_rect(x + 3, y, size - 6, 1, C_XBOX)
    t.fill_rect(x + 3, y + size - 1, size - 6, 1, C_XBOX)
    off = (size - n) // 2
    for r in range(n):
        row = bits[r]
        c = 0
        while c < n:
            if (row >> (n - 1 - c)) & 1:
                s = c
                while c < n and (row >> (n - 1 - c)) & 1:
                    c += 1
                t.fill_rect(x + off + s, y + off + r, c - s, 1, 0xFFFF)
            else:
                c += 1

def draw_mouse_cursor(tft, x, y):
    """Идеальная стрелочка Windows (белая с ровным хвостом и чёрным контуром)"""
    ARROW_MATRIX = (
        "B...............",
        "BB..............",
        "BWB.............",
        "BWWB............",
        "BWWWB...........",
        "BWWWWB..........",
        "BWWWWWB.........",
        "BWWWWWWB........",
        "BWWWWWWWB.......",
        "BWWWWWWWWB......",
        "BWWWBBBBBBB.....",
        "BWWBB...........",
        "BWBB............",
        "BB..............",
        "B...............",
        "................",
        "................",
    )
    for dy in range(17):
        row = ARROW_MATRIX[dy]
        for dx in range(16):
            c = row[dx]
            if c == 'W':
                tft.pixel(x + dx, y + dy, 0xFFFF)
            elif c == 'B':
                tft.pixel(x + dx, y + dy, 0x0000)

def draw_system_taskbar(tft, cfg, active_tab=None, tab_icon="folder"):
    """Универсальная панель задач RobotOS."""
    tb_y = 218
    tft.fill_rect(0, tb_y, W, TB_H, C_TASKBAR)
    tft.line(0, tb_y - 1, W, tb_y - 1, C_TASKBAR_SEP)

    # 1. Кнопка Пуск (глазки робота)
    bx, bw = 0, 26
    is_start = (active_tab == "START")
    btn_bg = C_START_HOVER if is_start else C_START_IDLE
    tft.fill_rect(bx, tb_y, bw, TB_H, btn_bg)
    eye_col = C_EYE_CYAN if is_start else C_WHITE

    ew, eh, gap = 5, 9, 3
    ex = (bw - (ew * 2 + gap)) // 2
    ey = tb_y + (TB_H - eh) // 2
    for off in (0, ew + gap):
        tft.fill_rect(ex + off, ey + 2, ew, eh - 4, eye_col)
        tft.fill_rect(ex + off + 1, ey, ew - 2, eh, eye_col)

    # 2. Активная вкладка запущенного приложения
    if active_tab and active_tab != "START":
        tab_x, tab_w = 30, 108
        tft.fill_rect(tab_x, tb_y, tab_w, TB_H, C_START_HOVER)
        fx, fy = tab_x + 6, tb_y + 4

        if tab_icon == "settings":
            tft.fill_rect(fx + 3, fy + 3, 8, 8, C_WHITE)
            tft.fill_rect(fx + 6, fy + 6, 2, 2, C_START_HOVER)
            tft.fill_rect(fx + 6, fy + 1, 2, 2, C_WHITE)
            tft.fill_rect(fx + 6, fy + 11, 2, 2, C_WHITE)
            tft.fill_rect(fx + 1, fy + 6, 2, 2, C_WHITE)
            tft.fill_rect(fx + 11, fy + 6, 2, 2, C_WHITE)
        elif tab_icon == "video":
            O = rgb(255, 140, 20)
            tft.fill_rect(fx + 1, fy, 12, 13, O)
            tft.fill_rect(fx, fy + 1, 14, 11, O)
            tft.fill_rect(fx + 4, fy + 2, 2, 9, C_WHITE)
            tft.fill_rect(fx + 6, fy + 3, 2, 7, C_WHITE)
            tft.fill_rect(fx + 8, fy + 4, 2, 5, C_WHITE)
        elif tab_icon == "explorer":
            e_col = rgb(0, 140, 240)
            tft.fill_rect(fx + 3, fy + 2, 8, 9, e_col)
            tft.fill_rect(fx + 5, fy + 4, 4, 2, rgb(26, 28, 34))
            tft.fill_rect(fx + 5, fy + 7, 4, 2, e_col)
            tft.fill_rect(fx + 6, fy + 8, 5, 2, rgb(26, 28, 34))
        elif tab_icon == "xbox":
            draw_xbox(tft, fx - 1, tb_y + 2, 16)
        elif tab_icon == "weather":
            tft.fill_rect(fx + 2, fy, 7, 7, rgb(255, 140, 0))
            tft.fill_rect(fx + 1, fy + 1, 9, 5, rgb(255, 190, 0))
            tft.fill_rect(fx + 4, fy + 5, 8, 6, C_WHITE)
        elif tab_icon == "winamp":
            tft.fill_rect(fx + 5, fy + 1, 3, 11, C_WHITE)
            tft.fill_rect(fx + 3, fy + 3, 7, 7, C_WHITE)
            tft.fill_rect(fx + 9, fy, 3, 2, rgb(255, 215, 0))
            tft.fill_rect(fx + 3, fy + 5, 8, 2, rgb(255, 200, 0))
        elif tab_icon == "htop":
            tft.fill_rect(fx + 1, fy + 7, 3, 5, rgb(0, 230, 120))
            tft.fill_rect(fx + 5, fy + 4, 3, 8, rgb(255, 215, 0))
            tft.fill_rect(fx + 9, fy + 1, 3, 11, rgb(255, 80, 80))
        elif tab_icon == "notepad":
            tft.fill_rect(fx + 2, fy, 11, 13, C_WHITE)
            tft.fill_rect(fx + 4, fy + 3, 7, 1, rgb(0, 120, 215))
        elif tab_icon == "cmd":
            tft.fill_rect(fx, fy + 1, 14, 11, C_DARK)
            tft.rect(fx, fy + 1, 14, 11, rgb(100, 110, 130))
            tft.text(">", fx + 2, fy + 3, C_WHITE)
        elif tab_icon == "player":
            tft.fill_rect(fx + 3, fy + 2, 8, 3, rgb(0, 230, 120))
            tft.fill_rect(fx + 9, fy + 3, 2, 7, rgb(0, 230, 120))
        else:
            tft.fill_rect(fx, fy + 1, 5, 2, rgb(255, 205, 50))
            tft.fill_rect(fx, fy + 3, 14, 8, rgb(230, 170, 20))
            tft.fill_rect(fx + 2, fy + 2, 9, 2, C_WHITE)
            tft.fill_rect(fx, fy + 4, 14, 7, rgb(255, 205, 50))

        draw_text(tft, active_tab, tab_x + 22, tb_y + 6, C_WHITE)
        tft.fill_rect(tab_x, tb_y + TB_H - 2, tab_w, 2, rgb(0, 160, 255))

    # 3. Батарейка
    bx, by = 258, tb_y + 7
    tft.rect(bx, by, 12, 7, C_WHITE)
    tft.fill_rect(bx + 12, by + 2, 2, 3, C_WHITE)
    tft.fill_rect(bx + 2, by + 2, 8, 3, C_WHITE)

    # 4. Часы
    clock_str = "%02d:%02d" % (cfg.get("hour", 20), cfg.get("minute", 45))
    tft.text(clock_str, 276, tb_y + 7, C_WHITE)


class RobotOS_GUI:
    def __init__(self, tft, audio, inputs):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs

        # Контекстное меню мыши
        self.ctx_open = False
        self.ctx_x = 0
        self.ctx_y = 0
        self.ctx_target_id = -1

        self.cursor = 4  
        self.start_open = False
        self.start_sel = 0

        self.eye_idx = 0
        self.trash_full = False
        now = time.ticks_ms()
        self.clock_tick = now

        self._wave = {}
        self.cfg = {
            "vol_ui": 30,
            "mute": False,
            "brightness": 100,
            "hour": 22,
            "minute": 52,
            "day": 21,
            "month": 10,
            "year": 2026,
            "desktop_color": C_DESKTOP,
        }

    def _wave_for(self, freq):
        amp = int(1200 * (self.cfg["vol_ui"] / 100))
        key = (freq, amp)
        w = self._wave.get(key)
        if w is None:
            n = max(2, int(22050 / freq))
            w = bytearray(n * 2)
            for i in range(n):
                struct.pack_into("<h", w, i * 2, int(amp * math.sin(2 * math.pi * i / n)))
            if len(self._wave) > 16:
                self._wave.clear()
            self._wave[key] = w
        return w

    def click_sound(self, freq=1200, ms=10):
        if self.cfg["mute"] or self.cfg["vol_ui"] == 0:
            return
        cycle = self._wave_for(freq)
        for _ in range(max(1, int((ms / 1000) * freq))):
            self.audio.write(cycle)

    def launch(self, factory):
        try:
            factory().run()
        except Exception as e:
            try:
                sys.print_exception(e)
            except Exception:
                pass
            self.show_error(e)
        gc.collect()

    def show_error(self, e):
        self.tft.fill(C_DARK)
        self.tft.fill_rect(0, 0, W, 26, rgb(200, 30, 50))
        self.tft.text("SYSTEM ERROR", 15, 9, C_WHITE)
        msg = f"{type(e).__name__}: {e}"
        y = 45
        for i in range(0, min(len(msg), 38 * 6), 38):
            self.tft.text(msg[i:i + 38], 15, y, C_WHITE)
            y += 14
        self.tft.text("Press BACK / ESC / ENTER", 15, H - 22, rgb(0, 240, 255))
        self.tft.show()
        while True:
            ev = self.inputs.get_event()
            if ev in ("BACK", "ESC", "ENTER"):
                break
            time.sleep_ms(20)

    def show_dialog(self, title, lines):
        dw, dh = 206, 104
        dx = (W - dw) // 2
        dy = (H - dh) // 2
        t = self.tft

        t.fill_rect(dx, dy, dw, dh, rgb(235, 238, 245))
        t.rect(dx, dy, dw, dh, rgb(0, 120, 215))

        t.fill_rect(dx + 2, dy + 2, dw - 4, 18, rgb(0, 120, 215))
        draw_text(t, title, dx + 8, dy + 7, C_WHITE)

        yy = dy + 28
        for line in lines:
            draw_text(t, line, dx + 10, yy, C_DARK)
            yy += 14

        t.fill_rect(dx + (dw - 44) // 2, dy + dh - 22, 44, 16, rgb(200, 205, 215))
        t.rect(dx + (dw - 44) // 2, dy + dh - 22, 44, 16, rgb(100, 105, 115))
        t.text("OK", dx + (dw - 44) // 2 + 14, dy + dh - 18, C_DARK)
        t.show()

        self.click_sound(1200, 15)
        while True:
            ev = self.inputs.get_event()
            if ev in ("ENTER", "BACK", "ESC"):
                self.click_sound(900, 15)
                break
            time.sleep_ms(20)

    def update_clock(self, now):
        changed = False
        while time.ticks_diff(now, self.clock_tick) >= 60000:
            self.clock_tick = time.ticks_add(self.clock_tick, 60000)
            m = self.cfg["minute"] + 1
            h = self.cfg["hour"]
            if m >= 60:
                m = 0
                h = (h + 1) % 24
            self.cfg["minute"] = m
            self.cfg["hour"] = h
            changed = True
        return changed

    def draw_round_rect(self, x, y, w, h, r, color):
        self.tft.fill_rect(x, y + r, w, h - 2 * r, color)
        self.tft.fill_rect(x + r, y, w - 2 * r, h, color)
        for dy in range(r):
            y_dist = r - dy
            dx = int(math.sqrt(r * r - y_dist * y_dist))
            line_w = w - 2 * r + 2 * dx
            self.tft.fill_rect(x + r - dx, y + dy, line_w, 1, color)
            self.tft.fill_rect(x + r - dx, y + h - 1 - dy, line_w, 1, color)

    def draw_desktop(self):
        bg = self.cfg.get("desktop_color", C_DESKTOP)
        self.tft.fill(bg)

        for i, icon in enumerate(DESKTOP_ICONS):
            ix, iy = icon["x"], icon["y"]
            title = icon["title"]
            is_sel = (self.cursor == i and not self.start_open)

            text_w = len(title) * 8
            box_w = 26 + text_w + 10

            if is_sel:
                self.tft.fill_rect(ix - 4, iy - 4, box_w, 26, C_SEL_BG)
                self.tft.rect(ix - 4, iy - 4, box_w, 26, C_SEL_BORDER)

            self.draw_icon(icon["id"], ix, iy)
            draw_text(self.tft, title, ix + 26, iy + 5, C_WHITE)

    def draw_icon(self, icon_id, x, y):
        t = self.tft

        if icon_id == 0:  
            t.fill_rect(x, y + 1, 18, 12, rgb(215, 220, 230))
            t.fill_rect(x + 2, y + 3, 14, 8, rgb(0, 120, 215))
            t.fill_rect(x + 3, y + 4, 3, 2, C_WHITE)
            t.fill_rect(x + 7, y + 13, 4, 2, rgb(160, 165, 175))
            t.fill_rect(x + 4, y + 15, 10, 2, rgb(190, 195, 205))
        elif icon_id == 1:  
            t.fill_rect(x + 1, y + 2, 7, 3, rgb(255, 205, 50))
            t.fill_rect(x + 1, y + 4, 18, 12, rgb(230, 170, 20))
            t.fill_rect(x + 3, y + 3, 12, 4, C_WHITE)
            t.fill_rect(x + 1, y + 6, 18, 10, rgb(255, 215, 60))
            t.hline(x + 2, y + 6, 16, rgb(255, 240, 150))
        elif icon_id == 2:
            draw_xbox(t, x, y - 1, 20)
        elif icon_id == 3:  
            t.fill_rect(x + 2, y + 2, 14, 2, rgb(180, 190, 205))
            t.fill_rect(x + 6, y, 6, 2, rgb(150, 160, 175))
            t.fill_rect(x + 4, y + 4, 10, 13, rgb(165, 175, 195))
            t.vline(x + 6, y + 6, 9, rgb(110, 125, 145))
            t.vline(x + 9, y + 6, 9, rgb(110, 125, 145))
            t.vline(x + 12, y + 6, 9, rgb(110, 125, 145))

    def draw_start_button(self):
        bx, by, bw, bh = 0, TB_Y, 26, TB_H
        is_active = (self.cursor == 4 or self.start_open)
        btn_bg = C_START_HOVER if is_active else C_START_IDLE
        self.tft.fill_rect(bx, by, bw, bh, btn_bg)
        eye_col = C_EYE_CYAN if is_active else C_EYE_WHITE

        ew, eh, gap = 5, 9, 3
        total_w = ew * 2 + gap
        ex = bx + (bw - total_w) // 2
        ey = by + (bh - eh) // 2
        self.draw_round_rect(ex, ey, ew, eh, 2, eye_col)
        self.draw_round_rect(ex + ew + gap, ey, ew, eh, 2, eye_col)

    def draw_taskbar(self):
        active = "START" if (self.cursor == 4 or self.start_open) else None
        draw_system_taskbar(self.tft, self.cfg, active_tab=active)
        
        if self.cursor == 5:
            self.tft.fill_rect(273, TB_Y, 47, TB_H, C_START_HOVER)
            clock_str = "%02d:%02d" % (self.cfg.get("hour", 20), self.cfg.get("minute", 45))
            self.tft.text(clock_str, 276, TB_Y + 7, C_EYE_CYAN)

    def draw_start_menu(self):
        if not self.start_open:
            return

        item_h = 18
        n_items = len(START_MENU_ITEMS)
        mw = 114
        mh = n_items * item_h + 8
        mx = 0
        my = TB_Y - mh

        self.tft.fill_rect(mx, my, mw, mh, C_MENU_BG)
        self.tft.rect(mx, my, mw, mh, C_TASKBAR_SEP)

        start_y = my + 4
        for i, (title, _) in enumerate(START_MENU_ITEMS):
            py = start_y + i * item_h
            if i == self.start_sel:
                self.tft.fill_rect(mx + 2, py, mw - 4, item_h, C_START_HOVER)
                draw_text(self.tft, title, mx + 10, py + 5, C_WHITE)
            else:
                draw_text(self.tft, title, mx + 10, py + 5, C_GRAY)

    def draw_context_menu(self):
        """Контекстное меню Windows по правой кнопке мыши"""
        if not self.ctx_open:
            return

        items = ["Открыть", "Копировать", "Вырезать", "Удалить", "Имя", "Свойства"]
        mw, mh = 104, len(items) * 16 + 8
        mx = min(W - mw - 2, max(2, self.ctx_x))
        my = min(TB_Y - mh - 2, max(2, self.ctx_y))

        self.tft.fill_rect(mx, my, mw, mh, rgb(28, 32, 44))
        self.tft.rect(mx, my, mw, mh, rgb(0, 160, 255))

        for i, item in enumerate(items):
            iy = my + 4 + i * 16
            col = C_WHITE if i == 0 else C_GRAY
            draw_text(self.tft, item, mx + 8, iy + 4, col)
            if i in (0, 4):
                self.tft.line(mx + 4, iy + 15, mx + mw - 4, iy + 15, rgb(45, 52, 70))
    
    def render_all(self):
        self.draw_desktop()
        self.draw_taskbar()
        self.draw_start_menu()
        self.draw_context_menu()

        # Стрелочка курсора мыши
        if self.inputs.mouse and self.inputs.mouse.present:
            draw_mouse_cursor(self.tft, self.inputs.mouse.x, self.inputs.mouse.y)
        self.tft.show()

    # ================================================================ подменю (320x240)
    def list_menu(self, title, items, sel, active_tab="Программы", tab_icon="folder"):
        n = len(items)
        back_idx = n - 1
        vis_count = 8
        top = 0
        step = 21

        while True:
            if sel < top: top = sel
            if sel >= top + vis_count: top = sel - vis_count + 1

            self.tft.fill_rect(0, 0, W, 20, rgb(28, 32, 44))
            self.tft.line(0, 19, W, 19, rgb(45, 52, 70))
            draw_text(self.tft, title, 10, 6, C_WHITE)
            self.tft.text("Esc", 294, 6, C_WHITE)

            self.tft.fill_rect(0, 20, W, 174, rgb(18, 20, 26))

            start_y = 24
            for idx in range(top, min(n, top + vis_count)):
                item = items[idx]
                y = start_y + (idx - top) * step
                if idx == sel:
                    self.tft.fill_rect(8, y - 2, W - 16, step - 2, rgb(0, 110, 210))
                    self.tft.rect(8, y - 2, W - 16, step - 2, rgb(0, 180, 255))
                    draw_text(self.tft, "> " + item, 14, y + 2, C_WHITE)
                else:
                    draw_text(self.tft, "  " + item, 14, y + 2, rgb(200, 205, 215))

            self.tft.fill_rect(0, 194, W, 24, rgb(14, 16, 22))
            self.tft.line(0, 194, W, 194, rgb(45, 52, 70))
            draw_text(self.tft, "СТРЕЛКИ:Выбор   ENTER:Пуск   ESC:Назад", 10, 202, rgb(130, 140, 160))

            draw_system_taskbar(self.tft, self.cfg, active_tab=active_tab, tab_icon=tab_icon)
            self.tft.show()

            while True:
                ev = self.inputs.get_event()
                if ev:
                    if ev == 'UP':
                        sel = (sel - 1) % n
                        self.click_sound(850, 15)
                        break
                    elif ev == 'DOWN':
                        sel = (sel + 1) % n
                        self.click_sound(750, 15)
                        break
                    elif ev in BACK_KEYS:
                        self.click_sound(600, 30)
                        return -1
                    elif ev == 'ENTER':
                        self.click_sound(600 if sel == back_idx else 1400, 30)
                        return sel
                time.sleep_ms(20)

    # ================================================================ секции
    def menu_robot(self):
        items = ["1. Демо-режим (Чистый экран)", "2. Тестер мимики (Управление)", "< Назад"]
        sel = 0
        back_idx = len(items) - 1

        while True:
            sel = self.list_menu("Робототехника", items, sel, active_tab="Робот", tab_icon="folder")
            if sel == -1 or sel == back_idx:
                return

            if sel in (0, 1):
                import app_eyes
                mode = "DEMO" if sel == 0 else "MANUAL"
                self.launch(lambda: app_eyes.RobotEyesApp(
                    self.tft, self.audio, self.inputs, self.eye_idx, mode, self.cfg))
                del sys.modules["app_eyes"]
                gc.collect()

    def menu_apps(self):
        sel = 0
        while True:
            lst = apps_reg.menu_entries("app")
            items = ["%d. %s" % (i + 1, e[2]) for i, e in enumerate(lst)] + ["< BACK"]
            sel = self.list_menu("Приложения", items, min(sel, len(items) - 1),
                                 active_tab="Программы", tab_icon="folder")
            if sel == -1 or sel == len(lst):
                return
            apps_reg.launch(self, lst[sel])

    def menu_games(self):
        import app_games
        self.launch(lambda: app_games.GamesApp(self.tft, self.audio, self.inputs, self.cfg))
        del sys.modules["app_games"]
        gc.collect()

    def open_section(self, idx):
        self.click_sound(1500, 25)
        self.start_open = False

        if idx == 0:
            self.menu_robot()
        elif idx == 1:
            self.menu_apps()
        elif idx == 2:
            self.menu_games()
        elif idx == 3:
            import app_player
            self.launch(lambda: app_player.MusicPlayerApp(self.tft, self.audio, self.inputs, self.cfg))
            del sys.modules["app_player"]
        elif idx == 4:
            import app_files
            self.launch(lambda: app_files.FileManagerApp(self.tft, self.audio, self.inputs, self.cfg))
            del sys.modules["app_files"]
        elif idx == 5:
            import app_settings
            self.launch(lambda: app_settings.SettingsApp(self.tft, self.audio, self.inputs, self.cfg))
            del sys.modules["app_settings"]
            self.clock_tick = time.ticks_ms()
        elif idx == 6:
            import app_sleep
            self.launch(lambda: app_sleep.SleepApp(self.tft, self.audio, self.inputs, self.cfg, None))
            del sys.modules["app_sleep"]
        elif idx == 7:
            import app_cmd
            self.launch(lambda: app_cmd.CmdApp(self.tft, self.audio, self.inputs, self.cfg))
            del sys.modules["app_cmd"]

        gc.collect()
        now = time.ticks_ms()
        self.update_clock(now)
        self.render_all()
    
    def draw_bg_quiet(self):
        """Отрисовка стола и панели в буфер без мерцания"""
        self.draw_desktop()
        self.draw_taskbar()
    
    # ================================================================ главный цикл
    def run(self):
        self.render_all()
        now = time.ticks_ms()
        self.clock_tick = now

        while True:
            # 1. Плиточный режим Metro (если включен)
            if self.cfg.get("desktop_mode", "classic") == "metro":
                import app_metro
                metro = app_metro.MetroDesktop(self)
                metro.run_loop()
                del sys.modules["app_metro"]
                gc.collect()
                self.render_all()
                continue

            old_cursor = self.cursor
            old_start_sel = self.start_sel

            # 2. ДВИЖЕНИЕ МЫШКИ И ПОДСВЕТКА (HOVER)
            if self.inputs.mouse and self.inputs.mouse.present:
                mouse_moved = self.inputs.mouse.update()
                mx, my = self.inputs.mouse.x, self.inputs.mouse.y

                # Если контекстное меню НЕ открыто — обновляем подсветку под курсором:
                if not self.ctx_open:
                    # А. Наведение на панели задач
                    if my >= TB_Y:
                        if 0 <= mx <= 26:
                            self.cursor = 4  # Подсветка кнопки Пуск
                        elif 270 <= mx <= 320:
                            self.cursor = 5  # Подсветка Часов
                    # Б. Наведение на иконки стола (если меню Пуск закрыто)
                    elif not self.start_open:
                        for i, icon in enumerate(DESKTOP_ICONS):
                            ix, iy = icon["x"], icon["y"]
                            box_w = 26 + len(icon["title"]) * 8 + 10
                            if ix - 4 <= mx <= ix + box_w and iy - 4 <= my <= iy + 26:
                                self.cursor = i
                                break
                    # В. Наведение на пункты меню Пуск (если меню открыто)
                    elif self.start_open:
                        item_h = 18
                        mh = len(START_MENU_ITEMS) * item_h + 8
                        sm_y = TB_Y - mh
                        if 0 <= mx <= 114 and sm_y <= my <= TB_Y:
                            hover_idx = (my - (sm_y + 4)) // item_h
                            if 0 <= hover_idx < len(START_MENU_ITEMS):
                                self.start_sel = hover_idx

                # Перерисовываем экран только если мышь сдвинулась или сменился выбор
                if mouse_moved or old_cursor != self.cursor or old_start_sel != self.start_sel:
                    self.render_all()

            now = time.ticks_ms()

            # 3. Часы
            if self.update_clock(now):
                self.draw_taskbar()
                self.tft.show()

            # 4. Обработка событий и кликов
            ev = self.inputs.get_event()
            if ev:
                old_cur = self.cursor
                old_open = self.start_open

                # ================= ПРАВАЯ КНОПКА МЫШИ (КОНТЕКСТНОЕ МЕНЮ) =================
                if ev == 'MOUSE_RCLICK' and self.inputs.mouse:
                    mx, my = self.inputs.mouse.x, self.inputs.mouse.y
                    self.ctx_x = mx
                    self.ctx_y = my
                    self.ctx_target_id = -1

                    # Проверяем, кликнули ли по иконке стола
                    for i, icon in enumerate(DESKTOP_ICONS):
                        ix, iy = icon["x"], icon["y"]
                        box_w = 26 + len(icon["title"]) * 8 + 10
                        if ix - 4 <= mx <= ix + box_w and iy - 4 <= my <= iy + 26:
                            self.ctx_target_id = i
                            self.cursor = i
                            break

                    self.ctx_open = True
                    self.click_sound(1200, 15)
                    self.render_all()
                    continue

                # ================= ЕСЛИ ОТКРЫТО КОНТЕКСТНОЕ МЕНЮ =================
                if self.ctx_open:
                    mx, my = (self.inputs.mouse.x, self.inputs.mouse.y) if self.inputs.mouse else (0, 0)
                    mw, mh = 104, 6 * 16 + 8
                    cm_x = min(W - mw - 2, max(2, self.ctx_x))
                    cm_y = min(TB_Y - mh - 2, max(2, self.ctx_y))

                    # Закрытие по ESC или повторному правому клику
                    if ev in BACK_KEYS or ev == 'MOUSE_RCLICK':
                        self.ctx_open = False
                        self.render_all()
                        continue

                    # Клик левой кнопки мыши:
                    elif ev in ('ENTER', 'MOUSE_LCLICK'):
                        # 1. Проверяем: кликнули ВНЕ меню -> ЗАКРЫВАЕМ МЕНЮ!
                        if not (cm_x <= mx <= cm_x + mw and cm_y <= my <= cm_y + mh):
                            self.ctx_open = False
                            self.render_all()
                            continue

                        # 2. Кликнули ВНУТРИ меню по пункту:
                        clicked_row = (my - (cm_y + 4)) // 16
                        self.ctx_open = False
                        self.render_all()

                        if clicked_row == 0: # "Открыть"
                            if self.ctx_target_id != -1:
                                if self.ctx_target_id == 0:
                                    import app_htop
                                    self.launch(lambda: app_htop.HtopApp(self.tft, self.audio, self.inputs, self.cfg))
                                    del sys.modules["app_htop"]
                                    self.render_all()
                                elif self.ctx_target_id in (1, 2):
                                    self.open_section(4 if self.ctx_target_id == 1 else 2)
                                elif self.ctx_target_id == 3:
                                    self.show_dialog("Корзина", ["Статус: Пусто", "Файлов нет."])
                        elif clicked_row == 5: # "Свойства"
                            self.show_dialog("Свойства системы", [
                                "RobotOS v2.0 (DVI Edition)",
                                "Платформа: RP2350 150MHz",
                                "Видео: 320x240 @ 60Hz",
                                "Память: 520KB SRAM",
                            ])
                        continue

                # ================= ЛЕВЫЙ КЛИК МЫШИ =================
                if ev == 'MOUSE_LCLICK' and self.inputs.mouse:
                    mx, my = self.inputs.mouse.x, self.inputs.mouse.y

                    # 1. Клик по кнопке Пуск (слева внизу)
                    if 0 <= mx <= 26 and TB_Y <= my <= H:
                        self.start_open = not self.start_open
                        self.start_sel = 0
                        self.click_sound(1200, 20)
                        self.render_all()
                        continue

                    # 2. Клик по часам (справа внизу)
                    elif 270 <= mx <= 320 and TB_Y <= my <= H:
                        import app_calendar
                        self.launch(lambda: app_calendar.CalendarApp(
                            self.tft, self.audio, self.inputs, self.cfg, bg_drawer=self.draw_bg_quiet))
                        del sys.modules["app_calendar"]
                        gc.collect()
                        self.render_all()
                        continue

                    # 3. Клик по пунктам меню Пуск (если оно открыто)
                    if self.start_open:
                        item_h = 18
                        mh = len(START_MENU_ITEMS) * item_h + 8
                        sm_y = TB_Y - mh
                        if 0 <= mx <= 114 and sm_y <= my <= TB_Y:
                            clicked_idx = (my - (sm_y + 4)) // item_h
                            if 0 <= clicked_idx < len(START_MENU_ITEMS):
                                target = START_MENU_ITEMS[clicked_idx][1]
                                self.start_open = False
                                self.open_section(target)
                                continue
                        else:
                            # Клик вне меню Пуск закрывает его!
                            self.start_open = False
                            self.render_all()
                            continue

                    # 4. Клик по иконкам на рабочем столе
                    for i, icon in enumerate(DESKTOP_ICONS):
                        ix, iy = icon["x"], icon["y"]
                        box_w = 26 + len(icon["title"]) * 8 + 10
                        if ix - 4 <= mx <= ix + box_w and iy - 4 <= my <= iy + 26:
                            self.cursor = i
                            if i == 0:
                                import app_htop
                                self.launch(lambda: app_htop.HtopApp(self.tft, self.audio, self.inputs, self.cfg))
                                del sys.modules["app_htop"]
                                self.render_all()
                            elif i == 1: self.open_section(4)
                            elif i == 2: self.open_section(2)
                            elif i == 3: self.show_dialog("Корзина", ["Статус: Пусто", "Файлов нет."])
                            break

                # --- 5. Меню Пуск открыто с клавиатуры ---
                if self.start_open:
                    if ev == 'UP':
                        self.start_sel = (self.start_sel - 1) % len(START_MENU_ITEMS)
                        self.click_sound(900, 10)
                        self.render_all()
                    elif ev == 'DOWN':
                        self.start_sel = (self.start_sel + 1) % len(START_MENU_ITEMS)
                        self.click_sound(800, 10)
                        self.render_all()
                    elif ev in BACK_KEYS:
                        self.start_open = False
                        self.click_sound(600, 15)
                        self.render_all()
                    elif ev == 'ENTER':
                        target = START_MENU_ITEMS[self.start_sel][1]
                        self.open_section(target)
                    continue

                # --- 6. Навигация клавиатурой по рабочему столу ---
                if ev == 'UP':
                    if self.cursor in (4, 5):
                        self.cursor = 3
                    else:
                        self.cursor = (self.cursor - 1) % 4
                    self.click_sound(850, 10)

                elif ev == 'DOWN':
                    if self.cursor == 3:
                        self.cursor = 4
                    elif self.cursor in (4, 5):
                        self.cursor = 0
                    else:
                        self.cursor += 1
                    self.click_sound(750, 10)

                elif ev == 'LEFT':
                    if self.cursor == 5:
                        self.cursor = 4
                        self.click_sound(950, 10)
                    elif self.cursor != 4:
                        self.cursor = 4
                        self.click_sound(950, 10)

                elif ev == 'RIGHT':
                    if self.cursor == 4:
                        self.cursor = 5
                        self.click_sound(950, 10)

                elif ev == 'ENTER':
                    if self.cursor == 5:
                        import app_calendar
                        self.launch(lambda: app_calendar.CalendarApp(
                            self.tft, self.audio, self.inputs, self.cfg, bg_drawer=self.draw_bg_quiet))
                        del sys.modules["app_calendar"]
                        gc.collect()
                        self.render_all()
                        continue
                    elif self.cursor == 4:
                        self.start_open = True
                        self.start_sel = 0
                        self.click_sound(1200, 20)
                    elif self.cursor == 0:
                        import app_htop
                        self.launch(lambda: app_htop.HtopApp(self.tft, self.audio, self.inputs, self.cfg))
                        del sys.modules["app_htop"]
                        gc.collect()
                        self.render_all()
                    elif self.cursor == 1:
                        self.open_section(4)
                        continue
                    elif self.cursor == 2:
                        self.open_section(2)
                        continue
                    elif self.cursor == 3:
                        self.show_dialog("Корзина", ["Статус: Пусто", "Удалённых файлов нет.", "", "Диск в порядке."])
                        self.render_all()

                elif ev in BACK_KEYS:
                    self.start_open = not self.start_open
                    self.start_sel = 0
                    self.click_sound(1000, 15)

                if old_cur != self.cursor or old_open != self.start_open:
                    self.render_all()

            time.sleep_ms(20)