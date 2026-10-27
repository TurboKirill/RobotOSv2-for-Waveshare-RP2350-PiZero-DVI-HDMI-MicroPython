# app_video.py - Видеоплеер Windows Media Player для RobotOS (DVI 320x240)
# Потоковый 160x120 -> 320x240 апскейл (буфер всего 3.2 КБ, без MemoryError!)
import os
import time
import math
import struct
import gc
import machine
import micropython
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240
TB_H = 22
WIN_H = H - TB_H

C_BG        = rgb(14, 18, 24)
C_HEADER    = rgb(28, 32, 44)
C_CARD      = rgb(24, 28, 38)
C_BORDER    = rgb(48, 56, 76)
C_ORANGE    = rgb(255, 140, 20)
C_WHITE     = 0xFFFF
C_GRAY      = rgb(140, 150, 170)
C_DARK_GRAY = rgb(90, 100, 120)

FPS         = 25
FRAME_MS    = 1000 // FPS  # 40 мс на кадр
AUDIO_RATE  = 22050

# ================= МАШИННЫЙ КОД CORTEX-M33 (Апскейл пачками) =================
@micropython.viper
def scale_chunk_160_to_320(src: ptr8, dst: ptr8, start_y: int, num_lines: int):
    """Растягивает 10 строк 160px в 20 строк 320px за 0.09 мс"""
    s_ptr = ptr16(src)
    d_ptr = ptr32(dst)
    s_idx = 0
    for line in range(num_lines):
        y = start_y + line
        d1 = (y * 2) * 160
        d2 = d1 + 160
        for x in range(160):
            p = int(s_ptr[s_idx])
            w = p | (p << 16)
            d_ptr[d1] = w
            d_ptr[d2] = w
            s_idx += 1
            d1 += 1
            d2 += 1

@micropython.viper
def apply_volume(buf: ptr8, n: int, vol: int):
    """Регулировка громкости аудиодорожки"""
    i = 0
    while i < n:
        low = int(buf[i])
        high = int(buf[i + 1])
        s = low | (high << 8)
        if s >= 32768: s -= 65536
        s = (s * vol) // 100
        if s < 0: s += 65536
        buf[i] = s & 0xFF
        buf[i + 1] = (s >> 8) & 0xFF
        i += 2

def read_exact(f, buf):
    """Точное чтение через границы кластеров без сдвигов"""
    mv = memoryview(buf)
    total = 0
    need = len(buf)
    while total < need:
        n = f.readinto(mv[total:])
        if not n: break
        total += n
    return total


class VideoPlayerApp:
    def __init__(self, tft, audio, inputs, config=None, filepath=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False, "hour": 20, "minute": 45}
        
        self.playlist = []
        self.cur_idx = 0
        self.volume = 50
        self.initial_file = filepath

        # ВЫДЕЛЯЕМ КРОШЕЧНЫЕ БУФЕРЫ ВСЕГО ОДИН РАЗ (3.2 КБ + 2 КБ = 5.2 КБ!)
        gc.collect()
        self.chunk_buf = bytearray(10 * 160 * 2) # 3200 байт
        self.chunk_mv  = memoryview(self.chunk_buf)
        self.audio_buf = bytearray(2048)         # 2048 байт
        self.audio_mv  = memoryview(self.audio_buf)

    def boost_spi(self):
        """Разгон SPI SD-карты до 25 МГц"""
        try:
            machine.SPI(1).init(baudrate=25000000)
        except Exception as e:
            print("SPI boost warning:", e)

    def scan_videos(self):
        self.playlist = []
        seen = set()

        if self.initial_file:
            self.playlist.append(self.initial_file)
            seen.add(self.initial_file.lower())

        search_dirs = ["/sd/video", "/sd/movies", "/sd/photo", "/sd", "/"]

        for d in search_dirs:
            try:
                d_bytes = d.encode() if isinstance(d, str) else d
                for entry in os.ilistdir(d_bytes):
                    raw_n = entry[0]
                    name = raw_n.decode() if isinstance(raw_n, bytes) else str(raw_n)
                    if name.startswith(".") or name.startswith("._") or name.startswith("audio"): 
                        continue
                    low = name.lower()
                    if low.endswith(".raw") or low.endswith(".rvid"):
                        full = (d + "/" + name).replace("//", "/")
                        if full.lower() not in seen:
                            seen.add(full.lower())
                            self.playlist.append(full)
            except:
                pass

        self.playlist.sort()

    def play_video(self, v_path):
        """Плавное воспроизведение видео со звуком"""
        self.boost_spi()
        gc.collect()

        tft_buf = self.tft.buffer
        file_size = os.stat(v_path)[6]

        # 160x120 = 38400 байт/кадр
        frame_size = 160 * 120 * 2
        total_frames = file_size // frame_size
        audio_chunk = (AUDIO_RATE * 2) // FPS # 1764 байта на кадр

        # Ищем аудиофайл .wav или .raw
        stem = v_path.rsplit(".", 1)[0]
        a_path = stem + ".wav"
        if not self._file_exists(a_path):
            a_path = stem + ".raw"
            if "video" in a_path.lower():
                a_path = a_path.replace("video", "audio").replace("VIDEO", "AUDIO")

        has_audio = False
        a_file = None
        if self._file_exists(a_path):
            try:
                a_file = open(a_path, "rb")
                if a_path.lower().endswith(".wav"):
                    hdr = a_file.read(128)
                    pos = hdr.find(b"data")
                    a_file.seek((pos + 8) if pos != -1 else 44)
                has_audio = True
                print("🔊 Аудио подключено:", a_path)
            except Exception as e:
                print("Аудио ошибка:", e)

        v_file = open(v_path, "rb")

        self.tft.fill(0)
        self.tft.show()

        cur_frame = 0
        is_paused = False

        try:
            while cur_frame < total_frames:
                t_start = time.ticks_ms()

                # Управление
                ev = self.inputs.get_event()
                if ev:
                    if ev in ("BACK", "ESC"):
                        break
                    elif ev in ("ENTER", " "):
                        is_paused = not is_paused
                        if is_paused:
                            self.tft.fill_rect(100, 100, 120, 36, rgb(20, 24, 34))
                            self.tft.rect(100, 100, 120, 36, C_ORANGE)
                            draw_text(self.tft, "[ II ПАУЗА ]", 116, 112, C_WHITE)
                            self.tft.show()
                    elif ev == "UP":
                        self.volume = min(100, self.volume + 5)
                    elif ev == "DOWN":
                        self.volume = max(0, self.volume - 5)

                if is_paused:
                    time.sleep_ms(30)
                    continue

                # 1. Читаем и выводим звук порцией ровно на 1 кадр
                if has_audio:
                    n_aud = read_exact(a_file, self.audio_mv[:audio_chunk])
                    if n_aud:
                        if self.volume < 100:
                            apply_volume(self.audio_buf, n_aud, self.volume)
                        self.audio.write(self.audio_mv[:n_aud])

                # 2. Читаем видеокадр 12 пачками по 3200 байт (НИКАКИХ MemoryError!)
                eof = False
                for chunk_idx in range(12):
                    n = read_exact(v_file, self.chunk_buf)
                    if n < 3200:
                        eof = True
                        break
                    scale_chunk_160_to_320(self.chunk_buf, tft_buf, chunk_idx * 10, 10)

                if eof:
                    break

                # 3. Выводим готовый кадр
                self.tft.show()
                cur_frame += 1

                # Точный тайминг 25 FPS (40 мс)
                dt = time.ticks_diff(time.ticks_ms(), t_start)
                wait_ms = FRAME_MS - dt
                if wait_ms > 0:
                    time.sleep_ms(wait_ms)

        finally:
            v_file.close()
            if a_file:
                a_file.close()
            gc.collect()

    def _file_exists(self, p):
        try:
            os.stat(p)
            return True
        except:
            return False

    def run(self):
        self.scan_videos()

        if not self.playlist:
            t = self.tft
            t.fill_rect(0, 0, W, 20, C_HEADER)
            draw_text(t, "Windows Media Player", 10, 6, C_WHITE)
            t.fill_rect(0, 20, W, 198, C_BG)
            draw_text(t, "Видеофайлы (.raw) не найдены!", 40, 70, C_ORANGE)
            draw_text(t, "Положите video.raw в /sd/video", 30, 100, C_WHITE)
            draw_system_taskbar(t, self.cfg, active_tab="Видео", tab_icon="video")
            t.show()
            while True:
                if self.inputs.get_event() in ("BACK", "ESC"):
                    return
                time.sleep_ms(25)

        sel = 0
        while True:
            t = self.tft
            t.fill_rect(0, 0, W, 20, C_HEADER)
            draw_text(t, "Windows Media Player", 10, 6, C_WHITE)
            t.text("Esc", 294, 6, C_WHITE)

            t.fill_rect(0, 20, W, 198, C_BG)
            draw_text(t, "ВИДЕОТЕКА MICROSD (25 FPS)", 14, 25, C_WHITE)

            y = 44
            for i, p in enumerate(self.playlist):
                is_cur = (i == sel)
                t.fill_rect(12, y, 296, 26, rgb(36, 44, 60) if is_cur else C_CARD)
                t.rect(12, y, 296, 26, C_ORANGE if is_cur else C_BORDER)
                draw_text(t, "[▶] " + p.split("/")[-1][:26], 20, y + 6, C_WHITE if is_cur else C_GRAY)
                y += 30

            draw_text(t, "ENTER: Запуск    ESC: Выход", 12, 198, rgb(100, 110, 130))
            draw_system_taskbar(t, self.cfg, active_tab="Видео", tab_icon="video")
            t.show()

            while True:
                ev = self.inputs.get_event()
                if ev:
                    break
                time.sleep_ms(25)

            if ev in ("BACK", "ESC"):
                return
            elif ev == "UP":
                sel = (sel - 1) % len(self.playlist)
            elif ev == "DOWN":
                sel = (sel + 1) % len(self.playlist)
            elif ev in ("ENTER", " "):
                self.play_video(self.playlist[sel])