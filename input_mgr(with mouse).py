# input_mgr.py - Единый диспетчер: Клавиатура + Пульт + Мышь PS/2
import time
from machine import Pin
from utime import ticks_us, ticks_diff
import ps2

IR_MAP = {
    0x31: 'UP', 0xA5: 'DOWN', 0x11: 'LEFT', 0xB5: 'RIGHT',
    0x39: 'ENTER', 0x2D: 'BACK', 0x1B: 'BACK',
}

class InputManager:
    def __init__(self, kbd_clk=14, kbd_data=15, ir_pin=3, mouse_clk=24, mouse_data=25):
        self.kbd = ps2.PS2Keyboard(clk_pin=kbd_clk, data_pin=kbd_data)

        self.ir_pin = Pin(ir_pin, Pin.IN, Pin.PULL_UP)
        self.ir_event = None
        self.ir_times = []
        self.ir_last_edge = ticks_us()
        self.ir_pin.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self._ir_irq)

        # Мышь PS/2 на ножках 18 и 22 платы (GP24 и GP25)
        self.mouse = None
        try:
            import ps2_mouse
            self.mouse = ps2_mouse.PS2Mouse(clk_pin=mouse_clk, data_pin=mouse_data)
        except Exception as e:
            print("Мышь не подключена:", e)

    def _ir_irq(self, pin):
        now = ticks_us()
        dt = ticks_diff(now, self.ir_last_edge)
        self.ir_last_edge = now
        if dt > 10000:
            if len(self.ir_times) >= 66:
                val = 0
                for i in range(1, 65, 2):
                    val >>= 1
                    if self.ir_times[i] > 1100: val |= 0x80000000
                cmd = (val >> 16) & 0xFF
                action = IR_MAP.get(cmd)
                if action: self.ir_event = action
            self.ir_times = []
        else:
            self.ir_times.append(dt)

    def get_event(self):
        # 1. Мышь: Левый и Правый клик
        if self.mouse and self.mouse.present:
            if self.mouse.get_left_click():
                return 'MOUSE_LCLICK'
            if self.mouse.get_right_click():
                return 'MOUSE_RCLICK'

        # 2. Пульт
        if self.ir_event:
            ev = self.ir_event
            self.ir_event = None
            return ev

        # 3. Клавиатура
        k = self.kbd.get_key()
        if k:
            if k == 'ESC': return 'BACK'
            return k

        return None