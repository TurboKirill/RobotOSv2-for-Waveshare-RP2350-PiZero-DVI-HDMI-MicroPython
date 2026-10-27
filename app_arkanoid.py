# app_arkanoid.py - Классический Арканоид RobotOS (DVI 320x240)
# 8 колонок кирпичей, 5 физических скоростей, панель задач Windows 10
import time
import math
import struct
import random
import gc
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240
TB_H = 22
WIN_H = H - TB_H  # 218px

# Палитра
C_BG       = rgb(14, 18, 28)       # Тёмно-синий аркадный фон
C_HEADER   = rgb(28, 32, 44)       # Шапка окна
C_BORDER   = rgb(45, 54, 75)       # Стенки игрового поля
C_PADDLE   = rgb(0, 220, 255)      # Неоново-голубая ракетка
C_BALL     = 0xFFFF                # Белый мяч
C_SPD      = rgb(255, 225, 0)      # Жёлтый (Скорость)
C_WHITE    = 0xFFFF
C_GRAY     = rgb(140, 150, 170)

# Цвета рядов кирпичей (от верхнего к нижнему)
ROW_COLORS = [
    rgb(255, 50, 70),    # Ряд 0: 50 очков (Красный)
    rgb(255, 130, 20),   # Ряд 1: 40 очков (Оранжевый)
    rgb(255, 220, 20),   # Ряд 2: 30 очков (Жёлтый)
    rgb(0, 230, 100),    # Ряд 3: 20 очков (Зелёный)
    rgb(0, 180, 255),    # Ряд 4: 10 очков (Голубой)
]

class ArkanoidApp:
    def __init__(self, tft, audio, inputs, config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False, "hour": 20, "minute": 45}

        # 5 физических профилей скорости (шаг, субшаги, скорость ракетки)
        self.physics_profiles = [
            {"step": 2, "substeps": 1, "pad_spd": 9},   # x1 (медленно)
            {"step": 3, "substeps": 1, "pad_spd": 12},  # x2 (классика)
            {"step": 5, "substeps": 1, "pad_spd": 16},  # x3 (быстро)
            {"step": 4, "substeps": 2, "pad_spd": 20},  # x4 (профи)
            {"step": 5, "substeps": 2, "pad_spd": 25},  # x5 (ракета)
        ]
        self.speed_lvl = 1  # По умолчанию x2

        # Платформа (Ракетка) под экран 320px
        self.pad_w = 54
        self.pad_h = 7
        self.pad_y = 202
        self.pad_x = (W - self.pad_w) // 2

        # Мяч
        self.ball_size = 5
        self.reset_ball()

        # Кирпичи: 5 рядов по 8 колонок
        self.rows = 5
        self.cols = 8
        self.brick_w = 34
        self.brick_h = 9
        self.brick_y_start = 30
        self.init_bricks()

        self.score = 0
        self.lives = 3
        self.game_over = False
        self.game_won = False
        self.ball_attached = True

    def init_bricks(self):
        self.bricks = [[1 for _ in range(self.cols)] for _ in range(self.rows)]

    def reset_ball(self):
        self.ball_x = self.pad_x + self.pad_w // 2 - self.ball_size // 2
        self.ball_y = self.pad_y - self.ball_size - 1
        prof = self.physics_profiles[self.speed_lvl]
        self.ball_dx = prof["step"]
        self.ball_dy = -prof["step"]
        self.ball_attached = True

    def apply_speed_to_ball(self):
        step = self.physics_profiles[self.speed_lvl]["step"]
        self.ball_dx = step if self.ball_dx > 0 else -step
        self.ball_dy = step if self.ball_dy > 0 else -step

    def beep(self, freq=900, ms=15):
        if self.cfg.get("mute") or self.cfg.get("vol_ui", 30) == 0:
            return
        rate = 22050
        samples = max(2, int(rate / freq))
        cycle = bytearray(samples * 2)
        amp = int(1000 * (self.cfg.get("vol_ui", 30) / 100))
        for i in range(samples):
            v = int(amp * math.sin(2 * math.pi * i / samples))
            struct.pack_into("<h", cycle, i * 2, v)
        for _ in range(max(1, int((ms / 1000) * freq))):
            self.audio.write(cycle)

    def draw_screen(self):
        t = self.tft

        # 1. Шапка окна (Y = 0..19)
        t.fill_rect(0, 0, W, 20, C_HEADER)
        t.line(0, 19, W, 19, C_BORDER)
        draw_text(t, f"СЧЕТ:{self.score:04d}", 10, 6, C_WHITE)
        draw_text(t, f"СК:x{self.speed_lvl + 1}", 110, 6, C_SPD)
        draw_text(t, f"ЖИЗНИ:{'#' * self.lives}", 170, 6, rgb(255, 60, 60))
        t.text("Esc", 294, 6, C_WHITE)

        # 2. Игровое поле (Y = 20..217)
        t.fill_rect(0, 20, W, 198, C_BG)

        # Боковые стенки поля
        t.fill_rect(0, 20, 6, 198, C_BORDER)
        t.fill_rect(W - 6, 20, 6, 198, C_BORDER)
        t.line(6, 217, W - 6, 217, C_BORDER)

        # Отрисовка кирпичей
        remaining = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if self.bricks[r][c] == 1:
                    remaining += 1
                    bx = 14 + c * (self.brick_w + 3)
                    by = self.brick_y_start + r * (self.brick_h + 3)
                    t.fill_rect(bx, by, self.brick_w, self.brick_h, ROW_COLORS[r])
                    t.line(bx, by, bx + self.brick_w - 1, by, C_WHITE)

        if remaining == 0:
            self.game_won = True

        # Платформа и мяч
        t.fill_rect(int(self.pad_x), self.pad_y, self.pad_w, self.pad_h, C_PADDLE)
        t.rect(int(self.pad_x), self.pad_y, self.pad_w, self.pad_h, C_WHITE)
        t.fill_rect(int(self.ball_x), int(self.ball_y), self.ball_size, self.ball_size, C_BALL)

        # Подсказка запуска мяча
        if self.ball_attached:
            draw_text(t, "ENTER: Запуск мяча", 88, 125, C_PADDLE)
            draw_text(t, "ВВЕРХ/ВНИЗ: Скорость", 80, 145, C_SPD)

        # 3. Системная панель задач RobotOS (Y = 218..239)
        draw_system_taskbar(t, self.cfg, active_tab="Арканоид", tab_icon="game")

        t.show()

    def step_physics(self):
        """Один микрошаг физики"""
        if self.ball_attached:
            self.ball_x = self.pad_x + self.pad_w // 2 - self.ball_size // 2
            self.ball_y = self.pad_y - self.ball_size - 1
            return

        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy

        # Отскок от левой и правой стенки
        if self.ball_x <= 7:
            self.ball_x = 7
            self.ball_dx = abs(self.ball_dx)
            self.beep(600, 8)
        elif self.ball_x >= W - 7 - self.ball_size:
            self.ball_x = W - 7 - self.ball_size
            self.ball_dx = -abs(self.ball_dx)
            self.beep(600, 8)

        # Потолок
        if self.ball_y <= 21:
            self.ball_y = 21
            self.ball_dy = abs(self.ball_dy)
            self.beep(600, 8)

        # Отскок от платформы
        if (self.pad_y <= self.ball_y + self.ball_size <= self.pad_y + self.pad_h + 4) and \
           (self.pad_x - 3 <= self.ball_x <= self.pad_x + self.pad_w + 3):
            self.ball_dy = -abs(self.ball_dy)
            self.ball_y = self.pad_y - self.ball_size - 1

            # Физический угол рикошета
            hit_offset = (self.ball_x + self.ball_size // 2) - (self.pad_x + self.pad_w // 2)
            step = self.physics_profiles[self.speed_lvl]["step"]
            if hit_offset < -12:   self.ball_dx = -int(step * 1.3)
            elif hit_offset > 12:  self.ball_dx = int(step * 1.3)
            else:                  self.ball_dx = step if self.ball_dx > 0 else -step

            self.beep(950, 12)

        # Столкновение с кирпичами
        for r in range(self.rows):
            for c in range(self.cols):
                if self.bricks[r][c] == 1:
                    bx = 14 + c * (self.brick_w + 3)
                    by = self.brick_y_start + r * (self.brick_h + 3)

                    if (bx <= self.ball_x + self.ball_size and self.ball_x <= bx + self.brick_w) and \
                       (by <= self.ball_y + self.ball_size and self.ball_y <= by + self.brick_h):
                        self.bricks[r][c] = 0
                        self.ball_dy = -self.ball_dy
                        self.score += (5 - r) * 10
                        self.beep(1100 + (5 - r) * 120, 14)
                        return

        # Падение мяча мимо платформы
        if self.ball_y > 214:
            self.lives -= 1
            self.beep(300, 90)
            if self.lives <= 0:
                self.game_over = True
            else:
                self.reset_ball()

    def run(self):
        while not self.game_over and not self.game_won:
            prof = self.physics_profiles[self.speed_lvl]

            ev = self.inputs.get_event()
            if ev:
                if ev in ['BACK', 'ESC']:
                    self.beep(500, 20)
                    return
                elif ev == 'LEFT':
                    self.pad_x = max(8, self.pad_x - prof["pad_spd"])
                elif ev == 'RIGHT':
                    self.pad_x = min(W - self.pad_w - 8, self.pad_x + prof["pad_spd"])
                elif ev == 'UP':
                    if self.speed_lvl < len(self.physics_profiles) - 1:
                        self.speed_lvl += 1
                        self.apply_speed_to_ball()
                        self.beep(1600, 12)
                elif ev == 'DOWN':
                    if self.speed_lvl > 0:
                        self.speed_lvl -= 1
                        self.apply_speed_to_ball()
                        self.beep(650, 12)
                elif ev in ['ENTER', ' '] and self.ball_attached:
                    self.ball_attached = False
                    step = prof["step"]
                    self.ball_dx = random.choice([-step, step])
                    self.ball_dy = -step
                    self.beep(1200, 15)

            # Выполнение микрошагов физики
            for _ in range(prof["substeps"]):
                self.step_physics()
                if self.ball_attached or self.game_over or self.game_won:
                    break

            self.draw_screen()
            time.sleep_ms(14)

        # Модальное окно финала
        self.tft.fill_rect(50, 70, 220, 80, rgb(28, 32, 44))
        self.tft.rect(50, 70, 220, 80, C_PADDLE)

        if self.game_won:
            draw_text(self.tft, "ПОБЕДА! ВЫ ВЫИГРАЛИ!", 66, 85, rgb(0, 255, 100))
        else:
            draw_text(self.tft, "ИГРА ОКОНЧЕНА!", 100, 85, rgb(255, 60, 60))

        draw_text(self.tft, f"ИТОГОВЫЙ СЧЁТ: {self.score}", 80, 108, C_WHITE)
        draw_text(self.tft, "ENTER: Заново   ESC: Выход", 64, 126, C_SPD)
        self.tft.show()

        time.sleep(1.0)
        while True:
            ev = self.inputs.get_event()
            if ev in ['BACK', 'ESC']:
                break
            elif ev in ['ENTER', ' ']:
                # Рестарт игры
                self.score = 0
                self.lives = 3
                self.game_over = False
                self.game_won = False
                self.init_bricks()
                self.reset_ball()
                self.run()
                break
            time.sleep_ms(30)