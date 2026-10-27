# app_weather.py - Климат и погода RobotOS (DVI 320x240)
# Слева: Датчики BH1750 (люксы) + DHT22 (температура и влажность)
# Справа: Интерактивные мини-глазки робота с реакцией на климат
import time
import math
import struct
import gc
import dht
from machine import Pin, I2C
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240
TB_H = 22
WIN_H = H - TB_H  # 218px

# Пин датчика DHT22 (1-Wire)
DHT_PIN = 13

# Палитра цветов
C_BG        = rgb(20, 24, 34)       # Тёмно-синий фон
C_HEADER    = rgb(28, 32, 44)       # Шапка окна
C_CARD      = rgb(26, 32, 46)       # Карточки
C_BORDER    = rgb(48, 56, 76)       # Рамки
C_WHITE     = 0xFFFF
C_GRAY      = rgb(140, 150, 170)
C_DARK_GRAY = rgb(90, 100, 120)
C_COLD      = rgb(0, 210, 255)      # Неоново-бирюзовый (Холод)
C_COMFORT   = rgb(0, 230, 120)      # Зелёный (Комфорт)
C_HOT       = rgb(255, 70, 70)      # Красный (Жара)
C_SUN       = rgb(255, 200, 30)      # Золотисто-солнечный
C_ACCENT    = rgb(0, 160, 255)

class WeatherApp:
    def __init__(self, tft, audio, inputs, config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False, "hour": 20, "minute": 45}

        # 1. Датчик освещённости BH1750 (I2C0: GP4 SDA, GP5 SCL)
        self.i2c = None
        self.has_bh1750 = False
        try:
            self.i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100000)
            self.i2c.writeto(0x23, b'\x01') # Power ON
            self.i2c.writeto(0x23, b'\x10') # High-Res Mode
            self.has_bh1750 = True
        except:
            pass

        # 2. Датчик температуры и влажности DHT22 (GP13)
        self.dht_sensor = None
        self.has_dht = False
        self.last_dht_read = 0
        try:
            self.dht_sensor = dht.DHT22(Pin(DHT_PIN))
            self.has_dht = True
        except:
            pass

        # Базовые значения
        self.temp = 23.5
        self.humidity = 45.0

    def read_lux(self):
        """Замер освещенности в Люксах с датчика BH1750"""
        if self.has_bh1750:
            try:
                data = self.i2c.readfrom(0x23, 2)
                return int((data[0] << 8 | data[1]) / 1.2)
            except:
                pass
        return 280

    def read_dht(self):
        """Опрос датчика DHT22 не чаще 1 раза в 2 секунды"""
        if not self.has_dht:
            return
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_dht_read) >= 2000:
            self.last_dht_read = now
            try:
                self.dht_sensor.measure()
                self.temp = self.dht_sensor.temperature()
                self.humidity = self.dht_sensor.humidity()
            except:
                pass

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

    def draw_round_rect(self, x, y, w, h, r, color):
        """Скругление углов для мини-глазок робота"""
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

    def draw_robot_reaction(self, state, frame):
        """Отрисовка реакций живых мини-глазок робота в правой карточке"""
        t = self.tft
        bx, by, bw, bh = 196, 24, 116, 160
        t.fill_rect(bx, by, bw, bh, C_CARD)

        cx = bx + bw // 2
        cy = by + 60
        ew, eh = 30, 42
        space = 14
        lx = cx - ew // 2 - space // 2
        rx = cx + ew // 2 + space // 2

        draw_text(t, "РЕАКЦИЯ", bx + 28, by + 10, C_GRAY)

        # 1. ХОЛОД (Дрожащие синие глазки)
        if state == "COLD":
            col = C_COLD
            t.rect(bx, by, bw, bh, col)
            shiver = (frame % 2) * 2 - 1
            self.draw_round_rect(lx - ew // 2 + shiver, cy - eh // 2, ew, eh, 8, col)
            self.draw_round_rect(rx - ew // 2 + shiver, cy - eh // 2, ew, eh, 8, col)
            draw_text(t, "БРР-Р!", bx + 36, by + 116, col)
            draw_text(t, "ХОЛОДНО", bx + 28, by + 132, col)

        # 2. ЖАРА (Красные сощуренные глазки)
        elif state == "HOT":
            col = C_HOT
            t.rect(bx, by, bw, bh, col)
            self.draw_round_rect(lx - ew // 2, cy - 8, ew, 16, 4, col)
            self.draw_round_rect(rx - ew // 2, cy - 8, ew, 16, 4, col)
            draw_text(t, "ОХ, ЖАРКО!", bx + 20, by + 116, col)
            draw_text(t, "ПЕРЕГРЕВ", bx + 26, by + 132, col)

        # 3. КОМФОРТ (Счастливые глазки с улыбкой)
        else:
            col = C_COMFORT
            t.rect(bx, by, bw, bh, col)
            self.draw_round_rect(lx - ew // 2, cy - eh // 2, ew, eh, 8, col)
            self.draw_round_rect(rx - ew // 2, cy - eh // 2, ew, eh, 8, col)
            # Прищур улыбки снизу
            t.fill_rect(lx - ew // 2, cy + 3, ew, 20, C_CARD)
            t.fill_rect(rx - ew // 2, cy + 3, ew, 20, C_CARD)
            draw_text(t, "ОТЛИЧНО!", bx + 24, by + 116, col)
            draw_text(t, "КОМФОРТНО", bx + 22, by + 132, col)

    def draw_screen(self, lux, state, status_txt, status_col, l_txt, l_icon, frame):
        t = self.tft

        # 1. Шапка окна (Y = 0..19)
        t.fill_rect(0, 0, W, 20, C_HEADER)
        t.line(0, 19, W, 19, C_BORDER)
        draw_text(t, "Погода и климат", 10, 6, C_WHITE)
        t.text("Esc", 294, 6, C_WHITE)

        # 2. Фон рабочей области
        t.fill_rect(0, 20, W, 198, C_BG)

        # ЛЕВАЯ КОЛОНКА (Датчики)
        # Карточка 1: Температура и Влажность (DHT22) (Y = 24..98)
        t.fill_rect(10, 24, 180, 76, C_CARD)
        t.rect(10, 24, 180, 76, status_col)
        draw_text(t, "КЛИМАТ ПОМЕЩЕНИЯ", 18, 30, C_WHITE)

        temp_str = f"{self.temp:+.1f} °C"
        draw_text(t, temp_str, 18, 48, status_col)

        hum_str = f"Влажность: {self.humidity:.0f}%"
        draw_text(t, hum_str, 18, 64, C_WHITE)
        draw_text(t, status_txt, 18, 80, status_col)

        # Карточка 2: Датчик освещения (BH1750) (Y = 104..184)
        t.fill_rect(10, 104, 180, 80, C_CARD)
        t.rect(10, 104, 180, 80, C_BORDER)
        draw_text(t, "ОСВЕЩЕНИЕ (BH1750)", 18, 110, C_WHITE)

        lux_str = f"Свет: {lux} Люкс"
        draw_text(t, lux_str, 18, 126, C_SUN)
        draw_text(t, f"{l_icon} {l_txt}", 18, 142, C_WHITE)

        # Шкала освещенности
        t.rect(18, 160, 164, 8, C_BORDER)
        fill_w = min(160, max(2, int(160 * (lux / 1000.0))))
        t.fill_rect(20, 162, fill_w, 4, C_SUN)

        # ПРАВАЯ КОЛОНКА (Мини-глазки робота)
        self.draw_robot_reaction(state, frame)

        # Нижняя подсказка
        if not self.has_dht:
            draw_text(t, "ВВЕРХ/ВНИЗ: Тест темп.   ESC: Выход", 12, 198, C_DARK_GRAY)
        else:
            draw_text(t, "Датчики активны            ESC: Выход", 12, 198, C_DARK_GRAY)

        # 3. Панель задач RobotOS
        draw_system_taskbar(t, self.cfg, active_tab="Погода", tab_icon="weather")

        t.show()

    def run(self):
        frame = 0

        while True:
            # Опрос сенсоров
            lux = self.read_lux()
            self.read_dht()

            # Анализ температуры
            if self.temp < 18.0:
                state = "COLD"
                status_txt = "Холодно"
                status_col = C_COLD
            elif self.temp > 26.0:
                state = "HOT"
                status_txt = "Жарко"
                status_col = C_HOT
            else:
                state = "COMFORT"
                status_txt = "Комфортно"
                status_col = C_COMFORT

            # Градация люксов
            if lux < 40:     l_txt, l_icon = "ТЕМНОТА",   "[НОЧЬ]"
            elif lux < 250:  l_txt, l_icon = "КОМНАТА",   "[ЛАМПА]"
            elif lux < 750:  l_txt, l_icon = "ДНЕВНОЙ",   "[ОКНО]"
            else:            l_txt, l_icon = "ЯРКОЕ",     "[СОЛНЦЕ]"

            # Отрисовка
            self.draw_screen(lux, state, status_txt, status_col, l_txt, l_icon, frame)

            # Опрос клавиш
            for _ in range(8):
                ev = self.inputs.get_event()
                if ev:
                    if ev in ['BACK', 'ESC']:
                        self.beep(600, 25)
                        return
                    # Ручная регулировка температуры стрелками, если DHT22 не подключен
                    elif ev == 'UP' and not self.has_dht:
                        self.temp = min(38.0, round(self.temp + 1.0, 1))
                        self.beep(1200, 10); break
                    elif ev == 'DOWN' and not self.has_dht:
                        self.temp = max(10.0, round(self.temp - 1.0, 1))
                        self.beep(800, 10); break
                    elif ev == 'ENTER':
                        self.beep(1500, 20)
                time.sleep_ms(35)

            frame += 1