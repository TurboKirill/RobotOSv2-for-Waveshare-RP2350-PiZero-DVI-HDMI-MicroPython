# test_mouse.py - Экспресс-тест мышки под распиновку Waveshare RP2350-PiZero
# CLK = Пин 18 (GPIO 24), DATA = Пин 22 (GPIO 25), GND = Пин 20, 5V = Пин 2
import time
from machine import Pin
from utime import ticks_us, ticks_diff

print("=== ТЕСТ МЫШКИ (Пин 18: GP24-CLK, Пин 22: GP25-DATA) ===")

clk = Pin(24, Pin.IN, Pin.PULL_UP)
data = Pin(25, Pin.IN, Pin.PULL_UP)

# 1. Проверяем подтяжку линий
time.sleep_ms(200)
c_val = clk.value()
d_val = data.value()
print(f"Состояние линий: CLK={c_val}, DATA={d_val}")

if c_val == 0 or d_val == 0:
    print("❌ Линия прижата к земле (0)! Проверь ножки 18 и 22.")
else:
    print("✅ Линии свободны (1). Начинаем опрос...")

def wait_clk(val, timeout=25000):
    t0 = ticks_us()
    while clk.value() != val:
        if ticks_diff(ticks_us(), t0) > timeout:
            return False
    return True

def send_byte(val):
    clk.init(Pin.OUT, value=0)
    time.sleep_us(120)
    data.init(Pin.OUT, value=0)
    time.sleep_us(10)
    clk.init(Pin.IN, Pin.PULL_UP)

    parity = 1
    for i in range(8):
        b = (val >> i) & 1
        parity ^= b
        if not wait_clk(0): return False
        data.value(b)
        if not wait_clk(1): return False

    if not wait_clk(0): return False
    data.value(parity)
    if not wait_clk(1): return False

    if not wait_clk(0): return False
    data.init(Pin.IN, Pin.PULL_UP)
    if not wait_clk(1): return False

    if not wait_clk(0): return False
    ack = (data.value() == 0)
    wait_clk(1)
    return ack

print("Посылаем команду мыши 0xF4 (Enable Data)...")
time.sleep_ms(400) # пауза на прогрев оптики

if send_byte(0xF4):
    print("🎉 УРА! МЫШЬ ОТВЕТИЛА (ACK)! Мышь жива и на связи!")
    print("Подвигай мышь или нажимай кнопки:")
    
    while True:
        if clk.value() == 0:
            val = 0
            for i in range(8):
                wait_clk(0)
                if data.value(): val |= (1 << i)
                wait_clk(1)
            wait_clk(0); wait_clk(1) # parity
            wait_clk(0); wait_clk(1) # stop
            print(f"Сигнал от мыши: {hex(val)}")
        time.sleep_ms(5)
else:
    print("❌ Мышь не ответила. Если оптика горит — поменяй местами ножки 18 и 22!")