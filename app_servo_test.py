# app_servo_test.py - Тестовый пульт управления шасси робота (DVI 320x240)
# Колеса: GP1/GP2 (360°), Ковш: GP0 (180°), PWM 50Hz, системная панель задач
import time
import math
import struct
import gc
from machine import Pin, PWM
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240
TB_H = 22
WIN_H = H - TB_H  # 218px

# Палитра
C_BG       = rgb(20, 24, 34)       # Тёмно-синий фон
C_HEADER   = rgb(28, 32, 44)       # Шапка окна
C_CARD     = rgb(26, 32, 46)       # Карточки
C_BORDER   = rgb(48, 56, 76)       # Рамки
C_ACCENT   = rgb(0, 210, 255)      # Неоново-голубой
C_GREEN    = rgb(0, 230, 120)      # Зелёный (Вперёд / ОК)
C_ORANGE   = rgb(255, 160, 20)     # Оранжевый (Ковш)
C_RED      = rgb(255, 70, 70)      # Красный (Стоп)
C_WHITE    = 0xFFFF
C_GRAY     = rgb(140, 150, 170)
C_DARK_TXT = rgb(90, 100, 120)

class ServoTestApp:
    def __init__(self, tft, audio, inputs, config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False, "hour": 20, "minute": 45}

        # GP0: Ковш (0-180°), GP1: Правое колесо (360°), GP2: Левое колесо (360°)
        self.pwm_bucket  = self.init_pwm(0)
        self.pwm_r_wheel = self.init_pwm(1)
        self.pwm_l_wheel = self.init_pwm(2)

        self.bucket_angle = 90
        self.chassis_status = "СТОП"
        self.chassis_col = C_RED

        self.stop_all()

    def init_pwm(self, pin_num):
        try:
            p = PWM(Pin(pin_num))
            p.freq(50)
            return p
        except Exception as e:
            print(f"Ошибка инициализации GP{pin_num}:", e)
            return None

    def set_servo_angle(self, pwm, angle):
        if not pwm: return
        angle = max(0, min(180, angle))
        pulse_us = 500 + (angle / 180.0) * 2000
        duty = int(65535 * (pulse_us / 20000))
        pwm.duty_u16(duty)

    def stop_wheels(self):
        # 90 градусов для серв постоянного вращения — нейтраль (СТОП)
        self.set_servo_angle(self.pwm_r_wheel, 90)
        self.set_servo_angle(self.pwm_l_wheel, 90)
        self.chassis_status = "СТОП"
        self.chassis_col = C_RED

    def drive_forward(self):
        self.set_servo_angle(self.pwm_r_wheel, 0)
        self.set_servo_angle(self.pwm_l_wheel, 180)
        self.chassis_status = "ВПЕРЕД [^]"
        self.chassis_col = C_GREEN

    def drive_backward(self):
        self.set_servo_angle(self.pwm_r_wheel, 180)
        self.set_servo_angle(self.pwm_l_wheel, 0)
        self.chassis_status = "НАЗАД [v]"
        self.chassis_col = C_ORANGE

    def turn_left(self):
        self.set_servo_angle(self.pwm_r_wheel, 0)
        self.set_servo_angle(self.pwm_l_wheel, 0)
        self.chassis_status = "ВЛЕВО [<]"
        self.chassis_col = C_ACCENT

    def turn_right(self):
        self.set_servo_angle(self.pwm_r_wheel, 180)
        self.set_servo_angle(self.pwm_l_wheel, 180)
        self.chassis_status = "ВПРАВО [>]"
        self.chassis_col = C_ACCENT

    def stop_all(self):
        self.stop_wheels()
        self.set_servo_angle(self.pwm_bucket, self.bucket_angle)

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
        for _ in range(max(1, int((ms / 1000) * freq))):
            self.audio.write(cycle)

    def auto_demo_routine(self):
        """Автотест: подъем ковша и маневр колес"""
        self.tft.fill_rect(20, 90, 280, 50, rgb(28, 36, 54))
        self.tft.rect(20, 90, 280, 50, C_ACCENT)
        draw_text(self.tft, "ВЫПОЛНЕНИЕ АВТО-ТЕСТА...", 40, 108, C_WHITE)
        self.tft.show()

        # 1. Поднимаем ковш
        for a in range(20, 120, 10):
            self.bucket_angle = a
            self.set_servo_angle(self.pwm_bucket, a)
            time.sleep_ms(35)

        # 2. Едем вперед
        self.drive_forward()
        self.draw_screen()
        time.sleep(0.9)

        # 3. Разворот
        self.turn_right()
        self.draw_screen()
        time.sleep(0.8)

        # 4. Опускаем ковш и стоп
        self.stop_wheels()
        self.bucket_angle = 45
        self.set_servo_angle(self.pwm_bucket, 45)
        self.beep(1500, 30)
        self.draw_screen()

    # ------------------------------------------------------------ Отрисовка UI
    def draw_screen(self):
        t = self.tft

        # 1. Шапка окна (Y = 0..19)
        t.fill_rect(0, 0, W, 20, C_HEADER)
        t.line(0, 19, W, 19, C_BORDER)
        draw_text(t, "Тест сервоприводов", 10, 6, C_WHITE)
        t.text("Esc", 294, 6, C_WHITE)

        # 2. Фон рабочей области
        t.fill_rect(0, 20, W, 198, C_BG)

        # Карточка 1: ШАССИ (Колеса GP1 и GP2) (Y = 24..96)
        t.fill_rect(10, 24, 300, 72, C_CARD)
        t.rect(10, 24, 300, 72, C_BORDER)
        draw_text(t, "ШАССИ РОБОТА (GP1 / GP2)", 18, 30, C_WHITE)

        # Статус шасси с цветовой рамкой
        t.fill_rect(18, 46, 130, 20, rgb(16, 20, 28))
        t.rect(18, 46, 130, 20, self.chassis_col)
        draw_text(t, self.chassis_status, 24, 52, self.chassis_col)

        draw_text(t, "СТРЕЛКИ : Вперед/Назад/Поворот", 18, 72, C_GRAY)
        draw_text(t, "ПРОБЕЛ : Тормоз", 160, 52, C_RED)

        # Карточка 2: КОВШ (Манипулятор GP0) (Y = 102..184)
        t.fill_rect(10, 102, 300, 82, C_CARD)
        t.rect(10, 102, 300, 82, C_BORDER)
        draw_text(t, "ПРИВОД КОВША (GP0)", 18, 108, C_WHITE)

        deg_str = f"УГОЛ: {self.bucket_angle:03d} ГРАД"
        draw_text(t, deg_str, 18, 126, C_ORANGE)

        # Шкала угла ковша
        t.rect(18, 142, 284, 8, C_BORDER)
        fill_w = int(280 * (self.bucket_angle / 180.0))
        if fill_w > 0:
            t.fill_rect(20, 144, fill_w, 4, C_ORANGE)

        # Быстрые пресеты угла
        draw_text(t, "КЛАВИШИ: 1:10'  2:45'  3:90'  4:135'", 18, 160, C_GRAY)

        # Панель подсказок перед панелью задач (Y = 190..217)
        draw_text(t, "ENTER: Демо        ESC: Стоп и Выход", 12, 196, C_DARK_TXT)

        # 3. Системная панель задач RobotOS (Y = 218..239)
        draw_system_taskbar(t, self.cfg, active_tab="Серво", tab_icon="cmd")

        t.show()

    def run(self):
        while True:
            self.draw_screen()

            ev = self.inputs.get_event()
            if not ev:
                time.sleep_ms(20)
                continue

            if ev in ['BACK', 'ESC']:
                self.stop_all()
                self.beep(600, 25)
                return

            # === УПРАВЛЕНИЕ ШАССИ ===
            elif ev == 'UP':
                self.drive_forward()
                self.beep(1200, 10)
            elif ev == 'DOWN':
                self.drive_backward()
                self.beep(900, 10)
            elif ev == 'LEFT':
                self.turn_left()
                self.beep(1000, 10)
            elif ev == 'RIGHT':
                self.turn_right()
                self.beep(1000, 10)
            elif ev in [' ', 's', 'S']:
                self.stop_wheels()
                self.beep(700, 15)

            # === УПРАВЛЕНИЕ КОВШОМ (КЛАВИШИ 1, 2, 3, 4) ===
            elif ev == '1':
                self.bucket_angle = 10
                self.set_servo_angle(self.pwm_bucket, 10)
                self.beep(800, 15)
            elif ev == '2':
                self.bucket_angle = 45
                self.set_servo_angle(self.pwm_bucket, 45)
                self.beep(1000, 15)
            elif ev == '3':
                self.bucket_angle = 90
                self.set_servo_angle(self.pwm_bucket, 90)
                self.beep(1200, 15)
            elif ev == '4':
                self.bucket_angle = 135
                self.set_servo_angle(self.pwm_bucket, 135)
                self.beep(1400, 15)

            # ДЕМО РЕЖИМ
            elif ev == 'ENTER':
                self.auto_demo_routine()