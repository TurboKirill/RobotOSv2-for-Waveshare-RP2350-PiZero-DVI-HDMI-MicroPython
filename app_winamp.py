# app_winamp.py - Полная версия легендарного Winamp для RobotOS (DVI 320x240)
# Эквалайзер (IIR Viper), Плейлист, Обзор папок, VU-метр, Плавный фейд
import os
import time
import math
import struct
import micropython
from array import array
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240
UI_MS = 250            # Оптимальная частота обновления UI (без заиканий)
CHUNK = 2048           # Размер звукового буфера
PANEL_Y = 98           # Верх нижней панели (EQ / PL / Обзор)
ROWS = 8

C_BG     = 0x0000
C_PANEL  = rgb(22, 24, 34)
C_FRAME  = rgb(70, 76, 96)
C_LCD    = rgb(6, 12, 8)
C_GREEN  = rgb(0, 230, 0)
C_DGREEN = rgb(0, 80, 0)
C_WHITE  = 0xFFFF
C_GRAY   = rgb(140, 150, 170)
C_CYAN   = rgb(0, 220, 255)
C_YELLOW = rgb(255, 215, 0)
C_RED    = rgb(255, 80, 80)
C_SEL    = rgb(0, 60, 140)
C_TITLE  = rgb(70, 60, 110)
C_STRIPE = rgb(120, 110, 170)
C_BTN    = rgb(46, 50, 66)
C_BTN_ON = rgb(20, 70, 40)

ACT = ('prev', 'play', 'pause', 'stop', 'next', 'back', 'fwd', 'eject', 'eq', 'pl')

SEGR = {'a': (1, 0, 8, 2), 'b': (8, 1, 2, 8), 'c': (8, 9, 2, 8), 'd': (1, 16, 8, 2),
        'e': (0, 9, 2, 8), 'f': (0, 1, 2, 8), 'g': (1, 8, 8, 2)}
SEGS = ("abcdef", "bc", "abdeg", "abcdg", "bcfg", "acdfg", "acdefg", "abc", "abcdefg", "abcdfg")

# ================= МАШИННЫЙ КОД: эквалайзер + громкость + уровень =================
@micropython.viper
def process(buf: ptr8, n: int, p: ptr32) -> int:
    gl = int(p[0])
    gm = int(p[1])
    gh = int(p[2])
    vol = int(p[3])
    ch = int(p[4])
    k1 = int(p[5])
    k2 = int(p[6])
    byp = int(p[7])
    i = 0
    c = 0
    pl = 0
    pr = 0
    while i < n:
        s = int(buf[i]) | (int(buf[i + 1]) << 8)
        if s >= 32768:
            s -= 65536
        if byp == 0:
            o = 8 + c * 2
            a = int(p[o])
            b = int(p[o + 1])
            a += ((s - a) * k1) >> 15
            b += ((s - b) * k2) >> 15
            p[o] = a
            p[o + 1] = b
            s = (a * gl + (b - a) * gm + (s - b) * gh) >> 8
        s = (s * vol) >> 8
        if s > 32767:
            s = 32767
        elif s < -32768:
            s = -32768
        m = s
        if m < 0:
            m = -m
        if c == 0:
            if m > pl: pl = m
        else:
            if m > pr: pr = m
        u = s & 0xFFFF
        buf[i] = u & 0xFF
        buf[i + 1] = (u >> 8) & 0xFF
        i += 2
        if ch == 2:
            c = 1 - c
    return pl | (pr << 16)


def show_name(nb):
    if isinstance(nb, str): return nb
    try: return nb.decode("utf-8")
    except Exception: return "".join(chr(b) if 32 <= b < 127 else "?" for b in nb)

def list_dir(dirb):
    out = []
    try:
        for e in os.ilistdir(dirb):
            n = e[0]
            if isinstance(n, str): n = n.encode()
            if n in (b".", b".."): continue
            out.append((n, e[1] == 0x4000))
    except Exception:
        pass
    return out

def join_path(d, n):
    if d.endswith(b"/"): return d + n
    return d + b"/" + n

def is_wav(nb):
    return nb.lower().endswith(b".wav") and not nb.startswith(b".")

def wav_info(path):
    try:
        fsz = os.stat(path)[6]
        with open(path, "rb") as f:
            h = f.read(12)
            if len(h) < 12 or h[0:4] != b"RIFF" or h[8:12] != b"WAVE":
                return None
            rate = ch = bits = fmt = 0
            while True:
                ck = f.read(8)
                if len(ck) < 8: return None
                size = struct.unpack("<I", ck[4:8])[0]
                cid = ck[0:4]
                if cid == b"fmt ":
                    d = f.read(size)
                    fmt, ch, rate, _, _, bits = struct.unpack("<HHIIHH", d[:16])
                    if size & 1: f.read(1)
                elif cid == b"data":
                    off = f.tell()
                    if fmt not in (1, 0xFFFE): return None
                    return (rate, ch, bits, off, min(size, fsz - off))
                else:
                    f.seek(size + (size & 1), 1)
    except Exception:
        return None

def db_gain(db):
    return int(256 * math.pow(10, db / 20))

def tri_right(t, x, y, h, col):
    hh = h // 2
    for i in range(h):
        w = hh - abs(i - hh)
        t.fill_rect(x, y + i, w + 1, 1, col)

def tri_left(t, x, y, h, col):
    hh = h // 2
    for i in range(h):
        w = hh - abs(i - hh)
        t.fill_rect(x + hh - w, y + i, w + 1, 1, col)

def tri_up(t, cx, y, rows, col):
    for i in range(rows):
        t.fill_rect(cx - i, y + i, 2 * i + 1, 1, col)

def seg_digit(t, x, y, d, col):
    for s in SEGS[d]:
        r = SEGR[s]
        t.fill_rect(x + r[0], y + r[1], r[2], r[3], col)


class WinampApp:
    def __init__(self, tft, audio, inputs, config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"hour": 20, "minute": 45}

        self.tracks = []
        self.idx = 0
        self.state = 'stop'
        self.volume = 80
        self.focus = 1
        self.panel = None

        self.f = None
        self.info = None
        self.left = 0
        self.pos = 0
        self.byterate = 44100
        self.buf = bytearray(CHUNK)
        self.mv = memoryview(self.buf)
        self.silence = bytearray(1024)
        self.infos = {}
        self.msg = ""
        self.msg_until = 0

        self.gain = 100
        self.fade = 0
        self.pending = None

        self.eq_on = False
        self.eq_db = [0, 0, 0, 0]
        self.eq_sel = 1
        self.p = array('i', [256, 256, 256, 256, 2, 2255, 18840, 1, 0, 0, 0, 0])

        self.vu = [0] * 10
        self.vl = 0
        self.vr = 0
        self.marq = 0
        self.tick = 0
        self.last_ui = time.ticks_ms()

        self.pl_cur = 0
        self.pl_top = 0
        self.br_dir = b"/sd"
        self.br_items = []
        self.br_cur = 0
        self.br_top = 0

    def scan_music(self):
        found = []
        seen = set()
        for d in (b"/sd/wav", b"/sd/WAV", b"/sd"):
            for n, isd in list_dir(d):
                if not isd and is_wav(n):
                    full = join_path(d, n)
                    low = show_name(full).lower()
                    if low not in seen:
                        seen.add(low)
                        found.append(full)
        found.sort(key=lambda x: show_name(x).lower())
        self.tracks = found

    def get_info(self, path):
        r = self.infos.get(path, 0)
        if r == 0:
            r = wav_info(path)
            if len(self.infos) > 64: self.infos.clear()
            self.infos[path] = r
        return r

    def track_name(self, path):
        n = show_name(path.split(b"/")[-1])
        if n.lower().endswith(".wav"): n = n[:-4]
        return n

    def dur_str(self, path):
        inf = self.get_info(path)
        if not inf or not inf[0]: return "--:--"
        sec = inf[4] // (inf[0] * inf[1] * (inf[2] // 8))
        return "%d:%02d" % (sec // 60, sec % 60)

    def say(self, text, ms=3000):
        self.msg = text
        self.msg_until = time.ticks_add(time.ticks_ms(), ms)

    def close_file(self):
        if self.f:
            try: self.f.close()
            except Exception: pass
        self.f = None
        self.info = None

    def set_filters(self, rate):
        self.p[5] = int((1 - math.exp(-2 * math.pi * 250 / rate)) * 32768)
        self.p[6] = int((1 - math.exp(-2 * math.pi * 3000 / rate)) * 32768)

    def sync_eq(self):
        d = self.eq_db
        self.p[0] = db_gain(d[1])
        self.p[1] = db_gain(d[2])
        self.p[2] = db_gain(d[3])
        self.p[7] = 0 if self.eq_on else 1

    def load(self, i):
        self.close_file()
        self.idx = i
        path = self.tracks[i]
        inf = self.get_info(path)
        if not inf or inf[2] != 16 or inf[1] not in (1, 2) or inf[0] < 8000:
            self.say("Нужен WAV 16 бит: " + self.track_name(path)[:14])
            return False
        try:
            self.f = open(path, "rb")
            self.f.seek(inf[3])
        except Exception as e:
            self.say("Ошибка файла")
            self.f = None
            return False
        self.info = inf
        self.left = inf[4]
        self.pos = 0
        self.byterate = inf[0] * inf[1] * 2
        self.p[4] = inf[1]
        for k in (8, 9, 10, 11): self.p[k] = 0
        self.set_filters(inf[0])
        self.sync_eq()
        self.marq = 0
        return True

    def start_track(self, i):
        n = len(self.tracks)
        for _ in range(n):
            if self.load(i):
                self.state = 'play'
                self.gain = 0
                self.fade = 1
                return True
            i = (i + 1) % n
        self.state = 'stop'
        return False

    def switch(self, i):
        if not self.tracks: return
        i %= len(self.tracks)
        if self.state == 'play' and self.f:
            self.pending = i
            self.fade = -1
        elif self.state == 'pause':
            self.load(i)
        else:
            self.idx = i
            self.start_track(i)

    def track_end(self):
        n = len(self.tracks)
        self.start_track((self.idx + 1) % n)

    def seek(self, sec):
        if not self.f or not self.info or self.fade < 0: return
        fr = 2 * self.info[1]
        np = self.pos + sec * self.byterate
        np = max(0, min(self.info[4] - fr * 2, np))
        np -= np % fr
        self.f.seek(self.info[3] + np)
        self.pos = np
        self.left = self.info[4] - np
        for k in (8, 9, 10, 11): self.p[k] = 0
        self.gain = 0
        self.fade = 1

    def pump(self):
        n = min(CHUNK, self.left)
        if n > 0:
            n = self.f.readinto(self.mv[:n])
        fr = 2 * self.info[1]
        if not n or n < fr:
            self.track_end()
            return
        n -= n % fr
        self.left -= n
        self.pos += n

        pre = db_gain(self.eq_db[0]) if self.eq_on else 256
        self.p[3] = (self.volume * 256 // 100) * self.gain // 100 * pre // 256
        pk = process(self.buf, n, self.p)
        self.vl = pk & 0xFFFF
        self.vr = pk >> 16
        self.audio.write(self.mv[:n])

        if self.fade < 0:
            self.gain -= 25
            if self.gain <= 0:
                self.gain = 0
                tgt = self.pending
                self.pending = None
                self.fade = 0
                if tgt is not None: self.start_track(tgt)
        elif self.fade > 0:
            self.gain += 20
            if self.gain >= 100:
                self.gain = 100
                self.fade = 0

    def do_action(self, act):
        if act == 'prev': self.switch(self.idx - 1)
        elif act == 'next': self.switch(self.idx + 1)
        elif act == 'play':
            if not self.tracks: self.open_panel('BR')
            elif self.state == 'stop': self.start_track(self.idx)
            elif self.state == 'pause':
                self.state = 'play'
                self.gain = 0
                self.fade = 1
        elif act == 'pause':
            if self.state == 'play': self.state = 'pause'
            elif self.state == 'pause':
                self.state = 'play'
                self.gain = 0
                self.fade = 1
        elif act == 'stop':
            self.state = 'stop'
            self.fade = 0
            self.pending = None
            self.close_file()
            self.pos = 0
        elif act == 'back': self.seek(-10)
        elif act == 'fwd': self.seek(10)
        elif act == 'eject': self.open_panel('BR')
        elif act == 'eq': self.open_panel('EQ')
        elif act == 'pl': self.open_panel('PL')

    def open_panel(self, name):
        if self.panel == name:
            self.panel = None
        else:
            self.panel = name
            if name == 'PL':
                self.pl_cur = self.idx if self.idx < len(self.tracks) else 0
                self.pl_top = max(0, self.pl_cur - ROWS + 1) if self.pl_cur >= ROWS else 0
            elif name == 'BR':
                try: os.stat(self.br_dir)
                except Exception: self.br_dir = b"/"
                self.br_build()
        self.redraw_all()

    def br_build(self):
        d = self.br_dir
        ents = list_dir(d)
        wavs = sorted([n for n, isd in ents if not isd and is_wav(n)], key=lambda x: show_name(x).lower())
        dirs = sorted([n for n, isd in ents if isd], key=lambda x: show_name(x).lower())
        items = []
        if d != b"/": items.append(("..", None, 'up'))
        if wavs: items.append(("[ИГРАТЬ ВСЕ: %d]" % len(wavs), None, 'all'))
        for n in dirs: items.append(("[" + show_name(n) + "]", n, 'dir'))
        for n in wavs: items.append((show_name(n), n, 'file'))
        self.br_items = items
        self.br_cur = 1 if (len(items) > 1 and items[0][2] == 'up') else 0
        self.br_top = 0

    @staticmethod
    def _top(cur, top):
        if cur < top: return cur
        if cur >= top + ROWS: return cur - ROWS + 1
        return top

    def select(self, i):
        if self.state == 'pause': self.state = 'play'
        self.switch(i)

    def key_pl(self, ev):
        n = len(self.tracks)
        if not n: return
        if ev == 'UP': self.pl_cur = (self.pl_cur - 1) % n
        elif ev == 'DOWN': self.pl_cur = (self.pl_cur + 1) % n
        elif ev == 'ENTER': self.select(self.pl_cur)
        self.pl_top = self._top(self.pl_cur, self.pl_top)
        self.draw_panel()
        self.tft.show(wait=False)

    def key_eq(self, ev):
        if ev == 'LEFT': self.eq_sel = (self.eq_sel - 1) % 4
        elif ev == 'RIGHT': self.eq_sel = (self.eq_sel + 1) % 4
        elif ev == 'UP':
            self.eq_db[self.eq_sel] = min(12, self.eq_db[self.eq_sel] + 2)
            self.eq_on = True
        elif ev == 'DOWN':
            self.eq_db[self.eq_sel] = max(-12, self.eq_db[self.eq_sel] - 2)
            self.eq_on = True
        elif ev == 'ENTER':
            self.eq_on = not self.eq_on
        self.sync_eq()
        self.draw_panel()
        self.tft.show(wait=False)

    def key_br(self, ev):
        n = len(self.br_items)
        if ev == 'UP' and n: self.br_cur = (self.br_cur - 1) % n
        elif ev == 'DOWN' and n: self.br_cur = (self.br_cur + 1) % n
        elif ev == 'ENTER' and n:
            label, name, kind = self.br_items[self.br_cur]
            d = self.br_dir
            if kind == 'up':
                self.br_dir = d.rsplit(b"/", 1)[0] or b"/"
                self.br_build()
            elif kind == 'dir':
                self.br_dir = join_path(d, name)
                self.br_build()
            else:
                wavs = [join_path(d, x[1]) for x in self.br_items if x[2] == 'file']
                first = 0
                if kind == 'file': first = wavs.index(join_path(d, name))
                self.tracks = wavs
                self.pl_cur = first
                self.pl_top = 0
                self.select(first)
                self.panel = None
                self.redraw_all()
                return
        self.br_top = self._top(self.br_cur, self.br_top)
        self.draw_panel()
        self.tft.show(wait=False)

    def handle(self, ev):
        back = ev in ('BACK', 'ESC')
        pn = self.panel
        if pn:
            if back:
                self.panel = None
                self.redraw_all()
            elif pn == 'PL': self.key_pl(ev)
            elif pn == 'EQ': self.key_eq(ev)
            else: self.key_br(ev)
            return None

        if back: return 'EXIT'
        old_foc = self.focus
        if ev == 'LEFT': self.focus = (self.focus - 1) % 10
        elif ev == 'RIGHT': self.focus = (self.focus + 1) % 10
        elif ev == 'UP': self.volume = min(100, self.volume + 5)
        elif ev == 'DOWN': self.volume = max(0, self.volume - 5)
        elif ev == 'ENTER': self.do_action(ACT[self.focus])

        if old_foc != self.focus:
            self.draw_buttons()
        self.draw_lcd()
        self.tft.show(wait=False)
        return None

    # ------------------------------------------------------------ Отрисовка
    def draw_title(self):
        t = self.tft
        t.fill_rect(0, 0, W, 12, C_TITLE)
        for y in (3, 6, 9):
            t.hline(4, y, 120, C_STRIPE)
            t.hline(196, y, 120, C_STRIPE)
        t.fill_rect(128, 1, 64, 10, C_TITLE)
        t.text("WINAMP", 136, 2, C_WHITE)

    def draw_buttons(self):
        t = self.tft
        pn = self.panel
        for i in range(10):
            act = ACT[i]
            x = 1 + i * 32
            on = ((act == 'play' and self.state == 'play') or
                  (act == 'pause' and self.state == 'pause') or
                  (act == 'eject' and pn == 'BR') or
                  (act == 'eq' and pn == 'EQ') or
                  (act == 'pl' and pn == 'PL'))
            foc = (i == self.focus and pn is None)
            t.fill_rect(x, 70, 30, 22, C_BTN_ON if on else C_BTN)
            t.rect(x, 70, 30, 22, C_CYAN if foc else C_FRAME)
            col = C_GREEN if on else C_WHITE
            cx, cy = x + 15, 81
            if act == 'prev':
                t.fill_rect(cx - 7, cy - 5, 2, 10, col)
                tri_left(t, cx - 4, cy - 5, 10, col)
            elif act == 'play': tri_right(t, cx - 4, cy - 6, 12, col)
            elif act == 'pause':
                t.fill_rect(cx - 5, cy - 5, 3, 10, col)
                t.fill_rect(cx + 2, cy - 5, 3, 10, col)
            elif act == 'stop': t.fill_rect(cx - 5, cy - 5, 10, 10, col)
            elif act == 'next':
                tri_right(t, cx - 5, cy - 5, 10, col)
                t.fill_rect(cx + 5, cy - 5, 2, 10, col)
            elif act == 'back': t.text("-10", x + 3, cy - 4, col)
            elif act == 'fwd': t.text("+10", x + 3, cy - 4, col)
            elif act == 'eject':
                tri_up(t, cx, cy - 6, 6, col)
                t.fill_rect(cx - 6, cy + 2, 12, 3, col)
            elif act == 'eq': t.text("EQ", cx - 8, cy - 4, col)
            else: t.text("PL", cx - 8, cy - 4, col)

    def draw_lcd(self):
        """Быстрое обновление табло дисплея без перерисовки кнопок"""
        t = self.tft
        now = time.ticks_ms()

        # Время и спектроанализатор
        t.fill_rect(4, 16, 68, 46, C_LCD)
        t.rect(4, 16, 68, 46, C_FRAME)
        sec = self.pos // self.byterate if self.f else 0
        if not (self.state == 'pause' and (self.tick // 2) % 2 == 0):
            m, s = min(sec // 60, 99), sec % 60
            seg_digit(t, 8, 20, m // 10, C_GREEN)
            seg_digit(t, 20, 20, m % 10, C_GREEN)
            t.fill_rect(33, 25, 2, 2, C_GREEN)
            t.fill_rect(33, 32, 2, 2, C_GREEN)
            seg_digit(t, 40, 20, s // 10, C_GREEN)
            seg_digit(t, 52, 20, s % 10, C_GREEN)

        for i in range(10):
            h = self.vu[i]
            if h > 0:
                col = C_GREEN if h < 12 else (C_YELLOW if h < 15 else C_RED)
                t.fill_rect(8 + i * 6, 58 - h, 5, h, col)

        # Бегущая строка названия
        t.fill_rect(78, 16, 236, 12, C_LCD)
        t.rect(78, 16, 236, 12, C_FRAME)
        col = C_GREEN
        if self.msg and time.ticks_diff(self.msg_until, now) > 0:
            text = self.msg
            col = C_YELLOW
        elif self.tracks and self.idx < len(self.tracks):
            p = self.tracks[self.idx]
            text = "%d. %s (%s)" % (self.idx + 1, self.track_name(p), self.dur_str(p))
        else:
            text = "Нет треков"

        if len(text) > 28:
            s2 = text + "   *   "
            o = self.marq % len(s2)
            text = (s2 + s2)[o:o + 28]
        draw_text(t, text, 82, 18, col)

        # Битрейт
        t.fill_rect(78, 30, 236, 10, C_PANEL)
        inf = self.info
        if inf:
            t.text("%3d kbps  %2d kHz" % (inf[0] * inf[2] * inf[1] // 1000, inf[0] // 1000), 78, 31, C_GREEN)
            t.text("stereo" if inf[1] == 2 else "mono", 214, 31, C_CYAN)
        else:
            t.text("--- kbps  -- kHz", 78, 31, C_DGREEN)

        st_map = {'play': ('PLAY', C_GREEN), 'pause': ('PAUSE', C_YELLOW), 'stop': ('STOP', C_GRAY)}
        st_t, st_c = st_map.get(self.state, ('STOP', C_GRAY))
        t.text(st_t, 274, 31, st_c)

        # Полоса трека
        t.fill_rect(78, 44, 236, 12, C_PANEL)   # Затираем старый ползунок сверху и снизу
        t.fill_rect(78, 46, 236, 8, C_LCD)
        t.rect(78, 46, 236, 8, C_FRAME)
        if inf and inf[4] > 0:
            px = min(226, self.pos * 226 // inf[4])
            t.fill_rect(80, 48, px, 4, C_DGREEN)
            t.fill_rect(78 + px, 45, 6, 10, C_GRAY)

        # Громкость
        t.fill_rect(78, 56, 236, 12, C_PANEL)
        t.text("VOL", 78, 58, C_GRAY)
        t.rect(104, 58, 100, 8, C_FRAME)
        t.fill_rect(106, 60, self.volume * 96 // 100, 4, C_GREEN)
        t.text("%3d%%" % self.volume, 212, 58, C_WHITE)
        t.text("EQ ON" if self.eq_on else "EQ OFF", 262, 58, C_GREEN if self.eq_on else C_DGREEN)

    def panel_frame(self, title, right="", rcol=C_GREEN):
        t = self.tft
        t.fill_rect(0, PANEL_Y, W, 218 - PANEL_Y, C_PANEL)
        t.fill_rect(0, PANEL_Y, W, 12, C_TITLE)
        for y in (PANEL_Y + 3, PANEL_Y + 6, PANEL_Y + 9):
            t.hline(4, y, 70, C_STRIPE)
            t.hline(W - 74, y, 70, C_STRIPE)
        tw = len(title) * 8
        t.fill_rect((W - tw) // 2 - 4, PANEL_Y + 1, tw + 8, 10, C_TITLE)
        draw_text(t, title, (W - tw) // 2, PANEL_Y + 2, C_WHITE)
        if right:
            draw_text(t, right, W - 6 - len(right) * 8, PANEL_Y + 2, rcol)

    def draw_panel(self):
        t = self.tft
        pn = self.panel
        if pn == 'PL': self.draw_pl()
        elif pn == 'EQ': self.draw_eq()
        elif pn == 'BR': self.draw_br()
        else:
            t.fill_rect(0, PANEL_Y, W, 218 - PANEL_Y, C_PANEL)
            t.hline(0, PANEL_Y - 2, W, C_FRAME)
            draw_text(t, "Треков в плейлисте: %d" % len(self.tracks), 8, PANEL_Y + 14, C_GREEN)
            draw_text(t, "ВЛЕВО/ВПРАВО - Выбор кнопки", 8, PANEL_Y + 36, C_GRAY)
            draw_text(t, "ВВЕРХ/ВНИЗ    - Громкость", 8, PANEL_Y + 50, C_GRAY)
            draw_text(t, "ENTER         - Нажать кнопку", 8, PANEL_Y + 64, C_GRAY)
            draw_text(t, "ESC           - Выход", 8, PANEL_Y + 78, C_GRAY)

    def draw_pl(self):
        t = self.tft
        self.panel_frame("ПЛЕЙЛИСТ")
        n = len(self.tracks)
        if not n:
            draw_text(t, "Плейлист пуст", 8, PANEL_Y + 30, C_GRAY)
            return
        for r in range(ROWS):
            i = self.pl_top + r
            if i >= n: break
            y = PANEL_Y + 14 + r * 12
            if i == self.pl_cur:
                t.fill_rect(2, y - 1, W - 8, 11, C_SEL)
            col = C_WHITE if i == self.idx else C_GREEN
            p = self.tracks[i]
            draw_text(t, ("%d. %s" % (i + 1, self.track_name(p)))[:29], 6, y, col)
            d = self.dur_str(p)
            t.text(d, W - 12 - len(d) * 8, y, col)

    def draw_eq(self):
        t = self.tft
        self.panel_frame("ЭКВАЛАЙЗЕР", "ВКЛ" if self.eq_on else "ВЫКЛ", C_GREEN if self.eq_on else C_RED)
        names = ("ПРЕАМП", "БАСЫ", "СРЕДНИЕ", "ВЫСОКИЕ")
        xs = (40, 120, 200, 280)
        for i in range(4):
            cx = xs[i]
            sel = (i == self.eq_sel)
            db = self.eq_db[i]
            t.fill_rect(cx - 1, 118, 3, 49, C_BTN)
            t.hline(cx - 9, 142, 19, C_GRAY)
            ky = 142 - db * 2
            kc = C_CYAN if sel else (C_GREEN if self.eq_on else C_GRAY)
            t.fill_rect(cx - 7, ky - 3, 15, 7, kc)
            s = "%+d dB" % db
            t.text(s, cx - len(s) * 4, 172, C_WHITE if sel else C_GRAY)
            nm = names[i]
            draw_text(t, nm, cx - len(nm) * 4, 184, C_CYAN if sel else C_GRAY)

    def draw_br(self):
        t = self.tft
        d = show_name(self.br_dir)
        self.panel_frame("ОБЗОР: " + (d if len(d) <= 22 else "..." + d[-19:]))
        items = self.br_items
        for r in range(ROWS):
            i = self.br_top + r
            if i >= len(items): break
            y = PANEL_Y + 14 + r * 12
            label, name, kind = items[i]
            if i == self.br_cur:
                t.fill_rect(2, y - 1, W - 8, 11, C_SEL)
            col = C_YELLOW if kind in ('dir', 'up') else (C_CYAN if kind == 'all' else C_GREEN)
            draw_text(t, label[:37], 6, y, col)

    def redraw_all(self):
        t = self.tft
        self.draw_title()
        t.fill_rect(0, 12, W, PANEL_Y - 12, C_PANEL)
        self.draw_buttons()
        self.draw_lcd()
        self.draw_panel()
        draw_system_taskbar(t, self.cfg, active_tab="WINAMP", tab_icon="winamp")
        t.show(wait=False)

    def tick_ui(self):
        self.tick += 1
        lvl = max(self.vl, self.vr) if (self.state == 'play' and self.f) else 0
        self.vu.pop(0)
        self.vu.append(min(16, lvl * 16 // 16000))
        if self.tick % 2 == 0:
            self.marq += 1
        self.draw_lcd()
        self.tft.show(wait=False)

    def run(self):
        self.scan_music()
        self.redraw_all()
        if self.tracks:
            self.start_track(0)
        try:
            while True:
                ev = self.inputs.get_event()
                if ev and self.handle(ev) == 'EXIT':
                    break

                if self.state == 'play' and self.f:
                    self.pump()
                else:
                    self.audio.write(self.silence)
                    time.sleep_ms(5)

                now = time.ticks_ms()
                if time.ticks_diff(now, self.last_ui) >= UI_MS:
                    self.last_ui = now
                    self.tick_ui()
        finally:
            self.close_file()