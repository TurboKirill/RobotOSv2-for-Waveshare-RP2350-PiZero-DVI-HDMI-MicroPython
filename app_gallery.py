# app_gallery.py - Полноэкранная быстрая фотогалерея для RobotOS (DVI 320x240)
# Чистый Fullscreen 320x240 (без рамок и консолей), RAW 16b, BMP (16, 24, 32-bit ARGB)
import os
import time
import math
import struct
import micropython
from dvi_display import color565 as rgb
from gui import draw_text

W, H = 320, 240

# ================= МАШИННЫЙ КОД ARM CORTEX-M33 (VIPER) =================
@micropython.viper
def decode_row_24(src: ptr8, dst: ptr8, width: int):
    s = 0
    d = 0
    for x in range(width):
        b = int(src[s])
        g = int(src[s + 1])
        r = int(src[s + 2])
        s += 3
        c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        dst[d] = c & 0xFF
        dst[d + 1] = (c >> 8) & 0xFF
        d += 2

@micropython.viper
def decode_row_32(src: ptr8, dst: ptr8, width: int):
    s = 0
    d = 0
    for x in range(width):
        b = int(src[s])
        g = int(src[s + 1])
        r = int(src[s + 2])
        s += 4  # Пропуск Alpha
        c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        dst[d] = c & 0xFF
        dst[d + 1] = (c >> 8) & 0xFF
        d += 2

@micropython.viper
def decode_row_24_scale2(src: ptr8, dst: ptr8, w_out: int):
    s = 0
    d = 0
    for x in range(w_out):
        b = int(src[s])
        g = int(src[s + 1])
        r = int(src[s + 2])
        s += 6
        c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        dst[d] = c & 0xFF
        dst[d + 1] = (c >> 8) & 0xFF
        d += 2

@micropython.viper
def decode_row_32_scale2(src: ptr8, dst: ptr8, w_out: int):
    s = 0
    d = 0
    for x in range(w_out):
        b = int(src[s])
        g = int(src[s + 1])
        r = int(src[s + 2])
        s += 8
        c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        dst[d] = c & 0xFF
        dst[d + 1] = (c >> 8) & 0xFF
        d += 2


class GalleryApp:
    def __init__(self, tft, audio, inputs, config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False}
        self.photos = []
        self.current_idx = 0

    def beep(self, freq=1100, ms=10):
        if self.cfg.get("mute") or self.cfg.get("vol_ui", 30) == 0:
            return
        rate = 22050
        samples = max(2, int(rate / freq))
        cycle = bytearray(samples * 2)
        amp = int(800 * (self.cfg.get("vol_ui", 30) / 100))
        for i in range(samples):
            v = int(amp * math.sin(2 * math.pi * i / samples))
            struct.pack_into("<h", cycle, i * 2, v)
        for _ in range(int((ms / 1000) * freq)):
            self.audio.write(cycle)

    def _safe_str(self, val):
        if isinstance(val, str): return val
        try: return val.decode("utf-8")
        except: return "".join(chr(b) if 32 <= b < 127 else "_" for b in val)

    def scan_photos(self, start_dir=None):
        """Сканирует папки в поисках BMP, RAW и BIN"""
        self.photos = []
        seen = set()
        valid_exts = (".bmp", ".raw", ".bin")

        search_roots = []
        if start_dir:
            search_roots.append(start_dir)

        for r in ["/photo", "photo", "/sd/photo", "/sd/PHOTO", "/sd/pictures", "/sd", "/"]:
            if r not in search_roots:
                search_roots.append(r)

        for d in search_roots:
            try:
                for e in os.ilistdir(d):
                    name = self._safe_str(e[0])
                    if name.startswith("."): continue
                    is_dir = (e[1] == 0x4000)
                    low = name.lower()

                    if is_dir and d in ("/", "/sd"):
                        sub_dir = (d + "/" + name).replace("//", "/")
                        if not name.startswith("$") and name not in ("lib", "System Volume Information"):
                            try:
                                for sub_e in os.ilistdir(sub_dir):
                                    sub_name = self._safe_str(sub_e[0])
                                    if not sub_name.startswith(".") and any(sub_name.lower().endswith(x) for x in valid_exts):
                                        full = (sub_dir + "/" + sub_name).replace("//", "/")
                                        if full.lower() not in seen:
                                            seen.add(full.lower())
                                            self.photos.append(full)
                            except: pass
                    elif not is_dir and any(low.endswith(x) for x in valid_exts):
                        full = (d + "/" + name).replace("//", "/")
                        if full.lower() not in seen:
                            seen.add(full.lower())
                            self.photos.append(full)
            except: pass

        self.photos.sort(key=lambda x: x.split("/")[-1].lower())
        self.current_idx = 0

    def open_folder_dialog(self):
        cur_dir = "/photo"
        try: os.stat(cur_dir)
        except: cur_dir = "/sd"
        if self.photos:
            cur_dir = "/".join(self.photos[self.current_idx].split("/")[:-1])
            if not cur_dir: cur_dir = "/sd"
            
        sel = 0
        top = 0
        bw, bh = 280, 160
        bx = (W - bw) // 2
        by = (H - bh) // 2
        
        while True:
            items = []
            if cur_dir not in ["/", "/sd"]:
                items.append((".. (UP)", True, "UP"))
                
            try:
                for e in os.ilistdir(cur_dir):
                    name = self._safe_str(e[0])
                    if name.startswith("."): continue
                    is_d = (e[1] == 0x4000)
                    low = name.lower()
                    if is_d:
                        items.append((name, True, "DIR"))
                    elif low.endswith(".bmp") or low.endswith(".raw") or low.endswith(".bin"):
                        items.append((name, False, "IMG"))
            except Exception as ex:
                print("Picker error:", ex)
                
            if not items:
                items = [("<ПУСТО>", False, "")]
                
            sel = max(0, min(sel, len(items) - 1))
            if sel < top: top = sel
            if sel >= top + 7: top = sel - 6
            
            self.tft.fill_rect(bx, by, bw, bh, rgb(20, 24, 36))
            self.tft.rect(bx, by, bw, bh, rgb(0, 210, 255))
            self.tft.fill_rect(bx + 2, by + 2, bw - 4, 18, rgb(28, 32, 44))
            p_title = cur_dir if len(cur_dir) < 22 else ".." + cur_dir[-19:]
            draw_text(self.tft, f"Папка: {p_title}", bx + 8, by + 6, 0xFFFF)
            
            y = by + 26
            for i in range(top, min(len(items), top + 7)):
                name, is_dir, tag = items[i]
                is_cur = (i == sel)
                if is_cur:
                    self.tft.fill_rect(bx + 4, y - 1, bw - 8, 14, rgb(0, 110, 210))
                    
                icon = "<UP> " if tag == "UP" else ("[DIR]" if is_dir else "[IMG]")
                col = rgb(255, 215, 0) if is_dir or tag == "UP" else rgb(255, 80, 180)
                draw_text(self.tft, icon, bx + 6, y + 2, col)
                draw_text(self.tft, name[:22], bx + 68, y + 2, 0xFFFF if is_cur else rgb(220, 225, 235))
                y += 15
                
            self.tft.line(bx, by + bh - 22, bx + bw, by + bh - 22, rgb(45, 55, 75))
            draw_text(self.tft, "ENTER:Выбрать       ESC:Назад", bx + 16, by + bh - 16, rgb(140, 150, 170))
            self.tft.show()
            
            while True:
                ev = self.inputs.get_event()
                if not ev:
                    time.sleep_ms(20); continue
                if ev == 'UP':
                    sel = (sel - 1) % len(items); break
                elif ev == 'DOWN':
                    sel = (sel + 1) % len(items); break
                elif ev in ['ESC', 'BACK']:
                    return None
                elif ev == 'ENTER':
                    name, is_dir, tag = items[sel]
                    if tag == "UP":
                        cur_dir = "/".join(cur_dir.rstrip("/").split("/")[:-1])
                        if not cur_dir: cur_dir = "/"
                        sel = 0; top = 0; break
                    elif is_dir:
                        cur_dir = (cur_dir + "/" + name).replace("//", "/")
                        sel = 0; top = 0; break
                    else:
                        full_f = (cur_dir + "/" + name).replace("//", "/")
                        self.scan_photos(start_dir=cur_dir)
                        if full_f in self.photos:
                            self.current_idx = self.photos.index(full_f)
                        return full_f

    # ------------------------------------------------------------ Показ фото (НА ВЕСЬ ЭКРАН 320x240)
    def show_photo_fast(self, path):
        ext = path.split(".")[-1].lower()

        try:
            tft_mv = memoryview(self.tft.buffer)

            # 1. RAW ФАЙЛЫ (Мгновенное чтение всего экрана)
            if ext in ("raw", "bin"):
                sz = os.stat(path)[6]
                self.tft.fill(0)

                with open(path, "rb") as f:
                    if sz == 320 * 240 * 2:
                        f.readinto(tft_mv)
                    elif sz == 320 * 240 * 3:
                        raw_row = bytearray(320 * 3)
                        for y in range(240):
                            f.readinto(raw_row)
                            decode_row_24(raw_row, tft_mv[y * 320 * 2:], 320)
                    else:
                        f.readinto(tft_mv)

            # 2. BMP ФАЙЛЫ (Все типы с абсолютным позиционированием)
            else:
                with open(path, "rb") as f:
                    header = f.read(54)
                    if header[:2] != b'BM':
                        self.draw_error("Неверный формат")
                        return

                    offset = struct.unpack_from("<I", header, 10)[0]
                    w = struct.unpack_from("<i", header, 18)[0]
                    h_raw = struct.unpack_from("<i", header, 22)[0]
                    bpp = struct.unpack_from("<H", header, 28)[0]

                    is_top_down = (h_raw < 0)
                    h = abs(h_raw)

                    if bpp not in (16, 24, 32):
                        self.draw_error(f"BMP {bpp}b не поддерживается")
                        return

                    bytes_per_pix = bpp // 8
                    row_len = w * bytes_per_pix
                    pad = (4 - (row_len % 4)) % 4
                    stride = row_len + pad
                    raw_row = bytearray(stride)

                    self.tft.fill(0)

                    # Сжатие 640x480 -> 320x240 на весь экран
                    if w >= 600:
                        scale_fn = decode_row_32_scale2 if bpp == 32 else decode_row_24_scale2
                        for y in range(240):
                            src_y = y * 2 if is_top_down else (h - 1) - (y * 2)
                            f.seek(offset + src_y * stride)
                            f.readinto(raw_row)
                            scale_fn(raw_row, tft_mv[y * 320 * 2:], 320)
                    # Стандартный вывод на весь экран (до 240 строк!)
                    else:
                        h_target = min(h, 240)
                        w_target = min(w, 320)
                        for y in range(h_target):
                            src_y = y if is_top_down else (h - 1) - y
                            f.seek(offset + src_y * stride)
                            f.readinto(raw_row)

                            dst = y * 320 * 2
                            if bpp == 32:
                                decode_row_32(raw_row, tft_mv[dst:], w_target)
                            elif bpp == 24:
                                decode_row_24(raw_row, tft_mv[dst:], w_target)
                            elif bpp == 16:
                                tft_mv[dst : dst + w_target * 2] = raw_row[:w_target * 2]

            # ЧИСТЫЙ ЭКРАН БЕЗ НИЖНЕЙ КОНСОЛИ!
            self.tft.show()

        except Exception as e:
            print("Ошибка загрузки:", e)
            self.draw_error("Ошибка файла")

    def draw_error(self, msg):
        self.tft.fill(0x0000)
        self.tft.fill_rect(20, 95, 280, 50, rgb(28, 20, 25))
        self.tft.rect(20, 95, 280, 50, rgb(255, 60, 60))
        draw_text(self.tft, msg, 35, 107, rgb(255, 80, 80))
        draw_text(self.tft, "Нажмите < > чтобы пропустить", 35, 125, 0xFFFF)
        self.tft.show()

    def run(self):
        self.scan_photos()

        if not self.photos:
            self.tft.fill(rgb(14, 18, 28))
            draw_text(self.tft, "ФОТОГАЛЕРЕЯ", 100, 30, 0xFFFF)
            draw_text(self.tft, "Фотографии не найдены!", 60, 80, rgb(255, 215, 0))
            draw_text(self.tft, "Папки: /photo, /sd", 65, 110, rgb(140, 150, 170))
            draw_text(self.tft, "Нажмите O для выбора папки", 45, 140, rgb(0, 210, 255))
            draw_text(self.tft, "ESC : Выход", 120, 180, 0xFFFF)
            self.tft.show()
            while True:
                ev = self.inputs.get_event()
                if ev in ['o', 'O']:
                    picked = self.open_folder_dialog()
                    if picked and self.photos: break
                elif ev in ['BACK', 'ESC']:
                    return
                time.sleep_ms(25)

        self.show_photo_fast(self.photos[self.current_idx])

        while True:
            ev = self.inputs.get_event()
            if ev:
                if ev in ['BACK', 'ESC']:
                    self.beep(600, 25)
                    break
                elif ev in ['RIGHT', 'DOWN']:
                    self.beep(1100, 12)
                    self.current_idx = (self.current_idx + 1) % len(self.photos)
                    self.show_photo_fast(self.photos[self.current_idx])
                elif ev in ['LEFT', 'UP']:
                    self.beep(950, 12)
                    self.current_idx = (self.current_idx - 1) % len(self.photos)
                    self.show_photo_fast(self.photos[self.current_idx])
                elif ev in ['o', 'O']:
                    picked = self.open_folder_dialog()
                    if picked and self.photos:
                        self.show_photo_fast(self.photos[self.current_idx])
            time.sleep_ms(20)

    def run_from_file(self, start_path):
        clean_path = start_path.replace("//", "/")
        folder = "/".join(clean_path.rstrip("/").split("/")[:-1])
        if not folder: folder = "/"

        self.scan_photos(start_dir=folder)

        target_norm = clean_path.lower()
        target_name = clean_path.split("/")[-1].lower()
        
        found_idx = -1
        for idx, p in enumerate(self.photos):
            if p.lower().replace("//", "/") == target_norm:
                found_idx = idx
                break
        
        if found_idx == -1:
            for idx, p in enumerate(self.photos):
                if p.split("/")[-1].lower() == target_name:
                    found_idx = idx
                    break

        if found_idx != -1:
            self.current_idx = found_idx
        else:
            self.photos.insert(0, clean_path)
            self.current_idx = 0

        if self.photos:
            self.show_photo_fast(self.photos[self.current_idx])
            while True:
                ev = self.inputs.get_event()
                if ev:
                    if ev in ('BACK', 'ESC'):
                        self.beep(600, 25)
                        break
                    elif ev in ['RIGHT', 'DOWN']:
                        self.beep(1100, 12)
                        self.current_idx = (self.current_idx + 1) % len(self.photos)
                        self.show_photo_fast(self.photos[self.current_idx])
                    elif ev in ['LEFT', 'UP']:
                        self.beep(950, 12)
                        self.current_idx = (self.current_idx - 1) % len(self.photos)
                        self.show_photo_fast(self.photos[self.current_idx])
                    elif ev in ['o', 'O']:
                        picked = self.open_folder_dialog()
                        if picked and self.photos:
                            self.show_photo_fast(self.photos[self.current_idx])
                time.sleep_ms(20)