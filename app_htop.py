# app_htop.py - Системный монитор RobotOS (htop) для RP2350
# Показывает реальные данные: частота, ОЗУ, Flash, SD, температура кристалла,
# загруженные модули Python и нагрузку Python-потока.
import os
import sys
import gc
import time
import machine
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240

REFRESH_MS = 500       # как часто обновлять данные
HIST_LEN   = 55       # длина графика нагрузки (точек)
TABLE_ROWS = 6         # строк в таблице модулей
ROW_H      = 12

C_BG       = 0x0000
C_TEXT     = rgb(204, 204, 204)
C_WHITE    = 0xFFFF
C_GREEN    = rgb(0, 230, 120)
C_CYAN     = rgb(0, 220, 255)
C_YELLOW   = rgb(255, 215, 0)
C_RED      = rgb(255, 80, 80)
C_GRAY     = rgb(140, 150, 170)
C_TITLE_BG = rgb(24, 26, 32)
C_BORDER   = rgb(45, 52, 65)
C_BAR_BG   = rgb(32, 36, 46)
C_HEAD_BG  = rgb(0, 150, 85)


def _fmt_size(used, total):
    """'1.2/3.6G' или '0.3/15.9M' - до 10 символов."""
    if total >= 1073741824:
        return "%.1f/%.1fG" % (used / 1073741824, total / 1073741824)
    return "%.1f/%.1fM" % (used / 1048576, total / 1048576)


class HtopApp:
    def __init__(self, tft, audio, inputs, config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"hour": 20, "minute": 45}

        self.cpu = 0.0
        self.cpu_hist = []
        self.busy_us = 0          # сколько мкс Python-поток был занят за интервал
        self.top = 0              # первая видимая строка таблицы модулей
        self.mods = []

        self.alloc = 0
        self.total = 1
        self.flash = None
        self.sd = None
        self.temp = None

        # Датчик температуры кристалла (внутренний АЦП)
        self.adc = None
        try:
            self.adc = machine.ADC(machine.ADC.CORE_TEMP)
        except Exception:
            try:
                self.adc = machine.ADC(4)
            except Exception:
                self.adc = None

    # ------------------------------------------------------------ сбор данных
    def _fs_usage(self, path):
        try:
            st = os.statvfs(path)
            total = st[0] * st[2]
            free = st[0] * st[3]
            return (total - free, total)
        except Exception:
            return None

    def _read_temp(self):
        if not self.adc:
            return None
        try:
            v = self.adc.read_u16() * 3.3 / 65535
            return 27 - (v - 0.706) / 0.001721
        except Exception:
            return None

    def _update_stats(self):
        gc.collect()
        free = gc.mem_free()
        alloc = gc.mem_alloc()
        self.alloc = alloc
        self.total = free + alloc

        self.flash = self._fs_usage("/")
        sd = self._fs_usage("/sd")
        # Если SD не вставлена, /sd может показывать ту же ФС, что и корень
        if sd and self.flash and sd[1] == self.flash[1]:
            sd = None
        self.sd = sd

        self.temp = self._read_temp()

        mods = []
        for name in list(sys.modules.keys()):
            try:
                n = len(dir(sys.modules[name]))
            except Exception:
                n = 0
            mods.append((name, n))
        mods.sort(key=lambda x: (-x[1], x[0]))
        self.mods = mods

        max_top = max(0, len(mods) - TABLE_ROWS)
        if self.top > max_top:
            self.top = max_top

    # ------------------------------------------------------------ отрисовка
    def _load_color(self, frac):
        if frac < 0.5:
            return C_GREEN
        if frac < 0.8:
            return C_YELLOW
        return C_RED

    def _bar(self, x, y, w, h, frac, color):
        t = self.tft
        frac = max(0.0, min(1.0, frac))
        t.fill_rect(x, y, w, h, C_BAR_BG)
        n = int(w * frac)
        if n > 0:
            t.fill_rect(x, y, n, h, color)
        t.rect(x, y, w, h, C_BORDER)

    def _row(self, y, label, frac, text):
        draw_text(self.tft, label, 6, y, C_CYAN)
        self._bar(40, y + 1, 190, 8, frac, self._load_color(frac))
        draw_text(self.tft, text, 236, y, C_WHITE)

    def _draw(self):
        t = self.tft

        # Шапка окна
        t.fill_rect(0, 0, W, 20, C_TITLE_BG)
        t.line(0, 19, W, 19, C_BORDER)
        t.fill_rect(8, 5, 13, 10, C_BG)
        t.rect(8, 5, 13, 10, rgb(100, 110, 130))
        t.fill_rect(11, 10, 2, 3, C_GREEN)
        t.fill_rect(15, 7, 2, 6, C_YELLOW)
        draw_text(t, "Монитор системы", 26, 6, C_WHITE)
        t.text("Esc", 294, 6, C_WHITE)

        # Поле
        t.fill_rect(0, 20, W, 198, C_BG)

        # Полосы: CPU, ОЗУ, Flash, SD
        self._row(24, "CPU", self.cpu, "%d%%" % int(self.cpu * 100))
        self._row(36, "ОЗУ", self.alloc / self.total,
                  "%d/%dK" % (self.alloc // 1024, self.total // 1024))
        if self.flash:
            self._row(48, "ФЛЭШ", self.flash[0] / self.flash[1],
                      _fmt_size(self.flash[0], self.flash[1]))
        else:
            draw_text(t, "ФЛЭШ  нет данных", 6, 48, C_GRAY)
        if self.sd:
            self._row(60, "SD", self.sd[0] / self.sd[1],
                      _fmt_size(self.sd[0], self.sd[1]))
        else:
            draw_text(t, "SD    карта не найдена", 6, 60, C_GRAY)

        # Строка: частота, температура, аптайм
        mhz = machine.freq() // 1000000
        temp_s = "%dC" % int(self.temp) if self.temp is not None else "n/a"
        up = time.ticks_ms() // 1000
        info = "%dMHz  TEMP %s  UP %02d:%02d:%02d" % (
            mhz, temp_s, up // 3600, (up // 60) % 60, up % 60)
        draw_text(t, info, 6, 74, C_YELLOW)

        # График нагрузки Python-потока (самая новая точка справа)
        gx, gy, gh = 6, 88, 20
        gw = HIST_LEN * 3 + 2
        t.fill_rect(gx, gy, gw, gh + 2, C_BAR_BG)
        t.rect(gx, gy, gw, gh + 2, C_BORDER)
        off = HIST_LEN - len(self.cpu_hist)
        for i, v in enumerate(self.cpu_hist):
            h = int(v * gh)
            if h > 0:
                t.fill_rect(gx + 1 + (off + i) * 3, gy + 1 + gh - h, 2, h,
                            self._load_color(v))
        draw_text(t, "нагрузка CPU", gx + gw + 10, gy + 6, C_GRAY)

        # Таблица модулей (настоящий список sys.modules)
        t.fill_rect(0, 112, W, 12, C_HEAD_BG)
        draw_text(t, "PID МОДУЛЬ               ОБЪЕКТ S", 6, 114, C_BG)

        y = 126
        for idx in range(self.top, min(len(self.mods), self.top + TABLE_ROWS)):
            name, n = self.mods[idx]
            running = (name == "app_htop")
            state = "R" if running else "S"
            line = "%3d %-20s %4d %s" % (idx, name[:20], n, state)
            draw_text(t, line, 6, y, C_GREEN if running else C_TEXT)
            y += ROW_H

        draw_text(t, "Модулей: %d   S: нагрузка" % len(self.mods), 6, 204, C_GRAY)

        # Панель задач
        draw_system_taskbar(t, self.cfg, active_tab="System", tab_icon="htop")

    # ------------------------------------------------------------ цикл
    def _redraw(self):
        t0 = time.ticks_us()
        self._draw()
        self.tft.show()
        self.busy_us += time.ticks_diff(time.ticks_us(), t0)

    def _refresh(self, interval_ms):
        if interval_ms > 0:
            self.cpu = min(1.0, self.busy_us / (interval_ms * 1000.0))
            self.cpu_hist.append(self.cpu)
            if len(self.cpu_hist) > HIST_LEN:
                self.cpu_hist.pop(0)
        self.busy_us = 0
        t0 = time.ticks_us()
        self._update_stats()
        self._draw()
        self.tft.show()
        self.busy_us += time.ticks_diff(time.ticks_us(), t0)

    def _stress(self):
        """Секунду крутим пустой цикл, чтобы увидеть рост нагрузки."""
        t0 = time.ticks_us()
        x = 0
        while time.ticks_diff(time.ticks_us(), t0) < 1000000:
            x += 1
        self.busy_us += time.ticks_diff(time.ticks_us(), t0)

    def run(self):
        self._refresh(0)
        last = time.ticks_ms()

        while True:
            now = time.ticks_ms()
            if time.ticks_diff(now, last) >= REFRESH_MS:
                self._refresh(time.ticks_diff(now, last))
                last = now

            ev = self.inputs.get_event()
            if not ev:
                time.sleep_ms(20)
                continue

            if ev in ['ESC', 'BACK']:
                return
            elif ev == 'UP':
                if self.top > 0:
                    self.top -= 1
                    self._redraw()
            elif ev == 'DOWN':
                if self.top < max(0, len(self.mods) - TABLE_ROWS):
                    self.top += 1
                    self._redraw()
            elif ev in ['s', 'S']:
                self._stress()
