# app_uninstaller.py - Установка и удаление приложений RobotOS (DVI 320x240)
# Удалить: файл уходит в корзину (/trash) - его можно вернуть кнопкой "Установить".
# Установить: из корзины или с SD-карты (папка /sd/apps). Системные приложения защищены.
import os
import sys
import gc
import time
import math
import struct
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar
import apps_reg

W, H = 320, 240

C_BG        = rgb(24, 26, 32)
C_HEADER    = rgb(30, 34, 44)
C_CARD      = rgb(32, 36, 48)
C_CARD_HOV  = rgb(46, 54, 74)
C_BORDER    = rgb(50, 56, 72)
C_ACCENT    = rgb(0, 160, 255)
C_WHITE     = 0xFFFF
C_GRAY      = rgb(140, 150, 170)
C_DARK_GRAY = rgb(95, 105, 125)
C_GREEN     = rgb(0, 230, 120)
C_RED       = rgb(255, 75, 75)
C_YELLOW    = rgb(255, 215, 0)

ROW_H = 22
VIS = 7
ROW_Y = 38


def fmt_size(n):
    if n >= 1024:
        return "%d KB" % ((n + 1023) // 1024)
    return "%d B" % n


def flash_free():
    try:
        st = os.statvfs("/")
        return st[0] * st[3]
    except Exception:
        return 1 << 30


def make_dir(p):
    try:
        os.mkdir(p)
    except OSError:
        pass


def remove_file(p):
    try:
        os.remove(p)
    except OSError:
        pass


def copy_file(src, dst):
    gc.collect()
    buf = bytearray(2048)
    mv = memoryview(buf)
    with open(src, "rb") as f, open(dst, "wb") as g:
        while True:
            n = f.readinto(buf)
            if not n:
                break
            g.write(mv[:n])


def move_file(src, dst):
    """Переименование; если не вышло (разные разделы) - копия + удаление."""
    remove_file(dst)
    try:
        os.rename(src, dst)
    except OSError:
        copy_file(src, dst)
        if apps_reg.size_of(dst) != apps_reg.size_of(src):
            remove_file(dst)
            raise OSError("copy failed")
        os.remove(src)


class UninstallerApp:
    def __init__(self, tft, audio, inputs, config=None, games=False):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config is not None else {"vol_ui": 30, "mute": False}
        self.kinds = ("game",) if games else ("app", "robot")
        self.title = "Игры" if games else "Приложения"
        self._wave = {}

    # ------------------------------------------------------------ звук
    def beep(self, freq=1100, ms=10):
        vol = self.cfg.get("vol_ui", 30)
        if self.cfg.get("mute") or vol == 0:
            return
        amp = int(900 * vol / 100)
        key = (freq, amp)
        w = self._wave.get(key)
        if w is None:
            n = max(2, int(22050 / freq))
            w = bytearray(n * 2)
            for i in range(n):
                struct.pack_into("<h", w, i * 2, int(amp * math.sin(2 * math.pi * i / n)))
            if len(self._wave) > 10:
                self._wave.clear()
            self._wave[key] = w
        for _ in range(max(1, int((ms / 1000) * freq))):
            self.audio.write(w)

    # ------------------------------------------------------------ окна
    def header(self, title):
        t = self.tft
        t.fill_rect(0, 0, W, 20, C_HEADER)
        t.line(0, 19, W, 19, C_BORDER)
        draw_text(t, "< " + title, 8, 6, C_WHITE)
        t.text("Esc", 294, 6, C_WHITE)
        t.fill_rect(0, 20, W, 198, C_BG)

    def dialog(self, title, lines, ask=False):
        """Окно сообщения. ask=True: кнопки Да/Нет, возвращает True при "Да"."""
        t = self.tft
        dw = 240
        dh = 28 + 15 * len(lines) + 28
        dx = (W - dw) // 2
        dy = (218 - dh) // 2
        yes = False
        self.beep(1200, 15)
        while True:
            t.fill_rect(dx, dy, dw, dh, rgb(28, 32, 44))
            t.rect(dx, dy, dw, dh, C_ACCENT)
            t.fill_rect(dx + 2, dy + 2, dw - 4, 18, rgb(38, 44, 60))
            draw_text(t, title, dx + 8, dy + 6, C_WHITE)
            yy = dy + 28
            for ln in lines:
                draw_text(t, ln[:28], dx + 12, yy, C_WHITE)
                yy += 15
            by = dy + dh - 24
            if ask:
                for i, (txt, val) in enumerate((("Да", True), ("Нет", False))):
                    bx = dx + 40 + i * 90
                    on = (yes == val)
                    t.fill_rect(bx, by, 70, 18, C_ACCENT if on else C_CARD_HOV)
                    t.rect(bx, by, 70, 18, C_WHITE if on else C_BORDER)
                    draw_text(t, txt, bx + 35 - len(txt) * 4, by + 5, C_WHITE)
            else:
                t.fill_rect(dx + (dw - 60) // 2, by, 60, 18, C_ACCENT)
                t.text("OK", dx + (dw - 16) // 2, by + 5, C_WHITE)
            t.show()
            while True:
                ev = self.inputs.get_event()
                if ev:
                    break
                time.sleep_ms(20)
            if ev in ("ESC", "BACK"):
                self.beep(800, 10)
                return False
            if ev == "ENTER" or ev == " ":
                self.beep(900, 12)
                return yes if ask else True
            if ask and ev in ("LEFT", "RIGHT", "UP", "DOWN"):
                yes = not yes
                self.beep(1000, 8)

    # ------------------------------------------------------------ операции
    def do_remove(self, e):
        mod = e[0]
        try:
            make_dir(apps_reg.TRASH)
            for ext in (".py", ".mpy"):          # и .py, и .mpy - иначе останется копия, которую грузит import
                p = apps_reg.ROOT + "/" + mod + ext
                try:
                    os.stat(p)
                except OSError:
                    continue
                move_file(p, apps_reg.TRASH + "/" + mod + ext)
        except Exception as ex:
            return False, str(ex)[:26]
        sys.modules.pop(mod, None)
        gc.collect()
        return True, "Перемещено в корзину"

    def do_install(self, src):
        """Возвращает (успех, сообщение) или None, если пользователь передумал."""
        mod, name, path, origin = src
        dst = apps_reg.ROOT + "/" + name
        size = apps_reg.size_of(path)
        cur = apps_reg.path_of(mod)
        if cur and origin == "trash":
            return False, "Уже установлено"
        if cur:
            if not self.dialog("Замена", ["Уже установлено:", apps_reg.title_of(mod, cur)[:26],
                                          "Заменить новой версией?"], ask=True):
                return None
        free = flash_free() + (apps_reg.size_of(cur) if cur else 0)
        if size + 4096 > free:
            return False, "Мало места (нужно %d KB)" % ((size + 4096) // 1024)
        try:
            if origin == "trash":
                for ext in (".py", ".mpy"):               # вернуть все файлы программы
                    p = apps_reg.TRASH + "/" + mod + ext
                    try:
                        os.stat(p)
                    except OSError:
                        continue
                    move_file(p, apps_reg.ROOT + "/" + mod + ext)
            else:
                tmp = dst + ".tmp"
                copy_file(path, tmp)
                if apps_reg.size_of(tmp) != size:
                    remove_file(tmp)
                    return False, "Ошибка копирования"
                remove_file(apps_reg.ROOT + "/" + mod + ".py")      # старые версии (.mpy грузится первым!)
                remove_file(apps_reg.ROOT + "/" + mod + ".mpy")
                os.rename(tmp, dst)
        except Exception as ex:
            return False, str(ex)[:26]
        sys.modules.pop(mod, None)
        gc.collect()
        known = any(r[0] == mod for r in apps_reg.REG)
        if not known and not apps_reg.read_header(dst):
            return True, "Нет заголовка robotos-app: в меню не появится"
        return True, "Установлено"

    # ------------------------------------------------------------ экран: установка
    def sources(self):
        out = []
        for d, origin in ((apps_reg.TRASH, "trash"), (apps_reg.SD_DIR, "sd")):
            seen = {}
            for m, n in apps_reg.list_files(d):           # одна строка на программу (.mpy важнее .py)
                if m not in seen or n.endswith(".mpy"):
                    seen[m] = n
            for m in sorted(seen):
                path = d + "/" + seen[m]
                if self.kind_of(m, path) in self.kinds:   # игры - в разделе игр, программы - в программах
                    out.append((m, seen[m], path, origin))
        return out

    def kind_of(self, mod, path):
        for r in apps_reg.REG:
            if r[0] == mod:
                return r[4]
        h = apps_reg.read_header(path)
        return h[2] if h else "app"

    def view_install(self):
        sel = 0
        top = 0
        while True:
            src = self.sources()
            n = len(src)
            if sel >= n:
                sel = max(0, n - 1)
            if sel < top:
                top = sel
            if sel >= top + VIS:
                top = sel - VIS + 1

            t = self.tft
            self.header("Установка")
            draw_text(t, "Корзина и SD (/sd/apps)", 12, 24, C_GRAY)
            if not n:
                draw_text(t, "Нет приложений для установки.", 12, 60, C_WHITE)
                draw_text(t, "Положите файл app_xxx.py", 12, 80, C_GRAY)
                draw_text(t, "в папку /sd/apps на карте.", 12, 95, C_GRAY)
            y = ROW_Y
            for i in range(top, min(n, top + VIS)):
                m, name, path, origin = src[i]
                cur = (i == sel)
                t.fill_rect(12, y, 296, ROW_H - 2, C_CARD_HOV if cur else C_CARD)
                t.rect(12, y, 296, ROW_H - 2, C_ACCENT if cur else C_BORDER)
                draw_text(t, apps_reg.title_of(m, path)[:20], 18, y + 6, C_WHITE if cur else rgb(220, 225, 235))
                draw_text(t, "корзина" if origin == "trash" else "SD", 184, y + 6,
                          C_YELLOW if origin == "trash" else C_GREEN)
                sz = fmt_size(apps_reg.size_of(path))
                t.text(sz, 302 - len(sz) * 8, y + 7, C_ACCENT if cur else C_GRAY)
                y += ROW_H
            draw_text(t, "ENTER: Установить  ВПРАВО: Стереть", 12, 202, C_DARK_GRAY)
            draw_system_taskbar(t, self.cfg, active_tab="Установка", tab_icon="settings")
            t.show()

            while True:
                ev = self.inputs.get_event()
                if ev:
                    break
                time.sleep_ms(20)

            if ev in ("ESC", "BACK"):
                self.beep(800, 10)
                return
            if not n:
                continue
            if ev == "UP":
                sel = (sel - 1) % n
                self.beep(850, 8)
            elif ev == "DOWN":
                sel = (sel + 1) % n
                self.beep(750, 8)
            elif ev == "ENTER":
                r = self.do_install(src[sel])
                if r is not None:
                    self.dialog("Готово" if r[0] else "Ошибка", [r[1][:28], r[1][28:56]] if len(r[1]) > 28 else [r[1]])
            elif ev == "RIGHT":
                m, name, path, origin = src[sel]
                if origin != "trash":
                    self.dialog("Файл на SD", ["Файлы на карте отсюда", "не удаляются."])
                elif self.dialog("Стереть навсегда", ["Удалить из корзины:", apps_reg.title_of(m, path)[:26],
                                                      "Вернуть будет нельзя!"], ask=True):
                    remove_file(apps_reg.TRASH + "/" + m + ".py")
                    remove_file(apps_reg.TRASH + "/" + m + ".mpy")
                    self.beep(600, 20)

    # ------------------------------------------------------------ экран: список
    def view_main(self):
        sel = 0
        top = 0
        while True:
            items = [e for e in apps_reg.all_entries() if e[4] in self.kinds]
            n = len(items) + 1               # последняя строка - "Установить"
            if sel >= n:
                sel = n - 1
            if sel < top:
                top = sel
            if sel >= top + VIS:
                top = sel - VIS + 1

            t = self.tft
            self.header(self.title)
            draw_text(t, "Установлено: %d   Свободно: %d KB" % (len(items), flash_free() // 1024), 12, 24, C_GRAY)
            y = ROW_Y
            for i in range(top, min(n, top + VIS)):
                cur = (i == sel)
                t.fill_rect(12, y, 296, ROW_H - 2, C_CARD_HOV if cur else C_CARD)
                t.rect(12, y, 296, ROW_H - 2, C_ACCENT if cur else C_BORDER)
                if i == len(items):
                    draw_text(t, "+ Установить приложение...", 18, y + 6, C_GREEN)
                else:
                    e = items[i]
                    draw_text(t, e[3][:24], 18, y + 6, C_WHITE if cur else rgb(220, 225, 235))
                    if e[7]:
                        draw_text(t, "СИСТЕМА", 246, y + 6, C_DARK_GRAY)
                    else:
                        sz = fmt_size(apps_reg.size_of(e[6]))
                        t.text(sz, 302 - len(sz) * 8, y + 7, C_ACCENT if cur else C_GRAY)
                y += ROW_H
            draw_text(t, "ENTER: Удалить / Установить", 12, 202, C_DARK_GRAY)
            draw_system_taskbar(t, self.cfg, active_tab="Приложения", tab_icon="settings")
            t.show()

            while True:
                ev = self.inputs.get_event()
                if ev:
                    break
                time.sleep_ms(20)

            if ev in ("ESC", "BACK"):
                self.beep(800, 10)
                return
            elif ev == "UP":
                sel = (sel - 1) % n
                self.beep(850, 8)
            elif ev == "DOWN":
                sel = (sel + 1) % n
                self.beep(750, 8)
            elif ev == "ENTER":
                self.beep(1200, 15)
                if sel == len(items):
                    self.view_install()
                    continue
                e = items[sel]
                if e[7]:
                    self.dialog("Нельзя удалить", ["Системное приложение:", e[3][:26], "нужно для работы ОС."])
                elif self.dialog("Удаление", ["Удалить приложение?", e[3][:26],
                                              "Оно уйдет в корзину", "(можно вернуть)"], ask=True):
                    ok, msg = self.do_remove(e)
                    self.dialog("Готово" if ok else "Ошибка", [msg])

    def run(self):
        try:
            self.view_main()
        finally:
            gc.collect()
