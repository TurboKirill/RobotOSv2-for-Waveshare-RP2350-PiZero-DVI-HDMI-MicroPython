# app_player.py - Всеядный аудиоплеер RobotOS (DVI 320x240)
# Автопоиск по всем подпапкам, русские имена (CP1251), фильтр дубликатов, громкость
import os
import time
import math
import struct
import gc
import micropython
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240
TB_H = 22
WIN_H = H - TB_H  # 218px

# Палитра
C_BG       = rgb(14, 18, 28)       # Тёмно-синий фон
C_HEADER   = rgb(28, 32, 44)       # Шапка окна
C_CARD     = rgb(22, 28, 42)       # Карточка трека
C_BORDER   = rgb(45, 55, 75)       # Границы
C_ACCENT   = rgb(0, 210, 255)      # Неоново-голубой
C_GREEN    = rgb(0, 230, 120)      # Зелёный Play
C_YELLOW   = rgb(255, 215, 0)      # Жёлтый Pause / Папки
C_WHITE    = 0xFFFF
C_GRAY     = rgb(140, 150, 170)
C_SEL_BG   = rgb(0, 110, 210)      # Выделение в проводнике

# ================= МАШИННЫЙ КОД ДЛЯ РЕГУЛИРОВКИ ГРОМКОСТИ =================
@micropython.viper
def apply_volume(buf_ptr: ptr8, num_bytes: int, vol_factor: int):
    """Мгновенное масштабирование PCM в машинном коде ARM Cortex-M33"""
    idx = 0
    while idx < num_bytes:
        low = int(buf_ptr[idx])
        high = int(buf_ptr[idx + 1])
        sample = low | (high << 8)
        if sample >= 32768:
            sample -= 65536
        sample = (sample * vol_factor) // 100
        if sample < 0:
            sample += 65536
        buf_ptr[idx] = sample & 0xFF
        buf_ptr[idx + 1] = (sample >> 8) & 0xFF
        idx += 2


class MusicPlayerApp:
    def __init__(self, tft, audio, inputs, config=None, filepath=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        if config:
            self.cfg = config
        else:
            from machine import RTC
            dt = RTC().datetime() # (год, месяц, день, день_недели, часы, минуты, секунды, ...)
            self.cfg = {"vol_ui": 30, "mute": False, "hour": dt[4], "minute": dt[5]}
        
        self.playlist = []
        self.cur_idx = 0
        self.volume = 35       # Стартовая громкость 35%
        self.is_paused = False
        self.initial_file = filepath

    def _decode_name(self, raw):
        """Безопасная расшифровка русских имен в кодировке Windows CP1251"""
        if isinstance(raw, str):
            return raw
        try:
            return raw.decode("utf-8")
        except:
            pass
        # Декодируем русские буквы из кодировки Windows CP1251
        out = []
        for b in raw:
            if 0xC0 <= b <= 0xFF: # Русские буквы А..я
                out.append(chr(0x0410 + (b - 0xC0)))
            elif 32 <= b < 127:
                out.append(chr(b))
            else:
                out.append("_")
        return "".join(out)

    def scan_music(self, folder=None):
        """Безопасный вычит всех треков без обрыва на скрытых метках Windows"""
        self.playlist = []
        seen = set()

        if self.initial_file:
            self.playlist.append(self.initial_file)
            seen.add(self.initial_file.split("/")[-1].lower())

        # Проверяем все возможные варианты папки WAV на SD-карте и в памяти
        search_dirs = [folder] if folder else [
            "/sd/WAV", "/sd/wav", "/sd/Wav", 
            "/sd/music", "/sd/Music", 
            "/sd", "/"
        ]

        for d in search_dirs:
            if not d: continue
            try:
                # Читаем в сырых байтах d.encode() — генератор больше НЕ ОБРЫВАЕТСЯ на середине!
                d_bytes = d.encode() if isinstance(d, str) else d
                for entry in os.ilistdir(d_bytes):
                    raw_name = entry[0]
                    # Безопасное чтение имени
                    if isinstance(raw_name, bytes):
                        try:
                            name = raw_name.decode("utf-8")
                        except:
                            name = "".join(chr(b) if 32 <= b < 127 else "_" for b in raw_name)
                    else:
                        name = str(raw_name)

                    # Пропускаем служебный мусор Windows/Mac
                    if name.startswith(".") or name.startswith("._") or name.startswith("$"):
                        continue

                    # Проверяем расширение .wav / .WAV
                    if name.lower().endswith(".wav"):
                        full = (d + "/" + name).replace("//", "/")
                        fname_key = name.lower()
                        # Защита от дубликатов
                        if fname_key not in seen:
                            seen.add(fname_key)
                            self.playlist.append(full)
            except:
                pass

        self.playlist.sort(key=lambda x: x.split("/")[-1].lower())

        if self.initial_file and self.initial_file in self.playlist:
            self.cur_idx = self.playlist.index(self.initial_file)
        elif self.playlist:
            self.cur_idx = 0

        print(f"🎵 Плеер: найдено {len(self.playlist)} треков -> {self.playlist}")

    # ------------------------------------------------------------ Всплывающий выбор трека
    def open_file_dialog(self):
        """Всплывающий мини-проводник для выбора музыки из любых папок"""
        cur_dir = "/sd/WAV"
        try: os.stat(cur_dir)
        except: cur_dir = "/sd"

        if self.playlist:
            cur_dir = "/".join(self.playlist[self.cur_idx].split("/")[:-1])
            if not cur_dir: cur_dir = "/sd"

        sel = 0
        top = 0
        visible_rows = 7
        bw, bh = 280, 160
        bx = (W - bw) // 2
        by = (WIN_H - bh) // 2

        while True:
            items = []
            if cur_dir not in ["/", "/sd"]:
                items.append((".. (UP)", True, "UP"))

            try:
                for e in os.ilistdir(cur_dir):
                    name = self._decode_name(e[0])
                    if name.startswith(".") or name.startswith("._"): continue
                    is_dir = (e[1] == 0x4000)
                    if is_dir:
                        items.append((name, True, "DIR"))
                    elif name.lower().endswith(".wav"):
                        items.append((name, False, "WAV"))
            except Exception as ex:
                print("Picker error:", ex)

            if not items:
                items = [("<ПУСТО>", False, "")]

            sel = max(0, min(sel, len(items) - 1))
            if sel < top: top = sel
            if sel >= top + visible_rows: top = sel - visible_rows + 1

            self.tft.fill_rect(bx, by, bw, bh, rgb(20, 24, 36))
            self.tft.rect(bx, by, bw, bh, C_ACCENT)
            self.tft.fill_rect(bx + 2, by + 2, bw - 4, 18, C_HEADER)

            p_title = cur_dir if len(cur_dir) < 22 else ".." + cur_dir[-19:]
            draw_text(self.tft, f"Папка: {p_title}", bx + 8, by + 6, C_WHITE)

            y = by + 26
            for i in range(top, min(len(items), top + visible_rows)):
                name, is_dir, tag = items[i]
                is_cursor = (i == sel)

                if is_cursor:
                    self.tft.fill_rect(bx + 4, y - 1, bw - 8, 14, C_SEL_BG)

                icon = "<UP> " if tag == "UP" else ("[DIR]" if is_dir else "[WAV]")
                col = C_YELLOW if is_dir or tag == "UP" else C_GREEN

                draw_text(self.tft, icon, bx + 6, y + 2, col)
                name_col = C_WHITE if is_cursor else rgb(220, 225, 235)
                draw_text(self.tft, name[:22], bx + 68, y + 2, name_col)
                y += 15

            self.tft.line(bx, by + bh - 22, bx + bw, by + bh - 22, C_BORDER)
            draw_text(self.tft, "ENTER:Выбрать       ESC:Назад", bx + 16, by + bh - 16, C_GRAY)
            self.tft.show()

            while True:
                ev = self.inputs.get_event()
                if not ev:
                    time.sleep_ms(20)
                    continue

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
                        target_file = (cur_dir + "/" + name).replace("//", "/")
                        self.initial_file = target_file
                        self.scan_music(folder=cur_dir)
                        return target_file

    # ------------------------------------------------------------ Отрисовка UI плеера
    def draw_player_ui(self):
        # 1. Шапка окна (Y = 0 .. 19)
        self.tft.fill_rect(0, 0, W, 20, C_HEADER)
        self.tft.line(0, 19, W, 19, C_BORDER)
        draw_text(self.tft, "Аудио Плеер", 10, 6, C_WHITE)
        self.tft.text("Esc", 294, 6, C_WHITE)

        # 2. Фон рабочей области
        self.tft.fill_rect(0, 20, W, 198, C_BG)

        if not self.playlist:
            return

        track_path = self.playlist[self.cur_idx]
        fname = track_path.split("/")[-1]

        # Номер трека
        count_str = f"ТРЕК {self.cur_idx + 1} ИЗ {len(self.playlist)}"
        draw_text(self.tft, count_str, 20, 32, C_GRAY)

        # 3. Карточка трека (Кассета)
        card_x, card_y, card_w, card_h = 20, 48, 280, 72
        self.tft.fill_rect(card_x, card_y, card_w, card_h, C_CARD)
        self.tft.rect(card_x, card_y, card_w, card_h, C_BORDER)

        # Имя трека через draw_text (с поддержкой русского языка!)
        disp_name = fname if len(fname) <= 30 else fname[:28] + "~"
        draw_text(self.tft, disp_name, card_x + 12, card_y + 16, C_WHITE)

        # Статус воспроизведения
        if self.is_paused:
            status_txt = "[ II ПАУЗА ]"
            status_col = C_YELLOW
        else:
            status_txt = "[ > ИГРАЕТ ]"
            status_col = C_GREEN
        draw_text(self.tft, status_txt, card_x + 12, card_y + 42, status_col)

        # 4. Шкала громкости
        self.draw_volume_bar()

        # 5. Панель горячих клавиш
        self.tft.line(20, 168, 300, 168, C_BORDER)
        draw_text(self.tft, "ВЛЕВО/ВПРАВО : Пред / След трек", 20, 175, C_WHITE)
        draw_text(self.tft, "ВВЕРХ/ВНИЗ   : Громкость +/- (5%)", 20, 187, C_ACCENT)
        draw_text(self.tft, "O : Выбрать файл      ENTER : Пауза", 20, 199, C_YELLOW)

        # 6. Системная панель задач RobotOS
        draw_system_taskbar(self.tft, self.cfg, active_tab="Плеер", tab_icon="player")

        self.tft.show()

    def draw_volume_bar(self):
        bar_x, bar_y = 20, 130
        self.tft.fill_rect(bar_x, bar_y, 280, 30, C_BG)

        vol_str = f"ГРОМКОСТЬ: {self.volume}%"
        draw_text(self.tft, vol_str, bar_x, bar_y, C_WHITE)

        self.tft.rect(bar_x, bar_y + 14, 280, 10, C_BORDER)
        fill_w = int(276 * (self.volume / 100))
        if fill_w > 0:
            self.tft.fill_rect(bar_x + 2, bar_y + 16, fill_w, 6, C_ACCENT)
        self.tft.show()

    # ------------------------------------------------------------ Воспроизведение
    def play_current_track(self):
        if not self.playlist: return 'EXIT'

        track_path = self.playlist[self.cur_idx]
        self.draw_player_ui()

        try:
            with open(track_path, "rb") as f:
                header = f.read(128)
                pos = header.find(b'data')
                data_offset = (pos + 8) if pos != -1 else 44
                f.seek(data_offset)

                buf = bytearray(2048)

                while True:
                    ev = self.inputs.get_event()
                    if ev:
                        if ev in ['BACK', 'ESC']:
                            return 'EXIT'
                        elif ev in ['ENTER', ' ']:
                            self.is_paused = not self.is_paused
                            self.draw_player_ui()
                        elif ev in ['o', 'O', 'f', 'F']:
                            picked = self.open_file_dialog()
                            if picked:
                                return 'CHANGE'
                            else:
                                self.draw_player_ui()
                        elif ev == 'UP':
                            self.volume = min(100, self.volume + 5)
                            self.draw_volume_bar()
                        elif ev == 'DOWN':
                            self.volume = max(0, self.volume - 5)
                            self.draw_volume_bar()
                        elif ev == 'RIGHT':
                            self.cur_idx = (self.cur_idx + 1) % len(self.playlist)
                            return 'NEXT'
                        elif ev == 'LEFT':
                            self.cur_idx = (self.cur_idx - 1) % len(self.playlist)
                            return 'PREV'

                    if self.is_paused:
                        time.sleep_ms(30)
                        continue

                    n = f.readinto(buf)
                    if not n:
                        self.cur_idx = (self.cur_idx + 1) % len(self.playlist)
                        return 'NEXT'

                    if self.volume < 100:
                        apply_volume(buf, n, self.volume)

                    self.audio.write(buf[:n])

        except Exception as e:
            print(f"Ошибка воспроизведения {track_path}:", e)
            self.cur_idx = (self.cur_idx + 1) % len(self.playlist)
            return 'NEXT'

    def run(self):
        self.scan_music()

        if not self.playlist:
            self.tft.fill_rect(0, 0, W, 20, C_HEADER)
            draw_text(self.tft, "Аудио Плеер", 10, 6, C_WHITE)
            self.tft.fill_rect(0, 20, W, 198, C_BG)
            draw_text(self.tft, "Файлы WAV не найдены!", 60, 70, C_WHITE)
            draw_text(self.tft, "Нажмите O чтобы выбрать файл", 40, 100, C_YELLOW)
            draw_text(self.tft, "Или ESC для выхода", 75, 140, C_GRAY)
            draw_system_taskbar(self.tft, self.cfg, active_tab="Плеер", tab_icon="player")
            self.tft.show()

            while True:
                ev = self.inputs.get_event()
                if ev in ['o', 'O']:
                    picked = self.open_file_dialog()
                    if picked: break
                elif ev in ['BACK', 'ESC']:
                    return
                time.sleep_ms(25)

        while True:
            res = self.play_current_track()
            if res == 'EXIT':
                break