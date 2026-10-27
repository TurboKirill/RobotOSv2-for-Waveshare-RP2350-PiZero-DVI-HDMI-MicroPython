# app_settings.py - Параметры RobotOS (DVI 320x240)
# Стиль "Параметры Windows 10": 100% русский текст, иконка-шестерёнка, валидация дат
import os
import time
import math
import struct
import gc
import sys
from machine import RTC
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240
TB_H = 22
WIN_H = H - TB_H  # 218px

# Палитра Windows Параметры
C_BG        = rgb(24, 26, 32)       # Тёмно-серый фон
C_HEADER    = rgb(30, 34, 44)       # Шапка окна
C_CARD      = rgb(32, 36, 48)       # Карточка
C_CARD_HOV  = rgb(46, 54, 74)       # Подсветка карточки
C_BORDER    = rgb(50, 56, 72)       # Рамка
C_ACCENT    = rgb(0, 160, 255)      # Синий Windows 10
C_WHITE     = 0xFFFF
C_GRAY      = rgb(140, 150, 170)
C_DARK_GRAY = rgb(95, 105, 125)
C_GREEN     = rgb(0, 230, 120)
C_RED       = rgb(255, 75, 75)
C_YELLOW    = rgb(255, 215, 0)

MAIN_CATEGORIES = [
    ("Система",         "Экран, ОЗУ, процессор, htop",       "sys"),
    ("Звук",            "Громкость, переключатель Mute",     "snd"),
    ("Устройства",      "Дисплей, клавиатура, I2S, SD",     "dev"),
    ("Персонализация",  "Фон, тема, оформление окон",        "pers"),
    ("Приложения",      "Список программ, удаление/устан.",  "apps"),
    ("Время и язык",    "Часы, дата календаря, регион",      "time"),
    ("Игры",            "Каталог ретро-игр RobotOS",         "games"),
]

def days_in_month(month, year):
    """Вычисление точного количества дней в месяце с учётом високосных лет"""
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    elif month in (4, 6, 9, 11):
        return 30
    elif month == 2:
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            return 29
        return 28
    return 30


class SettingsApp:
    def __init__(self, tft, audio, inputs, config):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config
        self.rtc = RTC()

        self.main_sel = 0
        self.sub_sel = 0

        # Начальная инициализация даты
        if "day" not in self.cfg:
            self.cfg["day"] = 14
            self.cfg["month"] = 3
            self.cfg["year"] = 2026

        self.apply_rtc()

    def apply_rtc(self):
        try:
            self.rtc.datetime((
                self.cfg.get("year", 2026),
                self.cfg.get("month", 3),
                self.cfg.get("day", 14),
                1,
                self.cfg.get("hour", 20),
                self.cfg.get("minute", 45),
                0, 0
            ))
        except:
            pass

    def beep(self, freq=1100, ms=10):
        if self.cfg.get("mute") or self.cfg.get("vol_ui", 30) == 0:
            return
        rate = 22050
        samples = max(2, int(rate / freq))
        cycle = bytearray(samples * 2)
        amp = int(900 * (self.cfg.get("vol_ui", 30) / 100))
        for i in range(samples):
            v = int(amp * math.sin(2 * math.pi * i / samples))
            struct.pack_into("<h", cycle, i * 2, v)
        for _ in range(max(1, int((ms / 1000) * freq))):
            self.audio.write(cycle)

    def _sd_present(self):
        try:
            os.stat("/sd")
            return True
        except:
            return False

    def show_dialog(self, title, lines):
        dw, dh = 240, 96
        dx = (W - dw) // 2
        dy = (WIN_H - dh) // 2
        t = self.tft

        t.fill_rect(dx, dy, dw, dh, rgb(28, 32, 44))
        t.rect(dx, dy, dw, dh, C_ACCENT)
        t.fill_rect(dx + 2, dy + 2, dw - 4, 18, rgb(38, 44, 60))
        draw_text(t, title, dx + 8, dy + 6, C_WHITE)

        yy = dy + 28
        for line in lines:
            draw_text(t, line[:28], dx + 12, yy, C_WHITE)
            yy += 15

        t.fill_rect(dx + (dw - 50) // 2, dy + dh - 22, 50, 16, C_ACCENT)
        t.text("OK", dx + (dw - 50) // 2 + 18, dy + dh - 18, C_WHITE)
        t.show()

        self.beep(1200, 15)
        while True:
            ev = self.inputs.get_event()
            if ev in ("ENTER", "BACK", "ESC", " "):
                self.beep(900, 15)
                break
            time.sleep_ms(20)

    # ------------------------------------------------------------ Иконки категорий
    def draw_category_icon(self, icon_type, x, y):
        t = self.tft
        if icon_type == "sys":
            t.fill_rect(x, y + 1, 16, 10, rgb(180, 195, 215))
            t.fill_rect(x + 2, y + 3, 12, 6, C_ACCENT)
            t.fill_rect(x + 6, y + 11, 4, 2, C_GRAY)
            t.fill_rect(x + 4, y + 13, 8, 2, rgb(180, 195, 215))
        elif icon_type == "snd":
            t.fill_rect(x + 1, y + 4, 4, 6, C_YELLOW)
            t.fill_rect(x + 5, y + 2, 4, 10, C_YELLOW)
            t.fill_rect(x + 11, y + 3, 2, 8, C_WHITE)
            t.fill_rect(x + 14, y + 1, 2, 12, C_WHITE)
        elif icon_type == "dev":
            t.fill_rect(x + 1, y + 2, 14, 10, rgb(0, 200, 180))
            t.rect(x + 1, y + 2, 14, 10, C_WHITE)
            t.fill_rect(x + 4, y + 5, 2, 2, C_WHITE)
            t.fill_rect(x + 7, y + 5, 2, 2, C_WHITE)
            t.fill_rect(x + 10, y + 5, 2, 2, C_WHITE)
            t.fill_rect(x + 5, y + 8, 6, 2, C_WHITE)
        elif icon_type == "pers":
            t.fill_rect(x + 2, y + 1, 12, 12, rgb(255, 110, 180))
            t.fill_rect(x + 4, y + 3, 3, 3, C_YELLOW)
            t.fill_rect(x + 9, y + 3, 3, 3, C_ACCENT)
            t.fill_rect(x + 4, y + 8, 3, 3, C_GREEN)
        elif icon_type == "apps":
            t.fill_rect(x + 1, y + 1, 6, 6, C_ACCENT)
            t.fill_rect(x + 9, y + 1, 6, 6, C_GREEN)
            t.fill_rect(x + 1, y + 9, 6, 6, C_YELLOW)
            t.fill_rect(x + 9, y + 9, 6, 6, rgb(255, 90, 90))
        elif icon_type == "time":
            t.fill_rect(x + 2, y + 1, 12, 12, C_GRAY)
            t.fill_rect(x + 3, y + 2, 10, 10, C_HEADER)
            t.fill_rect(x + 7, y + 4, 2, 4, C_YELLOW)
            t.fill_rect(x + 7, y + 7, 4, 2, C_YELLOW)
        elif icon_type == "games":
            t.fill_rect(x + 1, y + 3, 14, 8, rgb(16, 124, 65))
            t.fill_rect(x + 3, y + 5, 4, 4, C_WHITE)
            t.fill_rect(x + 10, y + 5, 2, 2, C_YELLOW)
            t.fill_rect(x + 12, y + 7, 2, 2, C_RED)

    # ------------------------------------------------------------ Главное меню (Без поиска!)
    def draw_main_menu(self):
        t = self.tft
        t.fill_rect(0, 0, W, 20, C_HEADER)
        t.line(0, 19, W, 19, C_BORDER)
        draw_text(t, "Параметры", 10, 6, C_WHITE)
        t.text("Esc", 294, 6, C_WHITE)

        t.fill_rect(0, 20, W, 198, C_BG)

        # Все 7 категорий на одном экране
        y = 24
        card_h = 24
        for i, (title, desc, icon_key) in enumerate(MAIN_CATEGORIES):
            is_sel = (i == self.main_sel)

            bg = C_CARD_HOV if is_sel else C_CARD
            t.fill_rect(10, y, 300, card_h, bg)
            t.rect(10, y, 300, card_h, C_ACCENT if is_sel else C_BORDER)

            self.draw_category_icon(icon_key, 16, y + 4)
            draw_text(t, title, 36, y + 4, C_WHITE if is_sel else rgb(220, 225, 235))
            draw_text(t, desc[:32], 36, y + 13, C_ACCENT if is_sel else C_DARK_GRAY)

            t.text(">", 296, y + 7, C_ACCENT if is_sel else C_DARK_GRAY)
            y += card_h + 1

        draw_text(t, "ENTER: Выбрать    ВВЕРХ/ВНИЗ: Навигация", 12, 202, C_DARK_GRAY)
        draw_system_taskbar(t, self.cfg, active_tab="Параметры", tab_icon="settings")
        t.show()

    def draw_sub_header(self, title):
        t = self.tft
        t.fill_rect(0, 0, W, 20, C_HEADER)
        t.line(0, 19, W, 19, C_BORDER)
        draw_text(t, f"< {title}", 8, 6, C_WHITE)
        t.text("Esc", 294, 6, C_WHITE)
        t.fill_rect(0, 20, W, 198, C_BG)

    # ------------------------------------------------------------ Подраздел: Звук
    def view_sound(self):
        items = ["Громкость UI", "Без звука", "Тест I2S"]
        self.sub_sel = 0

        while True:
            self.draw_sub_header("Звук")
            t = self.tft

            draw_text(t, "Настройки громкости и оповещений", 12, 26, C_GRAY)

            # Карточка 1: Громкость
            is_0 = (self.sub_sel == 0)
            t.fill_rect(12, 44, 296, 44, C_CARD_HOV if is_0 else C_CARD)
            t.rect(12, 44, 296, 44, C_ACCENT if is_0 else C_BORDER)
            draw_text(t, "Громкость интерфейса", 20, 50, C_WHITE)
            t.text(f"{self.cfg['vol_ui']}%", 260, 50, C_ACCENT if is_0 else C_WHITE)

            t.rect(20, 68, 260, 8, C_BORDER)
            w_fill = int(256 * (self.cfg["vol_ui"] / 100))
            if w_fill > 0:
                t.fill_rect(22, 70, w_fill, 4, C_ACCENT)

            # Карточка 2: Mute
            is_1 = (self.sub_sel == 1)
            t.fill_rect(12, 94, 296, 36, C_CARD_HOV if is_1 else C_CARD)
            t.rect(12, 94, 296, 36, C_ACCENT if is_1 else C_BORDER)
            draw_text(t, "Режим 'Без звука'", 20, 104, C_WHITE)
            m_txt = "[ ВКЛЮЧЕН ]" if self.cfg["mute"] else "[ ВЫКЛЮЧЕН ]"
            m_col = C_RED if self.cfg["mute"] else C_GREEN
            draw_text(t, m_txt, 190, 104, m_col)

            # Карточка 3: Тест звука
            is_2 = (self.sub_sel == 2)
            t.fill_rect(12, 136, 296, 34, C_CARD_HOV if is_2 else C_CARD)
            t.rect(12, 136, 296, 34, C_ACCENT if is_2 else C_BORDER)
            draw_text(t, "Воспроизвести сигнал теста", 20, 146, C_WHITE)

            # Аккуратная короткая подсказка, которая точно помещается
            draw_text(t, "ВЛЕВО/ВПРАВО: Звук   ENTER: Выбор", 12, 202, C_DARK_GRAY)
            draw_system_taskbar(t, self.cfg, active_tab="Параметры", tab_icon="settings")
            t.show()

            ev = self.inputs.get_event()
            if not ev:
                time.sleep_ms(20)
                continue

            if ev in ('ESC', 'BACK'):
                self.beep(800, 10)
                return
            elif ev == 'UP':
                self.sub_sel = (self.sub_sel - 1) % len(items)
                self.beep(850, 8)
            elif ev == 'DOWN':
                self.sub_sel = (self.sub_sel + 1) % len(items)
                self.beep(750, 8)
            elif ev in ('LEFT', 'RIGHT'):
                step = 5 if ev == 'RIGHT' else -5
                if self.sub_sel == 0:
                    self.cfg["vol_ui"] = max(0, min(100, self.cfg["vol_ui"] + step))
                    self.beep(1200, 15)
                elif self.sub_sel == 1:
                    self.cfg["mute"] = not self.cfg["mute"]
                    self.beep(1000, 15)
            elif ev == 'ENTER':
                if self.sub_sel == 1:
                    self.cfg["mute"] = not self.cfg["mute"]
                    self.beep(1000, 15)
                elif self.sub_sel == 2:
                    for f in [523, 659, 784, 1046]:
                        self.beep(f, 35)
                        time.sleep_ms(20)

    # ------------------------------------------------------------ Подраздел: Устройства (Без ИК, без наложений)
    def view_devices(self):
        sd_ok = self._sd_present()
        devices = [
            ("Экран DVI/HDMI",    "PIO2 DVI 320x240@60Hz",   True,  "АКТИВЕН"),
            ("Клавиатура PS/2",   "GPIO 14, 15 (CLK/DAT)",   True,  "АКТИВНА"),
            ("Аудио MAX98357A",   "GPIO 10, 11, 12 (I2S)",   True,  "АКТИВЕН"),
            ("MicroSD карта",     "SPI1 (GPIO 30..43)",       sd_ok, "ПОДКЛЮЧЕНА" if sd_ok else "НЕ НАЙДЕНА"),
            ("Мышь USB/PS2",      "Порт свободен",           False, "ОТКЛЮЧЕНА"),
        ]

        while True:
            self.draw_sub_header("Устройства")
            t = self.tft

            draw_text(t, "Оборудование и подключенные модули", 12, 26, C_GRAY)

            y = 44
            for name, desc, is_active, status_text in devices:
                t.fill_rect(12, y, 296, 28, C_CARD)
                t.rect(12, y, 296, 28, C_BORDER)

                # Зеленый / серый индикатор
                col = C_GREEN if is_active else C_DARK_GRAY
                t.fill_rect(18, y + 6, 6, 16, col)

                # Текст названия и пинов строго через draw_text
                draw_text(t, name, 30, y + 4, C_WHITE if is_active else C_GRAY)
                draw_text(t, desc, 30, y + 16, C_DARK_GRAY)

                # Статус справа
                status_col = C_GREEN if is_active else (C_RED if "НЕ" in status_text else C_DARK_GRAY)
                draw_text(t, status_text, 204, y + 10, status_col)
                y += 31

            draw_text(t, "ESC: Назад в меню параметров", 12, 202, C_DARK_GRAY)
            draw_system_taskbar(t, self.cfg, active_tab="Параметры", tab_icon="settings")
            t.show()

            ev = self.inputs.get_event()
            if ev in ('ESC', 'BACK', 'ENTER'):
                self.beep(800, 10)
                return
            time.sleep_ms(20)

# ------------------------------------------------------------ Подраздел: Персонализация
    def view_personalization(self):
        colors = [
            ("Стальной синий", rgb(58, 110, 165)),  # Windows 2000
            ("Морская волна",  rgb(0, 128, 128)),   # Classic Windows Teal
            ("Темный графит",  rgb(24, 28, 36)),    # Строгий тёмный
            ("Глубокий синий", rgb(18, 32, 65)),    # Ночной океан
            ("Изумрудный",     rgb(16, 75, 45)),    # Тёмно-зелёный
            ("Бордовый",       rgb(75, 20, 35)),    # Винный
            ("Чистый черный",  0x0000),             # OLED Black
        ]

        modes = [("Классический", "classic"), ("Плитки Win10", "metro")]
        
        cur_mode = self.cfg.get("desktop_mode", "classic")
        m_idx = 1 if cur_mode == "metro" else 0

        cur_c = self.cfg.get("desktop_color", colors[0][1])
        c_idx = 0
        for i, (_, val) in enumerate(colors):
            if val == cur_c: c_idx = i; break

        row_sel = 0 # 0: Режим стола, 1: Цвет стола

        while True:
            self.draw_sub_header("Персонализация")
            t = self.tft

            draw_text(t, "Оформление и режим рабочего стола", 12, 24, C_GRAY)

            name_c, col_val = colors[c_idx]
            mode_name, mode_val = modes[m_idx]

            # 1. Живое превью
            px, py, pw, ph = 12, 44, 110, 72
            if mode_val == "metro":
                # Превью плиток
                t.fill_rect(px, py, pw, ph, rgb(12, 14, 20))
                t.fill_rect(px + 4, py + 4, 50, 28, rgb(0, 120, 215)) # Wide robot tile
                t.fill_rect(px + 58, py + 4, 22, 28, rgb(16, 124, 65))
                t.fill_rect(px + 84, py + 4, 22, 28, rgb(0, 140, 240))
                t.fill_rect(px + 4, py + 36, 22, 28, rgb(215, 60, 40))
                t.fill_rect(px + 30, py + 36, 24, 28, rgb(230, 140, 0))
                t.fill_rect(px + 58, py + 36, 22, 28, rgb(0, 175, 120))
                t.fill_rect(px + 84, py + 36, 22, 28, rgb(240, 110, 20))
            else:
                # Превью классического стола
                t.fill_rect(px, py, pw, ph, col_val)
                t.fill_rect(px + 6, py + 8, 8, 6, C_WHITE)
                t.fill_rect(px + 6, py + 20, 8, 6, rgb(255, 205, 50))

            t.rect(px, py, pw, ph, C_ACCENT)
            # Панель в превью
            t.fill_rect(px, py + ph - 8, pw, 8, rgb(26, 28, 34))
            t.fill_rect(px + 2, py + ph - 6, 6, 4, C_ACCENT)

            # 2. Опции справа
            # Строка 0: Режим стола
            y = 44
            is_0 = (row_sel == 0)
            t.fill_rect(128, y, 180, 36, C_CARD_HOV if is_0 else C_CARD)
            t.rect(128, y, 180, 36, C_ACCENT if is_0 else C_BORDER)
            draw_text(t, "Режим стола:", 134, y + 4, C_WHITE)
            draw_text(t, f"< {mode_name} >", 134, y + 20, C_ACCENT)

            # Строка 1: Цвет фона (активен для классического)
            y = 86
            is_1 = (row_sel == 1)
            t.fill_rect(128, y, 180, 36, C_CARD_HOV if is_1 else C_CARD)
            t.rect(128, y, 180, 36, C_ACCENT if is_1 else C_BORDER)
            draw_text(t, "Цвет фона:", 134, y + 4, C_WHITE)
            draw_text(t, f"< {name_c} >", 134, y + 20, col_val if col_val != 0 else C_WHITE)

            # Инфо
            y = 130
            t.fill_rect(12, y, 296, 26, C_CARD)
            t.rect(12, y, 296, 26, C_BORDER)
            draw_text(t, "Стиль системы: Windows 10/11 [OK]", 20, y + 6, C_GREEN)

            draw_text(t, "ВВЕРХ/ВНИЗ: Строка   ВЛЕВО/ВПРАВО: Выбор   ESC", 10, 202, C_DARK_GRAY)
            draw_system_taskbar(t, self.cfg, active_tab="Параметры", tab_icon="settings")
            t.show()

            ev = self.inputs.get_event()
            if not ev:
                time.sleep_ms(20)
                continue

            if ev in ('ESC', 'BACK'):
                self.beep(800, 10)
                return

            elif ev in ('UP', 'DOWN'):
                row_sel = 1 - row_sel
                self.beep(850, 8)

            elif ev in ('LEFT', 'RIGHT'):
                step = 1 if ev == 'RIGHT' else -1
                if row_sel == 0:
                    # Переключение режима стола
                    m_idx = 1 - m_idx
                    self.cfg["desktop_mode"] = modes[m_idx][1]
                    self.beep(1100, 12)
                elif row_sel == 1:
                    # Переключение цвета фона
                    c_idx = (c_idx + step) % len(colors)
                    self.cfg["desktop_color"] = colors[c_idx][1]
                    self.beep(1100, 12)

    # ------------------------------------------------------------ Подраздел: Приложения / Игры
    def open_uninstaller(self, games=False):
        try:
            import app_uninstaller
            app_uninstaller.UninstallerApp(self.tft, self.audio, self.inputs, self.cfg, games).run()
        except Exception as e:
            self.show_dialog("Ошибка", ["Не удалось открыть:", str(e)[:24]])
        finally:
            sys.modules.pop("app_uninstaller", None)
            gc.collect()

    # ------------------------------------------------------------ Подраздел: Время и язык
    def view_time_and_language(self):
        fields = ["hour", "minute", "day", "month", "year", "lang"]
        field_names = ["Часы", "Минуты", "День", "Месяц", "Год", "Язык системы"]
        sel = 0

        while True:
            self.draw_sub_header("Время и язык")
            t = self.tft

            draw_text(t, "Дата, системное время и локализация", 12, 26, C_GRAY)

            # Карточка часов
            t.fill_rect(12, 42, 296, 40, C_CARD)
            t.rect(12, 42, 296, 40, C_BORDER)
            time_str = "%02d : %02d" % (self.cfg["hour"], self.cfg["minute"])
            date_str = "%02d.%02d.%04d" % (self.cfg["day"], self.cfg["month"], self.cfg.get("year", 2026))

            draw_text(t, f"Текущее время:  {time_str}", 24, 48, C_WHITE)
            draw_text(t, f"Текущая дата:   {date_str}", 24, 64, C_ACCENT)

            y = 88
            for i in range(len(fields)):
                is_cur = (i == sel)
                t.fill_rect(12, y, 296, 17, C_CARD_HOV if is_cur else C_CARD)
                t.rect(12, y, 296, 17, C_ACCENT if is_cur else C_BORDER)

                draw_text(t, field_names[i], 20, y + 3, C_WHITE if is_cur else C_GRAY)

                val_str = ""
                f_key = fields[i]
                if f_key == "hour": val_str = f"< {self.cfg['hour']:02d} ч >"
                elif f_key == "minute": val_str = f"< {self.cfg['minute']:02d} мин >"
                elif f_key == "day": val_str = f"< {self.cfg['day']:02d} >"
                elif f_key == "month": val_str = f"< {self.cfg['month']:02d} >"
                elif f_key == "year": val_str = f"< {self.cfg.get('year', 2026)} >"
                elif f_key == "lang": val_str = "< Русский (RU) >"

                draw_text(t, val_str, 170, y + 3, C_ACCENT if is_cur else C_WHITE)
                y += 18

            draw_text(t, "ВЛЕВО/ВПРАВО: Изменить   ESC: Сохранить", 12, 202, C_DARK_GRAY)
            draw_system_taskbar(t, self.cfg, active_tab="Параметры", tab_icon="settings")
            t.show()

            ev = self.inputs.get_event()
            if not ev:
                time.sleep_ms(20)
                continue

            if ev in ('ESC', 'BACK'):
                self.apply_rtc()
                self.beep(800, 10)
                return
            elif ev == 'UP':
                sel = (sel - 1) % len(fields)
                self.beep(850, 8)
            elif ev == 'DOWN':
                sel = (sel + 1) % len(fields)
                self.beep(750, 8)
            elif ev in ('LEFT', 'RIGHT'):
                step = 1 if ev == 'RIGHT' else -1
                f_key = fields[sel]
                yr = self.cfg.get("year", 2026)

                if f_key == "hour":
                    self.cfg["hour"] = (self.cfg["hour"] + step) % 24
                elif f_key == "minute":
                    self.cfg["minute"] = (self.cfg["minute"] + step) % 60
                elif f_key == "month":
                    self.cfg["month"] = max(1, min(12, self.cfg["month"] + step))
                    # Ограничиваем день при смене месяца (например, с 31 января на февраль)
                    max_d = days_in_month(self.cfg["month"], yr)
                    self.cfg["day"] = min(self.cfg["day"], max_d)
                elif f_key == "year":
                    self.cfg["year"] = max(2025, min(2035, yr + step))
                    max_d = days_in_month(self.cfg["month"], self.cfg["year"])
                    self.cfg["day"] = min(self.cfg["day"], max_d)
                elif f_key == "day":
                    max_d = days_in_month(self.cfg["month"], yr)
                    cur_d = self.cfg["day"] + step
                    if cur_d > max_d: cur_d = 1
                    elif cur_d < 1: cur_d = max_d
                    self.cfg["day"] = cur_d

                self.apply_rtc()
                self.beep(1000, 10)

    # ------------------------------------------------------------ Главный цикл
    def run(self):
        while True:
            self.draw_main_menu()

            ev = self.inputs.get_event()
            if not ev:
                time.sleep_ms(20)
                continue

            if ev in ('ESC', 'BACK'):
                self.beep(600, 20)
                return

            elif ev == 'UP':
                self.main_sel = (self.main_sel - 1) % len(MAIN_CATEGORIES)
                self.beep(850, 8)

            elif ev == 'DOWN':
                self.main_sel = (self.main_sel + 1) % len(MAIN_CATEGORIES)
                self.beep(750, 8)

            elif ev == 'ENTER':
                self.beep(1200, 15)
                target_key = MAIN_CATEGORIES[self.main_sel][2]

                if target_key == "sys":
                    try:
                        import app_htop
                        htop = app_htop.HtopApp(self.tft, self.audio, self.inputs, self.cfg)
                        htop.run()
                    except Exception as e:
                        self.show_dialog("Ошибка", ["Не удалось открыть HTOP:", str(e)[:24]])
                elif target_key == "snd":
                    self.view_sound()
                elif target_key == "dev":
                    self.view_devices()
                elif target_key == "pers":
                    self.view_personalization()
                elif target_key == "apps":
                    self.open_uninstaller(False)
                elif target_key == "time":
                    self.view_time_and_language()
                elif target_key == "games":
                    self.open_uninstaller(True)

                gc.collect()