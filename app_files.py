# app_files.py - Проводник RobotOS (DVI 320x240)
# Стиль Windows 10: 100% чистый русский шрифт, аккуратные бейджи, бесшовный UI
import os
import time
import math
import struct
import gc
from dvi_display import color565 as rgb
from gui import draw_system_taskbar

W, H = 320, 240
TB_H = 22                 # Высота панели задач
WIN_H = H - TB_H          # Рабочая область окна (218px)

# ---------------------------------------------------------------- Палитра
C_WIN_BG      = rgb(22, 26, 36)       # Тёмно-серый фон окна проводника
C_TITLE_BG    = rgb(28, 32, 44)       # Шапка окна
C_ADDR_BG     = rgb(16, 18, 26)       # Поле адресной строки
C_SEL_BG      = rgb(0, 110, 210)      # Полоса курсора
C_WHITE       = 0xFFFF
C_GRAY        = rgb(150, 160, 175)
C_DARK_TXT    = rgb(100, 110, 130)
C_GLOW        = rgb(0, 210, 255)
C_BORDER      = rgb(45, 52, 70)

# Бейджи файлов
C_DIR         = rgb(255, 205, 50)     # Золотой
C_WAV         = rgb(0, 230, 120)      # Зелёный
C_IMG         = rgb(255, 80, 180)     # Розовый
C_PY          = rgb(0, 210, 255)      # Голубой
C_TXT         = rgb(255, 170, 40)     # Оранжевый
C_FILE        = rgb(165, 175, 190)    # Серебристый
C_MARKED      = rgb(255, 245, 60)     # Ярко-жёлтый

# Панель задач Windows 10
C_TASKBAR     = rgb(26, 28, 34)
C_TASKBAR_SEP = rgb(44, 48, 58)
C_TAB_ACTIVE  = rgb(48, 52, 64)       # Светло-серая вкладка
C_ACCENT_LINE = rgb(0, 160, 255)      # Неоново-голубая полоска Windows 10

VISIBLE_ROWS  = 9
ROW_H         = 14

# ---------------------------------------------------------------- Фундаментальный русификатор шрифта 8x8
# 1. Русские буквы, визуально совпадающие с латиницей:
CYR_TO_LATIN = {
    'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H',
    'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X',
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x'
}

# 2. Истинно русские глифы 8x8:
CYR_BITMAPS = {
    # Заглавные
    'Б': b'\x7e\x40\x7c\x42\x42\x42\x7c\x00',
    'Г': b'\x7e\x42\x40\x40\x40\x40\x40\x00',
    'Д': b'\x1c\x24\x24\x24\x24\x7e\x42\x00',
    'Ж': b'\x49\x49\x2a\x1c\x2a\x49\x49\x00',
    'З': b'\x3c\x42\x02\x1c\x02\x42\x3c\x00',
    'И': b'\x42\x46\x4a\x52\x62\x42\x42\x00',
    'Й': b'\x34\x00\x42\x46\x4a\x52\x62\x00',
    'Л': b'\x1e\x22\x42\x42\x42\x42\x42\x00',
    'П': b'\x7e\x42\x42\x42\x42\x42\x42\x00',
    'У': b'\x42\x42\x42\x3e\x02\x04\x38\x00',
    'Ф': b'\x10\x7c\xd6\xd6\x7c\x10\x10\x00',
    'Ц': b'\x42\x42\x42\x42\x7e\x02\x02\x00',
    'Ч': b'\x42\x42\x42\x3e\x02\x02\x02\x00',
    'Ш': b'\x49\x49\x49\x49\x49\x7f\x00\x00',
    'Щ': b'\x49\x49\x49\x49\x7f\x01\x01\x00',
    'Ъ': b'\x60\x20\x3c\x22\x22\x22\x3c\x00',
    'Ы': b'\x42\x42\x72\x4a\x4a\x72\x00\x00',
    'Ь': b'\x40\x40\x7c\x42\x42\x42\x7c\x00',
    'Э': b'\x3c\x02\x02\x1e\x02\x02\x3c\x00',
    'Ю': b'\x46\x49\x49\x79\x49\x49\x46\x00',
    'Я': b'\x3e\x42\x42\x3e\x12\x22\x42\x00',

    # Строчные
    'б': b'\x3c\x40\x7c\x42\x42\x42\x7c\x00',
    'в': b'\x00\x00\x7c\x42\x78\x42\x7c\x00',
    'г': b'\x00\x00\x7e\x40\x40\x40\x40\x00',
    'д': b'\x00\x00\x1c\x24\x24\x7e\x42\x42',
    'ж': b'\x00\x00\x49\x2a\x1c\x2a\x49\x00',
    'з': b'\x00\x00\x3c\x02\x1c\x02\x3c\x00',
    'и': b'\x00\x00\x42\x46\x4a\x52\x62\x00',
    'й': b'\x34\x00\x42\x46\x4a\x52\x62\x00',
    'к': b'\x00\x00\x44\x48\x70\x48\x44\x00',
    'л': b'\x00\x00\x1e\x22\x42\x42\x42\x00',
    'м': b'\x00\x00\x42\x66\x5a\x42\x42\x00',
    'н': b'\x00\x00\x42\x42\x7e\x42\x42\x00',
    'п': b'\x00\x00\x7e\x42\x42\x42\x42\x00',
    'т': b'\x00\x00\x7e\x10\x10\x10\x10\x00',
    'ф': b'\x00\x10\x7c\xd6\x7c\x10\x10\x00',
    'ц': b'\x00\x00\x42\x42\x42\x7e\x02\x02',
    'ч': b'\x00\x00\x42\x42\x3e\x02\x02\x00',
    'ш': b'\x00\x00\x49\x49\x49\x49\x7f\x00',
    'щ': b'\x00\x00\x49\x49\x49\x7f\x01\x01',
    'ъ': b'\x00\x00\x60\x20\x3c\x22\x3c\x00',
    'ы': b'\x00\x00\x42\x42\x72\x4a\x72\x00',
    'ь': b'\x00\x00\x40\x40\x7c\x42\x7c\x00',
    'э': b'\x00\x00\x3c\x02\x1e\x02\x3c\x00',
    'ю': b'\x00\x00\x46\x49\x79\x49\x46\x00',
    'я': b'\x00\x00\x3e\x42\x3e\x12\x62\x00',
}

def draw_text(tft, text, x, y, color):
    """Выводит текст с гарантированной защитой от графических артефактов."""
    cx = x
    for ch in text:
        if ch in CYR_BITMAPS:
            bmp = CYR_BITMAPS[ch]
            for row in range(8):
                b = bmp[row]
                if b:
                    for col in range(8):
                        if b & (0x80 >> col):
                            tft.pixel(cx + col, y + row, color)
            cx += 8
        elif ch in CYR_TO_LATIN:
            tft.text(CYR_TO_LATIN[ch], cx, y, color)
            cx += 8
        elif ord(ch) < 128:
            tft.text(ch, cx, y, color)
            cx += 8
        else:
            # Неизвестный Unicode-байт никогда не бросаем во framebuf!
            tft.text('?', cx, y, color)
            cx += 8


class FileManagerApp:
    def __init__(self, tft, audio, inputs, config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False, "hour": 20, "minute": 45}

        # self.path is None -> экран выбора дисков "Этот компьютер"
        self.path = None
        self.items = []
        self.sel = 0
        self.top = 0
        self.marked = set()

        self.refresh()

    def _sd_present(self):
        try:
            os.stat("/sd")
            return True
        except:
            return False

    def beep(self, freq=1000, ms=15):
        if self.cfg.get("mute") or self.cfg.get("vol_ui", 30) == 0:
            return
        rate = 22050
        samples = max(2, int(rate / freq))
        cycle = bytearray(samples * 2)
        amp = int(1000 * (self.cfg.get("vol_ui", 30) / 100))
        for i in range(samples):
            v = int(amp * math.sin(2 * math.pi * i / samples))
            struct.pack_into("<h", cycle, i * 2, v)
        for _ in range(max(1, int((ms / 1000) * freq))):
            self.audio.write(cycle)

    def format_size(self, size):
        if size < 1024: return f"{size} B"
        elif size < 1024 * 1024: return f"{size//1024} KB"
        else: return f"{size//(1024*1024)} MB"

    def refresh(self):
        # 1. Режим "Этот компьютер"
        if self.path is None:
            self.items = [
                ("1. FLASH STORAGE ( / )", True, 0, "DRV", "/"),
            ]
            if self._sd_present():
                self.items.append(("2. MICROSD CARD  ( /sd )", True, 0, "DRV", "/sd"))
            self.sel = max(0, min(self.sel, len(self.items) - 1))
            self.top = 0
            return

        # 2. Режим просмотра папки
        items = []
        items.append(("..", True, 0, "UP", ""))

        raw_entries = []
        try:
            # 1. Читаем путь в сырых байтах — это защищает от падения на норвежских и спецсимволах!
            p_bytes = self.path.encode() if isinstance(self.path, str) else self.path
            
            for entry in os.ilistdir(p_bytes):
                # 2. Безопасная расшифровка имени файла
                raw_name = entry[0]
                if isinstance(raw_name, bytes):
                    try:
                        name = raw_name.decode("utf-8")
                    except:
                        # Если попалась редкая буква — заменяем её, но НЕ роняем чтение папки!
                        name = "".join(chr(b) if 32 <= b < 127 else "_" for b in raw_name)
                else:
                    name = str(raw_name)

                # Пропуск системного мусора
                if name.startswith('.') or name in ['System Volume Information', '$RECYCLE.BIN', 'FOUND.000']:
                    continue

                is_dir = (entry[1] == 0x4000)
                size = entry[3] if len(entry) > 3 else 0
                raw_entries.append((name, is_dir, size))
        except Exception as e:
            print("Ошибка чтения папки:", e)

        raw_entries.sort(key=lambda x: (not x[1], x[0].lower()))

        for name, is_dir, size in raw_entries:
            ext = name.split(".")[-1].lower() if "." in name else ""
            if not is_dir and size == 0:
                try:
                    full = (self.path + "/" + name).replace("//", "/")
                    size = os.stat(full)[6]
                except:
                    pass
            tag = "DIR" if is_dir else ext.upper()
            items.append((name, is_dir, size, tag, ""))

        if len(items) == 1:
            items.append(("<EMPTY>", False, 0, "---", ""))

        self.items = items
        self.sel = max(0, min(self.sel, len(items) - 1))
        if self.sel < self.top:
            self.top = self.sel
        if self.sel >= self.top + VISIBLE_ROWS:
            self.top = self.sel - VISIBLE_ROWS + 1

    # ------------------------------------------------------------ Диалоговые окна
    def prompt_input_cursor(self, title, initial_val=""):
        text = initial_val
        cur_pos = len(text)
        scroll_x = 0
        max_disp = 24
        bw, bh = 240, 76
        bx = (W - bw) // 2
        by = (WIN_H - bh) // 2

        while True:
            if cur_pos < scroll_x:
                scroll_x = cur_pos
            elif cur_pos >= scroll_x + max_disp:
                scroll_x = cur_pos - max_disp + 1

            disp_str = text[scroll_x : scroll_x + max_disp]

            self.tft.fill_rect(bx, by, bw, bh, rgb(28, 32, 44))
            self.tft.rect(bx, by, bw, bh, C_GLOW)
            self.tft.fill_rect(bx + 2, by + 2, bw - 4, 18, rgb(40, 48, 66))
            draw_text(self.tft, title[:24], bx + 8, by + 6, C_WHITE)

            self.tft.fill_rect(bx + 10, by + 26, bw - 20, 20, rgb(14, 16, 24))
            self.tft.rect(bx + 10, by + 26, bw - 20, 20, rgb(70, 85, 115))
            draw_text(self.tft, disp_str, bx + 14, by + 32, C_WHITE)

            c_px = bx + 14 + (cur_pos - scroll_x) * 8
            if bx + 14 <= c_px <= bx + bw - 14:
                self.tft.fill_rect(c_px, by + 42, 7, 2, C_GLOW)

            self.tft.text("ENTER: OK      ESC: CANCEL", bx + 28, by + 56, C_GRAY)
            self.tft.show()

            while True:
                ev = self.inputs.get_event()
                if ev:
                    if ev in ['ESC', 'BACK']:
                        return None
                    elif ev == 'ENTER':
                        clean = text.strip()
                        return clean if clean else None
                    elif ev == 'LEFT':
                        if cur_pos > 0:
                            cur_pos -= 1
                            self.beep(900, 6); break
                    elif ev == 'RIGHT':
                        if cur_pos < len(text):
                            cur_pos += 1
                            self.beep(900, 6); break
                    elif ev == 'BACKSPACE':
                        if cur_pos > 0:
                            text = text[:cur_pos-1] + text[cur_pos:]
                            cur_pos -= 1
                            self.beep(650, 8); break
                    elif len(ev) == 1 and ev not in ['\\']:
                        text = text[:cur_pos] + ev + text[cur_pos:]
                        cur_pos += 1
                        self.beep(1200, 6); break
                time.sleep_ms(20)

    def prompt_confirm(self, title, msg):
        bw, bh = 220, 75
        bx = (W - bw) // 2
        by = (WIN_H - bh) // 2
        sel = 0

        while True:
            self.tft.fill_rect(bx, by, bw, bh, rgb(28, 20, 25))
            self.tft.rect(bx, by, bw, bh, rgb(255, 60, 60))
            self.tft.fill_rect(bx + 2, by + 2, bw - 4, 18, rgb(180, 30, 40))
            draw_text(self.tft, title[:22], bx + 8, by + 6, C_WHITE)
            draw_text(self.tft, msg[:25], bx + 12, by + 28, C_WHITE)

            btn_y = by + 48
            c1 = C_GLOW if sel == 0 else C_GRAY
            c2 = C_GLOW if sel == 1 else C_GRAY
            self.tft.text("[ YES ]", bx + 40, btn_y, c1)
            self.tft.text("[ NO  ]", bx + 130, btn_y, c2)
            self.tft.show()

            while True:
                ev = self.inputs.get_event()
                if ev:
                    if ev in ['LEFT', 'RIGHT', 'UP', 'DOWN']:
                        sel = 1 - sel
                        self.beep(850, 10); break
                    elif ev in ['ESC', 'BACK']:
                        return False
                    elif ev == 'ENTER':
                        return (sel == 0)
                time.sleep_ms(20)

    def show_dialog(self, title, msg):
        bw, bh = 220, 70
        bx = (W - bw) // 2
        by = (WIN_H - bh) // 2
        self.tft.fill_rect(bx, by, bw, bh, rgb(28, 32, 44))
        self.tft.rect(bx, by, bw, bh, C_GLOW)
        self.tft.fill_rect(bx + 2, by + 2, bw - 4, 18, rgb(40, 48, 66))
        draw_text(self.tft, title, bx + 8, by + 6, C_WHITE)
        draw_text(self.tft, msg[:25], bx + 12, by + 30, C_WHITE)
        self.tft.text("[ ENTER: OK ]", bx + 64, by + 50, C_GLOW)
        self.tft.show()
        self.beep(600, 30)
        while True:
            ev = self.inputs.get_event()
            if ev in ['ENTER', 'ESC', 'BACK']:
                break
            time.sleep_ms(20)

    # ------------------------------------------------------------ Операции
    def copy_or_move(self, is_move=False):
        if self.path is None:
            return
        targets = list(self.marked) if self.marked else []
        if not targets:
            cur_item = self.items[self.sel][0]
            if cur_item not in ["..", "<EMPTY>"]:
                targets = [cur_item]

        if not targets:
            return

        title = "Перенос в папку:" if is_move else "Копировать в папку:"
        default_dst = (self.path + "/").replace("//", "/")
        target_path = self.prompt_input_cursor(title, default_dst)
        if not target_path:
            return

        target_dir = target_path.rstrip("/")
        if not target_dir: target_dir = "/"

        try:
            os.mkdir(target_dir)
        except:
            pass

        for f in targets:
            src = (self.path + "/" + f).replace("//", "/")
            dst = (target_dir + "/" + f).replace("//", "/")
            if src == dst:
                dst = (target_dir + "/copy_" + f).replace("//", "/")

            is_same_drive = (src.startswith("/sd") == dst.startswith("/sd"))
            if is_move and is_same_drive:
                try:
                    os.rename(src, dst)
                    continue
                except:
                    pass

            try:
                with open(src, "rb") as fsrc:
                    with open(dst, "wb") as fdst:
                        buf = bytearray(2048)
                        while True:
                            n = fsrc.readinto(buf)
                            if not n: break
                            fdst.write(buf[:n])
                if is_move:
                    try: os.remove(src)
                    except: pass
            except Exception as e:
                print("Copy/Move error:", e)

        self.beep(1600, 35)
        self.marked.clear()
        self.refresh()

    def delete_selected(self):
        if self.path is None:
            return
        targets = list(self.marked) if self.marked else []
        if not targets:
            cur_item = self.items[self.sel][0]
            if cur_item not in ["..", "<EMPTY>"]:
                targets = [cur_item]

        if not targets:
            return

        msg = f"Удалить {len(targets)} файл(ов)?" if len(targets) > 1 else f"Удалить {targets[0][:15]}?"
        if self.prompt_confirm("УДАЛЕНИЕ", msg):
            for t in targets:
                full = (self.path + "/" + t).replace("//", "/")
                try:
                    if (os.stat(full)[0] & 0x4000) != 0:
                        os.rmdir(full)
                    else:
                        os.remove(full)
                except Exception as e:
                    print("Del err:", e)
            self.beep(600, 40)
            self.marked.clear()
            self.refresh()

    def rename_item(self):
        if self.path is None:
            return
        cur_item = self.items[self.sel][0]
        if cur_item in ["..", "<EMPTY>"]:
            return
        new_name = self.prompt_input_cursor("Новое имя:", cur_item)
        if new_name and new_name != cur_item:
            try:
                os.rename((self.path + "/" + cur_item).replace("//", "/"),
                          (self.path + "/" + new_name).replace("//", "/"))
                self.beep(1400, 25)
            except Exception as e:
                print("Rename err:", e)
            self.refresh()

    def create_dir(self):
        if self.path is None:
            return
        new_dir = self.prompt_input_cursor("Имя новой папки:", "New_Folder")
        if new_dir:
            try:
                os.mkdir((self.path + "/" + new_dir).replace("//", "/"))
                self.beep(1400, 25)
            except Exception as e:
                print("Mkdir err:", e)
            self.refresh()

    # ------------------------------------------------------------ Отрисовка UI (Без зазоров!)
    def draw_window_header(self):
        # 1. Заголовок окна (Y = 0 .. 19)
        self.tft.fill_rect(0, 0, W, 20, C_TITLE_BG)
        self.tft.line(0, 19, W, 19, C_BORDER)

        # Миниатюрная папочка Windows слева
        self.tft.fill_rect(8, 5, 5, 2, C_DIR)
        self.tft.fill_rect(8, 7, 12, 7, rgb(230, 170, 20))
        self.tft.fill_rect(10, 6, 8, 2, C_WHITE)
        self.tft.fill_rect(8, 8, 12, 6, C_DIR)

        draw_text(self.tft, "Файлы", 25, 6, C_WHITE)

        # Чистый Esc справа
        self.tft.text("Esc", 294, 6, C_WHITE)

        # 2. Адресная строка (Y = 20 .. 37) - ровно встык!
        self.tft.fill_rect(0, 20, W, 18, C_WIN_BG)
        self.tft.fill_rect(6, 21, W - 12, 16, C_ADDR_BG)
        self.tft.rect(6, 21, W - 12, 16, C_BORDER)

        if self.path is None:
            draw_text(self.tft, "Этот компьютер", 12, 25, C_GLOW)
        else:
            p_str = self.path
            if len(p_str) > 34:
                p_str = ".." + p_str[-32:]
            self.tft.text(p_str, 12, 25, C_GLOW)

    def draw_file_list(self):
        # 3. Список файлов (Y = 38 .. 167) - ровно встык!
        self.tft.fill_rect(0, 38, W, 130, C_WIN_BG)

        y = 40
        for i in range(self.top, min(len(self.items), self.top + VISIBLE_ROWS)):
            item = self.items[i]
            name, is_dir, size, tag = item[0], item[1], item[2], item[3]
            is_cursor = (i == self.sel)
            is_marked = (name in self.marked)

            if is_cursor:
                self.tft.fill_rect(2, y - 1, W - 4, ROW_H, C_SEL_BG)

            # Аккуратные английские бейджи БЕЗ внутренних пробелов
            if tag == "DRV":
                badge, b_col = "[DRV]", C_DIR
            elif tag == "UP":
                badge, b_col = "[UP]", C_DIR
            elif tag == "DIR":
                badge, b_col = "[DIR]", C_DIR
            elif tag == "WAV":
                badge, b_col = "[WAV]", C_WAV
            elif tag in ["BMP", "RAW", "PNG"]:
                badge, b_col = f"[{tag[:3]}]", C_IMG
            elif tag == "PY":
                badge, b_col = "[PY]", C_PY
            elif tag in ["TXT", "LOG", "MD"]:
                badge, b_col = f"[{tag[:3]}]", C_TXT
            else:
                badge, b_col = "[FILE]", C_FILE

            # Метка выбора
            pfx = "*" if is_marked else " "
            self.tft.text(pfx + badge, 4, y + 3, C_MARKED if is_marked else b_col)

            # Имя файла начинается ровно с X = 58
            name_col = C_MARKED if is_marked else (C_WHITE if is_cursor else rgb(220, 225, 235))
            self.tft.text(name[:23], 58, y + 3, name_col)

            # Размер файла справа
            if not is_dir and tag not in ["---", "DRV", "UP"]:
                sz_str = self.format_size(size)
                self.tft.text(sz_str, 254, y + 3, C_WHITE if is_cursor else C_GRAY)
            elif is_dir and tag == "DIR":
                self.tft.text("<DIR>", 264, y + 3, C_DIR)

            y += ROW_H

    def draw_disk_bar(self):
        # 4. Панель диска (Y = 168 .. 193) - ровно встык!
        bar_y = 168
        self.tft.fill_rect(0, bar_y, W, 26, rgb(16, 20, 28))
        self.tft.line(0, bar_y, W, bar_y, C_BORDER)

        root = "/sd" if (self.path and self.path.startswith("/sd")) else "/"
        drive_name = "Карта MicroSD" if root == "/sd" else "Флеш-память"

        try:
            st = os.statvfs(root)
            total = st[0] * st[2]
            free = st[0] * st[3]
            used = total - free
            pct = int((used / total) * 100) if total > 0 else 0

            u_str = self.format_size(used)
            t_str = self.format_size(total)
            info_str = f"{drive_name}: {u_str} / {t_str} ({pct}%)"
            draw_text(self.tft, info_str, 8, bar_y + 4, C_GRAY)

            # Индикатор
            self.tft.rect(8, bar_y + 16, 304, 6, rgb(50, 58, 76))
            fill_w = min(300, max(2, int(300 * (pct / 100))))
            self.tft.fill_rect(10, bar_y + 18, fill_w, 2, C_GLOW)
        except:
            draw_text(self.tft, f"{drive_name}: Готов к работе", 8, bar_y + 6, C_GRAY)

    def draw_hotkeys_bar(self):
        # 5. Панель горячих клавиш (Y = 194 .. 217) - ровно встык!
        hk_y = 194
        self.tft.fill_rect(0, hk_y, W, 24, rgb(12, 15, 22))
        self.tft.line(0, hk_y, W, hk_y, C_BORDER)

        draw_text(self.tft, "ENTER:Открыть  ПРОБЕЛ:Выбор  C:Копир", 6, hk_y + 3, C_WHITE)
        draw_text(self.tft, "M:Перенос   D:Удалить   N:Папка   R:Имя", 6, hk_y + 13, C_GLOW)

    def render_all(self):
        self.draw_window_header()
        self.draw_file_list()
        self.draw_disk_bar()
        self.draw_hotkeys_bar()
        
        # Системная панель задач с нашей вкладкой "Файлы"
        draw_system_taskbar(self.tft, self.cfg, active_tab="Файлы", tab_icon="folder")
        
        self.tft.show()

    # ------------------------------------------------------------ Главный цикл
    def run(self):
        self.render_all()

        while True:
            ev = self.inputs.get_event()
            if not ev:
                time.sleep_ms(20)
                continue

            # Прыжок на диски по 1 / 2
            if ev == '1':
                self.path = "/"
                self.marked.clear()
                self.sel = 0
                self.top = 0
                self.refresh()
                self.beep(1300, 15)
                self.render_all()
                continue
            elif ev == '2':
                if self._sd_present():
                    self.path = "/sd"
                    self.marked.clear()
                    self.sel = 0
                    self.top = 0
                    self.refresh()
                    self.beep(1300, 15)
                    self.render_all()
                else:
                    self.beep(400, 40)
                continue

            # Навигация
            elif ev == 'UP':
                if len(self.items) > 0:
                    self.sel = (self.sel - 1) % len(self.items)
                    if self.sel < self.top:
                        self.top = self.sel
                    if self.sel >= self.top + VISIBLE_ROWS:
                        self.top = self.sel - VISIBLE_ROWS + 1
                    self.beep(850, 8)
                    self.render_all()
                continue

            elif ev == 'DOWN':
                if len(self.items) > 0:
                    self.sel = (self.sel + 1) % len(self.items)
                    if self.sel < self.top:
                        self.top = self.sel
                    if self.sel >= self.top + VISIBLE_ROWS:
                        self.top = self.sel - VISIBLE_ROWS + 1
                    self.beep(750, 8)
                    self.render_all()
                continue

            # Пробел: мульти-выбор
            elif ev == ' ':
                if self.path is not None and len(self.items) > 0:
                    curr_name = self.items[self.sel][0]
                    if curr_name not in ["..", "<EMPTY>"]:
                        if curr_name in self.marked:
                            self.marked.remove(curr_name)
                        else:
                            self.marked.add(curr_name)
                        self.beep(1400, 10)
                        self.sel = (self.sel + 1) % len(self.items)
                        if self.sel >= self.top + VISIBLE_ROWS:
                            self.top = self.sel - VISIBLE_ROWS + 1
                        self.render_all()
                continue

            # ESC: Выход / Подъём наверх
            elif ev in ['BACK', 'ESC']:
                self.beep(600, 20)
                if self.marked:
                    self.marked.clear()
                    self.render_all()
                elif self.path is not None:
                    if self.path not in ["/", "/sd"]:
                        self.path = "/".join(self.path.rstrip("/").split("/")[:-1])
                        if not self.path: self.path = "/"
                    else:
                        self.path = None
                    self.sel = 0
                    self.top = 0
                    self.refresh()
                    self.render_all()
                else:
                    return  # Выход на рабочий стол

            # Горячие клавиши
            elif ev in ['c', 'C']:
                self.copy_or_move(is_move=False)
                self.render_all()
                continue
            elif ev in ['m', 'M', 'x', 'X']:
                self.copy_or_move(is_move=True)
                self.render_all()
                continue
            elif ev in ['d', 'D']:
                self.delete_selected()
                self.render_all()
                continue
            elif ev in ['r', 'R']:
                self.rename_item()
                self.render_all()
                continue
            elif ev in ['n', 'N']:
                self.create_dir()
                self.render_all()
                continue

            # ENTER
            elif ev == 'ENTER':
                if len(self.items) == 0:
                    continue

                item = self.items[self.sel]
                curr_name, curr_isdir, _, curr_tag = item[0], item[1], item[2], item[3]

                # Вход в диск
                if self.path is None:
                    target_drive = item[4]
                    self.path = target_drive
                    self.sel = 0
                    self.top = 0
                    self.refresh()
                    self.beep(1200, 20)
                    self.render_all()
                    continue

                # Подъём на ".."
                if curr_name == "..":
                    if self.path not in ["/", "/sd"]:
                        self.path = "/".join(self.path.rstrip("/").split("/")[:-1])
                        if not self.path: self.path = "/"
                    else:
                        self.path = None
                    self.sel = 0
                    self.top = 0
                    self.refresh()
                    self.render_all()

                # Вход в папку
                elif curr_isdir:
                    self.beep(1200, 25)
                    self.path = (self.path + "/" + curr_name).replace("//", "/")
                    self.sel = 0
                    self.top = 0
                    self.marked.clear()
                    self.refresh()
                    self.render_all()

                # Открытие файлов через специализированные программы
                else:
                    full_file = (self.path + "/" + curr_name).replace("//", "/")
                    curr_ext = curr_name.split(".")[-1].lower() if "." in curr_name else ""

                    if curr_ext in ["bmp", "raw", "png"]:
                        try:
                            import app_gallery
                            gallery = app_gallery.GalleryApp(self.tft, self.audio, self.inputs, self.cfg)
                            gallery.run_from_file(full_file)
                        except Exception as e:
                            self.show_dialog("Галерея", "Ошибка запуска фото")
                        self.render_all()

                    elif curr_ext in ["wav", "mp3"]:
                        try:
                            import app_player
                            player = app_player.MusicPlayerApp(self.tft, self.audio, self.inputs, filepath=full_file)
                            player.run()
                        except Exception as e:
                            self.show_dialog("Плеер", "Ошибка запуска трека")
                        self.render_all()

                    elif curr_ext in ["txt", "log", "md", "py"]:
                        try:
                            import app_editor
                            editor = app_editor.NotepadApp(self.tft, self.audio, self.inputs, self.cfg, filepath=full_file)
                            editor.run()
                        except Exception as e:
                            self.show_dialog("Редактор", "Ошибка открытия текста")
                        self.render_all()
                    else:
                        self.beep(400, 40)