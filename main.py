# main.py - Точка входа PicoOS (DVI 320x240)
import time
import gc
from machine import Pin, I2S
import bios
import input_mgr
from dvi_display import DVIDisplay

print("Запуск системы PicoOS на DVI...")

# 1. Экран DVI 320x240
tft = DVIDisplay(bpp=16)

# 2. Звук I2S
audio = I2S(
    0,
    sck=Pin(10), ws=Pin(11), sd=Pin(12),
    mode=I2S.TX, bits=16, format=I2S.MONO,
    rate=22050, ibuf=1024
)

# 3. BIOS POST заставка
boot = bios.BootLoader(tft, audio)
boot.run()

# ОСВОБОЖДАЕМ ПАМЯТЬ: удаляем заставку BIOS перед загрузкой интерфейса
del boot
gc.collect()

# 4. Диспетчер ввода (Клавиатура + Пульт)
inputs = input_mgr.InputManager(kbd_clk=14, kbd_data=15, ir_pin=3)

# 5. Загрузка и старт GUI
import gui
os_gui = gui.RobotOS_GUI(tft, audio, inputs)
os_gui.run()