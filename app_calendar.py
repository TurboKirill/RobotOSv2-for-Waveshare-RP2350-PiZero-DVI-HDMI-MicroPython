# app_calendar.py - Всплывающий календарь и часы без мерцания (DVI 320x240)
import time
import math
import struct
import gc
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240
TB_H = 22
TB_Y = H - TB_H  # 218px

# Палитра Windows 10 Flyout
C_FLYOUT_BG  = rgb(26, 30, 40)       # Глубокий тёмно-серый фон
C_BORDER     = rgb(55, 65, 85)       # Тонкая строгая рамка
C_ACCENT     = rgb(0, 160, 255)      # Неоново-голубой Win10
C_TODAY_BG   = rgb(0, 110, 210)      # Синяя плашка сегодняшнего числа
C_WHITE      = 0xFFFF
C_GRAY       = rgb(150, 160, 175)
C_DARK_GRAY  = rgb(100, 110, 130)
C_WEEKEND    = rgb(255, 80, 80)      # Красный цвет выходных

class CalendarApp:
    def __init__(self, tft, audio, inputs, config=None, bg_drawer=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False, "hour": 22, "minute": 52, "day": 21, "month": 10, "year": 2026}
        self.bg_drawer = bg_drawer  # Отрисовка без tft.show()

        # Просмотр месяца (можно листать стрелками < >)
        self.view_m = self.cfg.get("month", 10)
        self.view_y = self.cfg.get("year", 2026)

    def beep(self, freq=1100, ms=10):
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

    def days_in_month(self, m, y):
        if m in (1, 3, 5, 7, 8, 10, 12): return 31
        elif m in (4, 6, 9, 11): return 30
        elif m == 2:
            return 29 if ((y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)) else 28
        return 30

    def day_of_week(self, d, m, y):
        """Алгоритм Сакамото: 0=Понедельник ... 6=Воскресенье"""
        t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
        if m < 3: y -= 1
        dow = (y + y // 4 - y // 100 + y // 400 + t[m - 1] + d) % 7
        return (dow + 6) % 7

    def draw_flyout(self):
        t = self.tft

        # 1. Фоновый рабочий стол рисуется В БУФЕР (без вызова tft.show!)
        if self.bg_drawer:
            self.bg_drawer()
        else:
            t.fill(self.cfg.get("desktop_color", rgb(58, 110, 165)))

        # Габариты виджета календаря (прижат в правый угол над часами)
        ww, wh = 156, 162
        wx = W - ww - 2  # X = 162
        wy = TB_Y - wh   # Y = 56

        m_names = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        d_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

        # Время и секунды
        cur_h = self.cfg.get("hour", 22)
        cur_m = self.cfg.get("minute", 52)
        sec = (time.ticks_ms() // 1000) % 60

        real_d = self.cfg.get("day", 21)
        real_m = self.cfg.get("month", 10)
        real_y = self.cfg.get("year", 2026)
        dow_idx = self.day_of_week(real_d, real_m, real_y)

        # 2. Тёмная карточка виджета с чёткой рамкой
        t.fill_rect(wx, wy, ww, wh, C_FLYOUT_BG)
        t.rect(wx, wy, ww, wh, C_BORDER)

        # 3. Живые цифровые часы
        time_str = "%02d:%02d:%02d" % (cur_h, cur_m, sec)
        draw_text(t, time_str, wx + 10, wy + 8, rgb(0, 220, 255))

        # День недели и дата прописью
        draw_text(t, d_names[dow_idx][:10], wx + 82, wy + 8, C_WHITE)
        full_date_str = f"{real_d} {m_names[real_m]} {real_y}"
        draw_text(t, full_date_str, wx + 10, wy + 20, C_GRAY)

        # Разделитель
        t.line(wx + 8, wy + 32, wx + ww - 8, wy + 32, rgb(48, 54, 70))

        # 4. Навигация по месяцам: < Октябрь 2026 >
        month_str = f"< {m_names[self.view_m]} {self.view_y} >"
        m_x = wx + (ww - len(month_str) * 8) // 2
        draw_text(t, month_str, m_x, wy + 38, C_WHITE)

        # Дни недели (Пн Вт Ср Чт Пт Сб Вс)
        days_hdr = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        start_grid_x = wx + 8
        for di, dh in enumerate(days_hdr):
            col = C_WEEKEND if di >= 5 else rgb(150, 160, 180)
            draw_text(t, dh, start_grid_x + di * 20, wy + 52, col)

        # 5. Сетка чисел месяца
        first_dow = self.day_of_week(1, self.view_m, self.view_y)
        total_days = self.days_in_month(self.view_m, self.view_y)

        cell_x = first_dow
        cell_y = 0
        for day in range(1, total_days + 1):
            dx = start_grid_x + cell_x * 20
            dy = wy + 66 + cell_y * 13

            # Отцентрированная синяя рамка сегодняшнего дня
            is_today = (day == real_d and self.view_m == real_m and self.view_y == real_y)
            if is_today:
                t.fill_rect(dx - 2, dy - 2, 20, 12, C_TODAY_BG)
                t.rect(dx - 2, dy - 2, 20, 12, C_WHITE)

            col = C_WHITE if is_today else (C_WEEKEND if cell_x >= 5 else rgb(220, 225, 235))
            draw_text(t, "%2d" % day, dx, dy, col)

            cell_x += 1
            if cell_x > 6:
                cell_x = 0
                cell_y += 1

        # 6. Подвал (аккуратные подписи)
        t.line(wx + 8, wy + wh - 16, wx + ww - 8, wy + wh - 16, rgb(48, 54, 70))
        draw_text(t, "< >:Месяц", wx + 8, wy + wh - 12, C_DARK_GRAY)
        draw_text(t, "ESC", wx + ww - 32, wy + wh - 12, C_WHITE)

        # 7. Панель задач снизу: подсвечиваем кнопку часов
        t.fill_rect(273, TB_Y, 47, TB_H, rgb(48, 52, 64))
        clock_str = "%02d:%02d" % (cur_h, cur_m)
        t.text(clock_str, 276, TB_Y + 7, rgb(0, 220, 255))

        # ЕДИНСТВЕННЫЙ ВЫЗОВ НА ВЕСЬ КАДР! НИКАКОГО МЕРЦАНИЯ!
        t.show()

    def run(self):
        self.beep(1200, 15)
        last_sec = -1

        while True:
            cur_sec = (time.ticks_ms() // 1000) % 60

            # Перерисовываем экран ТОЛЬКО когда реально сменилась секунда!
            if cur_sec != last_sec:
                last_sec = cur_sec
                self.draw_flyout()

            # Быстрый опрос кнопок
            ev = self.inputs.get_event()
            if ev:
                if ev in ('BACK', 'ESC', 'ENTER'):
                    self.beep(700, 15)
                    return
                elif ev == 'LEFT':
                    self.view_m -= 1
                    if self.view_m < 1:
                        self.view_m = 12
                        self.view_y -= 1
                    self.beep(900, 10)
                    self.draw_flyout()
                elif ev == 'RIGHT':
                    self.view_m += 1
                    if self.view_m > 12:
                        self.view_m = 1
                        self.view_y += 1
                    self.beep(900, 10)
                    self.draw_flyout()

            time.sleep_ms(25)