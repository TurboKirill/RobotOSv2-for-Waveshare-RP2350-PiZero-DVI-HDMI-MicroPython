# app_snake.py - Неоновая Змейка (Cyber-Snake) для RobotOS (DVI 320x240)
# Поле 30 x 18 клеток по 10 px. Рисуется только то, что изменилось (голова, хвост, еда).
import time
import math
import struct
import random
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240

# Игровое поле: 300 x 180 px, между шапкой (0..20) и панелью задач (218..239)
CELL   = 10
GRID_W = 30
GRID_H = 18
OFF_X  = 10
OFF_Y  = 29

C_BG      = 0x0000
C_HEADER  = rgb(18, 24, 44)
C_FIELD   = rgb(6, 10, 22)           # тёмно-синий фон поля
C_BORDER  = rgb(0, 120, 215)         # рамка поля
C_HEAD    = rgb(255, 255, 255)
C_BODY    = rgb(0, 240, 100)
C_FOOD    = rgb(255, 30, 80)
C_WHITE   = 0xFFFF
C_SCORE   = rgb(0, 220, 255)
C_BEST    = rgb(255, 230, 0)
C_RED     = rgb(255, 80, 80)
C_GREEN   = rgb(0, 230, 120)
C_PANEL   = rgb(30, 32, 40)
C_GRAY    = rgb(140, 150, 170)

DIRS = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
OPP  = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}
BACK_KEYS = ('BACK', 'ESC')

START_MS = 130      # начальная задержка между шагами
MIN_MS   = 55       # самая быстрая скорость


class SnakeApp:
    def __init__(self, tft, audio, inputs, config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config is not None else {
            "vol_ui": 30, "mute": False, "hour": 20, "minute": 45}
        self.best = self.cfg.get("snake_best", 0)    # рекорд живёт, пока включена плата
        self._wave = {}
        self.reset_game()

    # ------------------------------------------------------------ звук
    def beep(self, freq=1200, ms=20):
        vol = self.cfg.get("vol_ui", 30)
        if self.cfg.get("mute") or vol == 0:
            return
        amp = int(1200 * vol / 100)
        key = (freq, amp)
        w = self._wave.get(key)
        if w is None:
            n = max(2, int(22050 / freq))
            w = bytearray(n * 2)
            for i in range(n):
                struct.pack_into("<h", w, i * 2, int(amp * math.sin(2 * math.pi * i / n)))
            if len(self._wave) > 12:
                self._wave.clear()
            self._wave[key] = w
        for _ in range(max(1, int((ms / 1000) * freq))):
            self.audio.write(w)

    # ------------------------------------------------------------ логика
    def reset_game(self):
        cx, cy = GRID_W // 2, GRID_H // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]   # голова - первая
        self.occ = set(self.snake)                             # быстрая проверка занятости
        self.dir = 'RIGHT'
        self.queue = []                                        # очередь поворотов (макс. 2)
        self.score = 0
        self.speed = START_MS
        self.over = False
        self.won = False
        self.spawn_food()

    def spawn_food(self):
        if len(self.snake) >= GRID_W * GRID_H:
            self.food = None
            return
        for _ in range(60):
            p = (random.randint(0, GRID_W - 1), random.randint(0, GRID_H - 1))
            if p not in self.occ:
                self.food = p
                return
        free = [(x, y) for y in range(GRID_H) for x in range(GRID_W) if (x, y) not in self.occ]
        self.food = random.choice(free)

    def push_dir(self, d):
        last = self.queue[-1] if self.queue else self.dir
        if d != last and d != OPP[last] and len(self.queue) < 2:
            self.queue.append(d)

    def step(self):
        """Один шаг змейки. Рисует только изменившиеся клетки."""
        if self.queue:
            d = self.queue.pop(0)
            if d != OPP[self.dir]:
                self.dir = d
        dx, dy = DIRS[self.dir]
        old = self.snake[0]
        nh = (old[0] + dx, old[1] + dy)

        if nh[0] < 0 or nh[0] >= GRID_W or nh[1] < 0 or nh[1] >= GRID_H:
            self.over = True
            return
        tail = self.snake[-1]
        eating = (nh == self.food)
        # в клетку, где сейчас хвост, можно зайти: хвост за этот шаг уедет
        if nh in self.occ and not (nh == tail and not eating):
            self.over = True
            return

        self.snake.insert(0, nh)
        self.occ.add(nh)
        self.draw_body(old)
        self.draw_head(nh)

        if eating:
            self.score += 10
            if self.score > self.best:
                self.best = self.score
                self.cfg["snake_best"] = self.best
            self.beep(1200, 15)
            self.beep(1700, 25)
            if self.speed > MIN_MS:
                self.speed -= 3
            self.spawn_food()
            if self.food is None:
                self.won = True
                self.over = True
                return
            self.draw_food()
            self.draw_header()
        else:
            self.snake.pop()
            if tail != nh:
                self.occ.discard(tail)
                self.erase(tail)

    # ------------------------------------------------------------ рисование
    def draw_header(self):
        t = self.tft
        t.fill_rect(0, 0, W, 20, C_HEADER)
        t.hline(0, 20, W, C_BORDER)
        draw_text(t, "СЧЕТ: %03d" % self.score, 8, 6, C_SCORE)
        s = "РЕКОРД: %03d" % self.best
        draw_text(t, s, W - 8 - len(s) * 8, 6, C_BEST)

    def erase(self, c):
        self.tft.fill_rect(OFF_X + c[0] * CELL, OFF_Y + c[1] * CELL, CELL, CELL, C_FIELD)

    def draw_body(self, c):
        x = OFF_X + c[0] * CELL
        y = OFF_Y + c[1] * CELL
        self.tft.fill_rect(x, y, CELL, CELL, C_FIELD)
        self.tft.fill_rect(x + 1, y + 1, CELL - 2, CELL - 2, C_BODY)

    def draw_head(self, c):
        t = self.tft
        x = OFF_X + c[0] * CELL
        y = OFF_Y + c[1] * CELL
        t.fill_rect(x, y, CELL, CELL, C_HEAD)
        d = self.dir
        # глазки смотрят по ходу движения
        if d == 'RIGHT':
            e = ((6, 2), (6, 6))
        elif d == 'LEFT':
            e = ((2, 2), (2, 6))
        elif d == 'UP':
            e = ((2, 2), (6, 2))
        else:
            e = ((2, 6), (6, 6))
        for ex, ey in e:
            t.fill_rect(x + ex, y + ey, 2, 2, C_BG)

    def draw_food(self):
        if self.food is None:
            return
        x = OFF_X + self.food[0] * CELL
        y = OFF_Y + self.food[1] * CELL
        self.tft.fill_rect(x, y, CELL, CELL, C_FIELD)
        self.tft.fill_rect(x + 1, y + 1, CELL - 2, CELL - 2, C_FOOD)
        self.tft.fill_rect(x + 3, y + 3, 4, 4, C_WHITE)

    def render_full(self):
        t = self.tft
        t.fill(C_BG)
        self.draw_header()
        t.rect(OFF_X - 2, OFF_Y - 2, GRID_W * CELL + 4, GRID_H * CELL + 4, C_BORDER)
        t.fill_rect(OFF_X, OFF_Y, GRID_W * CELL, GRID_H * CELL, C_FIELD)
        self.draw_food()
        for c in self.snake[1:]:
            self.draw_body(c)
        self.draw_head(self.snake[0])
        draw_system_taskbar(t, self.cfg, active_tab="ЗМЕЙКА", tab_icon="xbox")
        t.show()

    def dialog(self, lines, h):
        """Окно по центру поля: lines = [(текст, цвет), ...]"""
        t = self.tft
        w = 248
        x = (W - w) // 2
        y = OFF_Y + (GRID_H * CELL - h) // 2
        t.fill_rect(x, y, w, h, C_PANEL)
        t.rect(x, y, w, h, C_WHITE)
        yy = y + 14
        for text, col in lines:
            draw_text(t, text, (W - len(text) * 8) // 2, yy, col)
            yy += 20
        t.show()

    # ------------------------------------------------------------ игра
    def play(self):
        """Один раунд. Возвращает 'OVER' или 'EXIT'."""
        paused = False
        nxt = time.ticks_add(time.ticks_ms(), self.speed)
        while True:
            ev = self.inputs.get_event()
            if ev:
                if ev in BACK_KEYS:
                    self.beep(500, 20)
                    return 'EXIT'
                elif ev == 'ENTER':
                    paused = not paused
                    if paused:
                        self.dialog([("ПАУЗА", C_BEST), ("ENTER - дальше", C_SCORE)], 66)
                    else:
                        self.render_full()
                        nxt = time.ticks_add(time.ticks_ms(), self.speed)
                elif ev in DIRS and not paused:
                    self.push_dir(ev)

            if not paused and time.ticks_diff(time.ticks_ms(), nxt) >= 0:
                self.step()
                if self.over:
                    return 'OVER'
                self.tft.show()
                nxt = time.ticks_add(time.ticks_ms(), self.speed)
            time.sleep_ms(5)

    def run(self):
        while self.inputs.get_event():       # сбросить "залипшее" нажатие, которым открыли игру
            pass
        while True:
            self.reset_game()
            self.render_full()
            if self.play() == 'EXIT':
                return

            # конец раунда
            if self.won:
                self.beep(1000, 60)
                self.beep(1500, 60)
                self.beep(2000, 120)
                head = ("ПОБЕДА!", C_GREEN)
            else:
                self.beep(400, 80)
                self.beep(250, 160)
                head = ("ИГРА ОКОНЧЕНА", C_RED)
            self.dialog([head,
                         ("СЧЕТ: %d" % self.score, C_WHITE),
                         ("ENTER - заново  ESC - выход", C_SCORE)], 82)

            while True:
                ev = self.inputs.get_event()
                if ev == 'ENTER':
                    self.beep(1200, 20)
                    break
                elif ev in BACK_KEYS:
                    self.beep(500, 20)
                    return
                time.sleep_ms(30)
