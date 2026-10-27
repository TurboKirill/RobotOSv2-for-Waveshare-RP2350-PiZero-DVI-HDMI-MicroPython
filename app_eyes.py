# app_eyes.py - Модуль мимики робота для DVI 320x240 (RP2350)
# 9 анимаций, палитра цветов, центрирование на ландшафтном экране
import time
import math
import random
import struct
from dvi_display import color565 as rgb
from gui import draw_text

W, H = 320, 240

# Палитра цветов глаз робота
COLOR_PALETTE = [
    ("CYAN",    rgb(0, 240, 255)),   # 🩵 Неоновый Бирюзовый
    ("GREEN",   rgb(0, 255, 70)),    # 💚 Ярко-зелёный
    ("YELLOW",  rgb(255, 230, 0)),   # 💛 Жёлтый
    ("RED",     rgb(255, 30, 30)),   # 🔴 Боевой красный
    ("PURPLE",  rgb(210, 40, 255)),  # 💜 Пурпурный
    ("WHITE",   0xFFFF),             # ⚪ Чистый белый
    ("BLUE",    rgb(0, 130, 255)),   # 💙 Синий
    ("ORANGE",  rgb(255, 120, 0)),   # 🧡 Оранжевый
    ("PINK",    rgb(255, 80, 180)),  # 🩷 Неоново-розовый
]

class RobotEyesApp:
    def __init__(self, tft, audio, inputs, color_idx=0, mode="DEMO", config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.color_idx = color_idx
        self.mode = mode
        self.cfg = config if config else {"vol_ui": 30, "mute": False}

        # Геометрия глаз для экрана DVI 320x240 (ровно по центру)
        self.ref_w = 80
        self.ref_h = 90
        self.ref_r = 18
        self.space = 26
        self.cx, self.cy = 160, 110

        self.anim_idx = 0
        self.anim_names = [
            "0: ПРОБУЖДЕНИЕ", "1: ОБЫЧНЫЙ", "2: ВЛЕВО", "3: ВПРАВО",
            "4: МОРГАНИЕ", "5: БЫСТР. МОРГАНИЕ", "6: УЛЫБКА", "7: ГРУСТЬ",
            "8: САККАДЫ", "9: СОН"
        ]

        self.reset_coords()

    @property
    def current_color(self):
        return COLOR_PALETTE[self.color_idx][1]

    def reset_coords(self):
        self.lx = self.cx - self.ref_w // 2 - self.space // 2
        self.ly = self.cy
        self.rx = self.cx + self.ref_w // 2 + self.space // 2
        self.ry = self.cy
        self.lw, self.lh = self.ref_w, self.ref_h
        self.rw, self.rh = self.ref_w, self.ref_h
        self.r = self.ref_r

    def beep(self, freq, ms, vol=1500):
        """Мягкие электронные трели робота"""
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

    def draw_round_rect(self, x, y, w, h, r, color):
        """Сглаженный прямоугольник со скруглением углов"""
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

    def render(self, caption=None):
        self.tft.fill(0x0000)

        # Левый глаз
        self.draw_round_rect(
            self.lx - self.lw // 2, self.ly - self.lh // 2,
            self.lw, self.lh, self.r, self.current_color
        )
        # Правый глаз
        self.draw_round_rect(
            self.rx - self.rw // 2, self.ry - self.rh // 2,
            self.rw, self.rh, self.r, self.current_color
        )

        # Подписи и цвет выводятся ТОЛЬКО в ручном режиме тестирования (MANUAL)
        if caption and self.mode != "DEMO":
            draw_text(self.tft, caption, 12, 222, rgb(130, 145, 175))
            c_name = COLOR_PALETTE[self.color_idx][0]
            draw_text(self.tft, f"ЦВЕТ: {c_name}", 210, 222, self.current_color)

        self.tft.show()

    # ================= 9 АНИМАЦИЙ РОБОТА =================

    def anim_0_wakeup(self):
        self.beep(600, 30); self.beep(900, 50); self.beep(1200, 80)
        for h in range(4, self.ref_h + 1, 8):
            self.lh = self.rh = h
            self.r = min(self.ref_r, h // 2)
            self.render(self.anim_names[0])
            time.sleep_ms(20)
        self.reset_coords()
        self.render(self.anim_names[0])

    def anim_1_normal(self):
        self.reset_coords()
        self.render(self.anim_names[1])

    def anim_2_look_left(self):
        self.beep(1100, 40); self.beep(1500, 50)
        self.lw += 12; self.lh += 12
        self.lx -= 30; self.rx -= 30
        self.render(self.anim_names[2])
        time.sleep(0.7)
        self.reset_coords()
        self.render(self.anim_names[2])

    def anim_3_look_right(self):
        self.beep(1100, 40); self.beep(1500, 50)
        self.rw += 12; self.rh += 12
        self.lx += 30; self.rx += 30
        self.render(self.anim_names[3])
        time.sleep(0.7)
        self.reset_coords()
        self.render(self.anim_names[3])

    def anim_4_blink(self):
        self.beep(1400, 12, vol=2000)
        orig_h = self.lh
        for h in [orig_h // 2, 4, orig_h // 2, orig_h]:
            self.lh = self.rh = h
            self.r = min(self.ref_r, h // 2)
            self.render(self.anim_names[4])
            time.sleep_ms(20)
        self.reset_coords()

    def anim_5_fast_blink(self):
        self.anim_4_blink()
        time.sleep_ms(70)
        self.anim_4_blink()

    def anim_6_happy(self):
        for f in [900, 1300, 1750]: self.beep(f, 30)
        self.render(self.anim_names[6])
        # Улыбчивый прищур век снизу
        for i in range(12):
            cut_h = 14 + i * 2
            self.tft.fill_rect(int(self.lx - self.lw // 2), int(self.ly + 10 + i * 2), int(self.lw), cut_h, 0x0000)
            self.tft.fill_rect(int(self.rx - self.rw // 2), int(self.ry + 10 + i * 2), int(self.rw), cut_h, 0x0000)
            self.tft.show()
            time.sleep_ms(25)
        time.sleep(0.9)
        self.reset_coords()
        self.render(self.anim_names[6])

    def anim_7_sad(self):
        self.beep(700, 70); self.beep(450, 110)
        self.render(self.anim_names[7])
        # Грустные веки сверху
        for i in range(10):
            cut_h = 14 + i * 2
            self.tft.fill_rect(int(self.lx - self.lw // 2), int(self.ly - self.lh // 2), int(self.lw), cut_h, 0x0000)
            self.tft.fill_rect(int(self.rx - self.rw // 2), int(self.ry - self.lh // 2), int(self.rw), cut_h, 0x0000)
            self.tft.show()
            time.sleep_ms(25)
        time.sleep(0.9)
        self.reset_coords()
        self.render(self.anim_names[7])

    def anim_8_saccade(self):
        for _ in range(3):
            dx = random.choice([-20, 20])
            dy = random.choice([-8, 8])
            self.lx += dx; self.rx += dx
            self.ly += dy; self.ry += dy
            self.render(self.anim_names[8])
            time.sleep_ms(120)
            self.lx -= dx; self.rx -= dx
            self.ly -= dy; self.ry -= dy
        self.render(self.anim_names[8])

    def anim_9_sleep(self):
        self.beep(800, 40); self.beep(400, 90)
        for h in range(self.ref_h, 3, -8):
            self.lh = self.rh = h
            self.r = min(self.ref_r, h // 2)
            self.render(self.anim_names[9])
            time.sleep_ms(20)
        time.sleep(1.0)
        self.reset_coords()

    def play_by_index(self, idx):
        funcs = [
            self.anim_0_wakeup, self.anim_1_normal, self.anim_2_look_left,
            self.anim_3_look_right, self.anim_4_blink, self.anim_5_fast_blink,
            self.anim_6_happy, self.anim_7_sad, self.anim_8_saccade, self.anim_9_sleep
        ]
        if 0 <= idx < len(funcs):
            funcs[idx]()

    def run(self):
        self.anim_0_wakeup()
        last_auto = time.ticks_ms()

        while True:
            ev = self.inputs.get_event()
            if ev:
                if ev in ('BACK', 'ESC'):
                    self.beep(500, 40)
                    break

                # Листаем анимации 0..9 (Влево / Вправо)
                elif ev == 'RIGHT':
                    self.anim_idx = (self.anim_idx + 1) % 10
                    self.play_by_index(self.anim_idx)
                elif ev == 'LEFT':
                    self.anim_idx = (self.anim_idx - 1) % 10
                    self.play_by_index(self.anim_idx)

                # Меняем цвет глаз (Вверх / Вниз)
                elif ev == 'UP':
                    self.color_idx = (self.color_idx + 1) % len(COLOR_PALETTE)
                    self.beep(1200, 15)
                    self.render(self.anim_names[self.anim_idx])
                elif ev == 'DOWN':
                    self.color_idx = (self.color_idx - 1) % len(COLOR_PALETTE)
                    self.beep(1000, 15)
                    self.render(self.anim_names[self.anim_idx])

                # Пробел: переключение ДЕМО / РУЧНОЙ режим
                elif ev == ' ':
                    self.mode = "MANUAL" if self.mode == "DEMO" else "DEMO"
                    self.beep(1500, 25)
                    lbl = f"{self.anim_names[self.anim_idx]} [{self.mode}]"
                    self.render(lbl)

                elif ev == 'ENTER':
                    self.play_by_index(self.anim_idx)

                last_auto = time.ticks_ms()

            # В DEMO-режиме робот сам периодически выражает эмоции
            if self.mode == "DEMO":
                now = time.ticks_ms()
                if time.ticks_diff(now, last_auto) > 2800:
                    self.anim_idx = random.choice([1, 2, 3, 4, 5, 6, 8])
                    self.play_by_index(self.anim_idx)
                    last_auto = time.ticks_ms()

            time.sleep_ms(20)