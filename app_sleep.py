# app_sleep.py - Анимация сна со скругленными живыми глазками (DVI 320x240)
import time
import math
import struct
from dvi_display import color565 as rgb
from gui import draw_text

W, H = 320, 240

C_BG   = 0x0000
C_GLOW = rgb(0, 240, 255)   # Неоновый бирюзовый (в тон глаз робота)
C_GRAY = rgb(120, 140, 180) # Мягкий цвет для Zzz...

class SleepApp:
    def __init__(self, tft, audio, inputs, config=None, pwm_bl=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False, "brightness": 90}
        self.pwm_bl = pwm_bl

        # Точные размеры и центрирование как в app_eyes.py (DVI 320x240)
        self.w = 80
        self.h = 90
        self.r = 18
        self.lx = 107
        self.rx = 213
        self.cy = 115

    def beep(self, freq, ms, vol=1500):
        if self.cfg.get("mute") or self.cfg.get("vol_ui", 30) == 0:
            return
        rate = 22050
        samples = max(2, int(rate / freq))
        cycle = bytearray(samples * 2)
        amp = int(vol * (self.cfg.get("vol_ui", 30) / 100))
        for i in range(samples):
            v = int(amp * math.sin(2 * math.pi * i / samples))
            struct.pack_into("<h", cycle, i * 2, v)
        for _ in range(max(1, int((ms / 1000) * freq))):
            self.audio.write(cycle)

    def fade_backlight(self, from_pct, to_pct, steps=15):
        """Плавное угасание ШИМ подсветки (если подключена)"""
        if not self.pwm_bl: return
        step = (to_pct - from_pct) / steps
        for i in range(steps):
            cur = from_pct + step * (i + 1)
            duty = int(65535 * (max(0, min(100, cur)) / 100))
            self.pwm_bl.duty_u16(duty)
            time.sleep_ms(20)

    def draw_round_rect(self, x, y, w, h, r, color):
        """Математически точное скругление дуг глаз"""
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

    def draw_both_eyes(self, w, h, r):
        """Отрисовка пары скругленных глаз ровно по центру"""
        self.draw_round_rect(self.lx - w // 2, self.cy - h // 2, w, h, r, C_GLOW)
        self.draw_round_rect(self.rx - w // 2, self.cy - h // 2, w, h, r, C_GLOW)

    def anim_collapse_to_slits(self):
        """Анимация засыпания: глаза мягко смыкаются в щелочки, затем в точки"""
        # Убаюкивающий нисходящий звук
        self.beep(750, 40)
        self.beep(550, 60)
        self.beep(350, 100)

        # 1. Глаза мягко смыкаются (высота 90 -> 4 пикселя)
        for h in [90, 64, 40, 20, 8, 4]:
            self.tft.fill(C_BG)
            r = min(self.r, h // 2)
            self.draw_both_eyes(self.w, h, r)
            self.tft.show()
            time.sleep_ms(25)

        # 2. Мягкая пауза с надписью Zzz...
        draw_text(self.tft, "Zzz...", self.rx + 24, self.cy - 30, C_GRAY)
        self.tft.show()
        time.sleep(0.8)

        # 3. Закрытые округлые полоски сжимаются в точки
        for w in [self.w, 54, 32, 14, 4]:
            self.tft.fill(C_BG)
            r = min(2, w // 2)
            self.draw_both_eyes(w, 4, r)
            self.tft.show()
            time.sleep_ms(20)

        # 4. Погружение экрана в полную темноту
        current_br = self.cfg.get("brightness", 90)
        self.fade_backlight(current_br, 0, steps=20)
        self.tft.fill(C_BG)
        self.tft.show()

    def anim_wakeup(self):
        """Анимация пробуждения: распахнутые круглые глаза и радостный аккорд"""
        target_br = self.cfg.get("brightness", 90)
        self.fade_backlight(0, target_br, steps=15)

        # 1. Из точек вырастают округлые щелочки
        for w in [4, 18, 40, 62, self.w]:
            self.tft.fill(C_BG)
            r = min(2, w // 2)
            self.draw_both_eyes(w, 4, r)
            self.tft.show()
            time.sleep_ms(15)

        # 2. Веки распахиваются в большие открытые глаза
        for h in [4, 18, 40, 65, self.h]:
            self.tft.fill(C_BG)
            r = min(self.r, h // 2)
            self.draw_both_eyes(self.w, h, r)
            self.tft.show()
            time.sleep_ms(20)

        # Победная трель пробуждения
        self.beep(400, 30)
        self.beep(750, 40)
        self.beep(1200, 70)
        time.sleep(0.4)

    def run(self):
        # Засыпаем
        self.anim_collapse_to_slits()

        # Ждем нажатия любой клавиши на клавиатуре или пульта
        while True:
            ev = self.inputs.get_event()
            if ev:
                break
            time.sleep_ms(30)

        # Просыпаемся и возвращаемся в систему
        self.anim_wakeup()