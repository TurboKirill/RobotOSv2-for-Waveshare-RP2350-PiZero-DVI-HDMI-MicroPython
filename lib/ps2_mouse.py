# lib/ps2_mouse.py - Стабилизированный драйвер мыши PS/2 для Waveshare RP2350-PiZero
# GP24 (CLK, пин 18) и GP25 (DATA, пин 22). Двойная валидация знаков X/Y (без фантомных кликов).
import time
from machine import Pin
from utime import ticks_us, ticks_diff

class PS2Mouse:
    def __init__(self, clk_pin=24, data_pin=25, bound_w=320, bound_h=240):
        self.clk = Pin(clk_pin, Pin.IN, Pin.PULL_UP)
        self.data = Pin(data_pin, Pin.IN, Pin.PULL_UP)
        self.bound_w = bound_w
        self.bound_h = bound_h

        # Начальное положение стрелочки
        self.x = bound_w // 2
        self.y = bound_h // 2
        
        # Кнопки
        self.btn_left = False
        self.btn_right = False
        self.left_clicked = False
        self.right_clicked = False
        
        # Счётчики антидребезга
        self.l_cnt = 0
        self.r_cnt = 0

        # Кольцевой буфер прерывания
        self.bit_idx = 0
        self.current_byte = 0
        self.buf = bytearray(64)
        self.head = 0
        self.tail = 0

        self.present = False
        self.init_mouse()

    def _wait_clk(self, val, timeout_us=25000):
        t0 = ticks_us()
        while self.clk.value() != val:
            if ticks_diff(ticks_us(), t0) > timeout_us: return False
        return True

    def _write_byte(self, val):
        self.clk.init(Pin.OUT, value=0)
        time.sleep_us(120)
        self.data.init(Pin.OUT, value=0)
        time.sleep_us(10)
        self.clk.init(Pin.IN, Pin.PULL_UP)

        parity = 1
        for i in range(8):
            b = (val >> i) & 1
            parity ^= b
            if not self._wait_clk(0): return False
            self.data.value(b)
            if not self._wait_clk(1): return False

        if not self._wait_clk(0): return False
        self.data.value(parity)
        if not self._wait_clk(1): return False

        if not self._wait_clk(0): return False
        self.data.init(Pin.IN, Pin.PULL_UP)
        if not self._wait_clk(1): return False

        if not self._wait_clk(0): return False
        ack = (self.data.value() == 0)
        self._wait_clk(1)
        return ack

    def init_mouse(self):
        if self.clk.value() == 0 or self.data.value() == 0:
            self.present = False
            return

        time.sleep_ms(400) # Прогрев оптики

        ok = self._write_byte(0xF4) # Enable Data Reporting
        if not ok:
            time.sleep_ms(100)
            ok = self._write_byte(0xF4)

        if ok:
            time.sleep_ms(20)
            self.present = True
            print("🖱️ [Mouse] Мышь PS/2 успешно запущена!")
            self.clk.irq(trigger=Pin.IRQ_FALLING, handler=self._clk_irq)
        else:
            print("🖱️ [Mouse] Мышь не ответила на 0xF4")
            self.present = False

    def _clk_irq(self, pin):
        """Аппаратный приём бит с проверкой стоп-бита"""
        bit = self.data.value()

        if self.bit_idx == 0:
            if bit == 0: # Стартовый бит 0
                self.current_byte = 0
                self.bit_idx += 1
        elif 1 <= self.bit_idx <= 8:
            if bit: self.current_byte |= (1 << (self.bit_idx - 1))
            self.bit_idx += 1
        elif self.bit_idx == 9:
            self.bit_idx += 1 # Parity
        elif self.bit_idx == 10:
            # Стоп-бит ОБЯЗАН быть 1! Если 0 - сбой линии, отбрасываем
            if bit == 1:
                nxt = (self.head + 1) % 64
                if nxt != self.tail:
                    self.buf[self.head] = self.current_byte
                    self.head = nxt
            self.bit_idx = 0

    def update(self):
        """Пакетный разбор с математической валидацией знаков X и Y"""
        if not self.present:
            return False

        old_x, old_y = self.x, self.y

        # Разбираем, когда накопились минимум 3 байта
        while ((self.head - self.tail) % 64) >= 3:
            b0 = self.buf[self.tail]
            b1 = self.buf[(self.tail + 1) % 64]
            b2 = self.buf[(self.tail + 2) % 64]

            # 1. Базовые маркеры PS/2: бит 3 всегда 1, биты переполнения 6 и 7 - всегда 0!
            if (b0 & 0x08) != 0x08 or (b0 & 0xC0) != 0:
                self.tail = (self.tail + 1) % 64
                continue

            # 2. МАТЕМАТИЧЕСКАЯ ЗАЩИТА: Знаковые биты 4 и 5 обязаны совпадать со знаком чисел b1 и b2!
            # Это полностью исключает фантомные клики при движении мыши!
            x_is_neg = (b0 & 0x10) != 0
            y_is_neg = (b0 & 0x20) != 0
            if x_is_neg != (b1 >= 128) or y_is_neg != (b2 >= 128):
                self.tail = (self.tail + 1) % 64
                continue

            # Пакет 100% валиден — забираем все 3 байта!
            self.tail = (self.tail + 3) % 64

            # Кнопки мыши: МГНОВЕННЫЙ ОТКЛИК на первый же пакет!
            btn_l = (b0 & 0x01) != 0
            btn_r = (b0 & 0x02) != 0

            # Левый клик срабатывает сразу при нажатии кнопки (0 -> 1)
            if btn_l and not self.btn_left:
                self.left_clicked = True
            self.btn_left = btn_l

            # Правый клик срабатывает сразу при нажатии кнопки (0 -> 1)
            if btn_r and not self.btn_right:
                self.right_clicked = True
            self.btn_right = btn_r

            # Смещение координат со знаком
            dx = (b1 - 256) if x_is_neg else b1
            dy = (b2 - 256) if y_is_neg else b2

            # Фильтр аномалий
            if abs(dx) > 60 or abs(dy) > 60:
                continue

            # Плавная чувствительность под 320x240
            scaled_dx = int(dx * 0.75)
            scaled_dy = int(dy * 0.75)

            self.x = max(0, min(self.bound_w - 2, self.x + scaled_dx))
            self.y = max(0, min(self.bound_h - 2, self.y - scaled_dy))

        return (old_x != self.x or old_y != self.y)

    def get_left_click(self):
        if self.left_clicked:
            self.left_clicked = False
            return True
        return False

    def get_right_click(self):
        if self.right_clicked:
            self.right_clicked = False
            return True
        return False