# app_cmd.py - Командная строка RobotOS (CMD.EXE) в стиле Windows
# DVI 320x240, эмуляция дисков C:\ и D:\, запуск скриптов, история команд
import os
import time
import math
import struct
import gc
import machine
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240
TB_H = 22
WIN_H = H - TB_H  # 218px

# Палитра классического CMD
C_BG       = 0x0000            # Глубокий чёрный
C_TEXT     = rgb(204, 204, 204)# Классический светло-серый текст Windows CMD
C_WHITE    = 0xFFFF
C_GREEN    = rgb(0, 230, 120)
C_CYAN     = rgb(0, 220, 255)
C_YELLOW   = rgb(255, 215, 0)
C_RED      = rgb(255, 80, 80)
C_GRAY     = rgb(140, 150, 170)# Серая статистика (добавлен!)
C_TITLE_BG = rgb(24, 26, 32)
C_BORDER   = rgb(45, 52, 65)

MAX_ROWS   = 16                # Вмещается 16 строк текста
MAX_COLS   = 38                # До 38 символов в строку
ROW_H      = 12
MAX_LINES  = 200               # Размер буфера истории вывода (для прокрутки)
SCROLL_STEP = 4                # Сколько строк за одно нажатие прокрутки
VIS_LINES  = MAX_ROWS - 1      # Сколько строк вывода видно на экране


class CmdApp:
    def __init__(self, tft, audio, inputs, config=None):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False, "hour": 20, "minute": 45}

        # Текущий путь в файловой системе
        self.cur_path = "/sd" if self._sd_present() else "/"

        # Буфер строк терминала
        self.lines = [
            "Kirill Dmitriev RobotOS cmd_v1",
            "(C) Корпорация RobotOS, 2026.",
            "",
            "Введите HELP для вызова справки.",
            ""
        ]

        # Прокрутка: на сколько строк мы отмотали вверх (0 = внизу)
        self.scroll = 0

        # Адрес "удалённого" хоста после CONNECT (None = локальная консоль)
        self.remote_host = None

        # Ввод команды
        self.cmd_buffer = ""
        self.history = []
        self.hist_idx = 0
        self.cursor_blink = True
        self.last_blink = time.ticks_ms()

    def _sd_present(self):
        try:
            os.stat("/sd")
            return True
        except:
            return False

    def beep(self, freq=1200, ms=8):
        if self.cfg.get("mute") or self.cfg.get("vol_ui", 30) == 0:
            return
        rate = 22050
        samples = max(2, int(rate / freq))
        cycle = bytearray(samples * 2)
        amp = int(800 * (self.cfg.get("vol_ui", 30) / 100))
        for i in range(samples):
            v = int(amp * math.sin(2 * math.pi * i / samples))
            struct.pack_into("<h", cycle, i * 2, v)
        for _ in range(max(1, int((ms / 1000) * freq))):
            self.audio.write(cycle)

    # ------------------------------------------------------------ Маппинг путей под Windows (C:\ и D:\)
    def get_prompt(self):
        if self.remote_host:
            return f"root@{self.remote_host}:~# "
        if self.cur_path.startswith("/sd"):
            rel = self.cur_path[3:].replace("/", "\\")
            return f"D:{rel}>"
        else:
            rel = self.cur_path.replace("/", "\\")
            if not rel.startswith("\\"): rel = "\\" + rel
            return f"C:{rel}>"

    def _safe_name(self, raw):
        """Имя файла из bytes в str без падения на 'битых' (не UTF-8) именах."""
        if isinstance(raw, str):
            return raw
        try:
            return raw.decode("utf-8")
        except Exception:
            return "".join(chr(b) if 32 <= b < 127 else "?" for b in raw)

    def list_dir(self, path):
        """Список (имя, is_dir, размер). Путь передаём как bytes, чтобы
        MicroPython не бросал UnicodeError на именах не в UTF-8."""
        out = []
        for e in os.ilistdir(path.encode()):
            name = self._safe_name(e[0])
            out.append((name, e[1] == 0x4000, e[3] if len(e) > 3 else 0))
        return out

    def resolve_case(self, parent, name):
        """Находит реальное имя папки/файла на диске без учёта регистра."""
        try:
            name_low = name.lower()
            for e in os.ilistdir(parent.encode()):
                real = self._safe_name(e[0])
                if real.lower() == name_low:
                    return real
        except:
            pass
        return name

    def resolve_path(self, target):
        """Переводит DOS-путь (D:\wav) в точный регистронезависимый Unix-путь (/sd/WAV)."""
        target = target.strip().replace("\\", "/")
        
        # Определение диска
        if target.upper().startswith("C:"):
            cur = "/"
            parts = [p for p in target[2:].split("/") if p]
        elif target.upper().startswith("D:"):
            cur = "/sd"
            parts = [p for p in target[2:].split("/") if p]
        elif target.startswith("/"):
            cur = "/sd" if target.startswith("/sd") else "/"
            parts = [p for p in target.split("/") if p]
            if cur == "/sd" and parts and parts[0] == "sd":
                parts.pop(0)
        else:
            cur = self.cur_path
            parts = [p for p in target.split("/") if p]

        # Пошаговый поиск точных имён папок с диска
        for part in parts:
            if part == "..":
                if cur not in ["/", "/sd"]:
                    cur = "/".join(cur.rstrip("/").split("/")[:-1])
                    if not cur: cur = "/"
            elif part == ".":
                continue
            else:
                real_name = self.resolve_case(cur, part)
                cur = (cur + "/" + real_name).replace("//", "/")

        return cur.rstrip("/") if cur != "/" else "/"

    def print_line(self, text, color=C_TEXT):
        # Новый вывод всегда возвращает экран вниз
        self.scroll = 0
        while len(text) > MAX_COLS:
            self.lines.append((text[:MAX_COLS], color))
            text = text[MAX_COLS:]
        self.lines.append((text, color))
        if len(self.lines) > MAX_LINES:
            self.lines = self.lines[-MAX_LINES:]

    # ------------------------------------------------------------ Прокрутка истории
    def scroll_by(self, delta):
        """delta > 0 - вверх (к старым строкам), delta < 0 - вниз."""
        max_scroll = max(0, len(self.lines) - VIS_LINES)
        self.scroll = max(0, min(max_scroll, self.scroll + delta))

    # ------------------------------------------------------------ Строка прогресса в стиле wget
    def _dl_bar(self, pct, total_kb):
        """' 45%[==========>             ]  180K' - 36 символов, имя файла отдельно."""
        width = 24
        if pct >= 100:
            bar = "=" * width
        else:
            filled = pct * width // 100
            bar = "=" * filled + ">" + " " * (width - 1 - filled)
        done_kb = total_kb * pct // 100
        return f"{pct:>3}%[{bar}] {done_kb:>4}K"

    # ------------------------------------------------------------ Команды "удалённого" хоста
    def _remote_command(self, cmd):
        """Фейковые команды после CONNECT. True - команда обработана."""
        host = self.remote_host
        if cmd in ["EXIT", "QUIT", "LOGOUT", "DISCONNECT", "DC"]:
            self.print_line(f"Соединение с {host} закрыто.", C_YELLOW)
            self.remote_host = None
            return True
        if cmd == "WHOAMI":
            self.print_line("root", C_WHITE)
            return True
        if cmd == "PWD":
            self.print_line("/root", C_WHITE)
            return True
        if cmd == "ID":
            self.print_line("uid=0(root) gid=0(root) groups=0(root)", C_WHITE)
            return True
        if cmd == "UNAME":
            self.print_line("Linux pentagon-gw 5.15.0 x86_64", C_WHITE)
            return True
        if cmd in ["LS", "DIR"]:
            self.print_line("bin  etc  home  root  tmp", C_CYAN)
            self.print_line("secret_plans.txt  launch_codes.bak", C_WHITE)
            return True
        return False

    # ------------------------------------------------------------ Исполнение команд
    def execute_command(self, cmd_raw):
        cmd_clean = cmd_raw.strip()
        if not cmd_clean:
            return

        self.history.append(cmd_clean)
        self.hist_idx = len(self.history)
        parts = cmd_clean.split()
        cmd = parts[0].upper()
        args = parts[1:]

        # 0. Если мы "подключены" - сначала пробуем удалённые команды
        if self.remote_host and self._remote_command(cmd):
            return None

        # 1. Переключение дисков C: и D:
        if cmd == "C:":
            self.cur_path = "/"
            return
        elif cmd == "D:":
            if self._sd_present():
                self.cur_path = "/sd"
            else:
                self.print_line("Устройство D: не готово (SD не найдена).", C_RED)
            return

        # 2. HELP
        if cmd in ["HELP", "?"]:
            self.print_line("Команды RobotOS CMD:", C_YELLOW)
            self.print_line(" DIR, LS         - Список файлов", C_CYAN)
            self.print_line(" CD <папка>      - Смена каталога", C_CYAN)
            self.print_line(" C:, D:          - Выбор диска", C_CYAN)
            self.print_line(" TYPE, CAT <файл>- Просмотр текста", C_CYAN)
            self.print_line(" MD, MKDIR <имя> - Создать папку", C_CYAN)
            self.print_line(" DEL, RM <файл>  - Удалить файл", C_CYAN)
            self.print_line(" COPY <src> <dst>- Копировать", C_CYAN)
            self.print_line(" PY <файл.py>    - Запуск скрипта", C_CYAN)
            self.print_line(" MEM             - Статистика ОЗУ", C_CYAN)
            self.print_line(" CLS, CLEAR      - Очистить экран", C_CYAN)
            self.print_line(" REBOOT, EXIT    - Перезагрузка/Выход", C_CYAN)
            self.print_line(" PING <ip>       - Проверка сети", C_CYAN)
            self.print_line(" CONNECT <ip>    - Подключение", C_CYAN)
            self.print_line(" DISCONNECT      - Разорвать связь", C_CYAN)
            self.print_line(" DOWNLOAD FILES  - Секретные архивы ;)", C_CYAN)
            self.print_line(" PgUp/PgDn       - Прокрутка вывода", C_GRAY)

        # 3. CLS
        elif cmd in ["CLS", "CLEAR"]:
            self.lines.clear()
            self.scroll = 0

        # 4. VER
        elif cmd == "VER":
            self.print_line("RobotOS Command Prompt [v2.0.26]", C_WHITE)
            self.print_line("Платформа: Raspberry Pi RP2350B DVI", C_TEXT)

        # 5. DIR / LS
        elif cmd in ["DIR", "LS"]:
            try:
                raw_entries = self.list_dir(self.cur_path)
                raw_entries.sort(key=lambda x: (not x[1], x[0].lower()))

                self.print_line(f" Содержимое {self.get_prompt()[:-1]}", C_YELLOW)
                files_cnt, dirs_cnt, total_bytes = 0, 0, 0

                for name, is_dir, sz in raw_entries:
                    # Имя слева (25 символов, длинное обрезается с ~), размер справа
                    name_col = name if len(name) <= 25 else name[:24] + "~"
                    if is_dir:
                        self.print_line(f" {name_col:<25} {'<DIR>':>10}", C_YELLOW)
                        dirs_cnt += 1
                    else:
                        sz_str = f"{sz//1024} KB" if sz > 1024 else f"{sz} B"
                        self.print_line(f" {name_col:<25} {sz_str:>10}", C_TEXT)
                        files_cnt += 1
                        total_bytes += sz

                # Статистика
                st = os.statvfs("/sd" if self.cur_path.startswith("/sd") else "/")
                free_mb = (st[0] * st[3]) // (1024 * 1024)
                self.print_line(f" Файлов: {files_cnt}, Папок: {dirs_cnt}", C_GRAY)
                self.print_line(f" Свободно: {free_mb} МБ", C_GREEN)
            except Exception as e:
                err_str = repr(e) if not str(e) else str(e)
                self.print_line(f"Ошибка DIR: {err_str}", C_RED)

        # 6. CD
        elif cmd == "CD":
            if not args:
                self.print_line(self.get_prompt()[:-1], C_WHITE)
            elif args[0] == "..":
                if self.cur_path not in ["/", "/sd"]:
                    p = "/".join(self.cur_path.rstrip("/").split("/")[:-1])
                    self.cur_path = p if p else "/"
                else:
                    self.cur_path = "/"
            elif args[0] in ["\\", "/"]:
                self.cur_path = "/sd" if self.cur_path.startswith("/sd") else "/"
            else:
                target = self.resolve_path(args[0])
                try:
                    if (os.stat(target)[0] & 0x4000) != 0:
                        self.cur_path = target
                    else:
                        self.print_line("Системе не удается найти указанный путь.", C_RED)
                except:
                    self.print_line("Путь не найден.", C_RED)

        # 7. TYPE / CAT
        elif cmd in ["TYPE", "CAT"]:
            if not args:
                self.print_line("Синтаксис: TYPE <имя_файла>", C_GRAY)
            else:
                target = self.resolve_path(args[0])
                try:
                    with open(target, "r") as f:
                        for _ in range(25):
                            line = f.readline()
                            if not line: break
                            self.print_line(line.rstrip("\r\n"), C_WHITE)
                except Exception as e:
                    self.print_line(f"Ошибка чтения: {e}", C_RED)

        # 8. MD / MKDIR
        elif cmd in ["MD", "MKDIR"]:
            if not args:
                self.print_line("Синтаксис: MD <имя_папки>", C_GRAY)
            else:
                target = self.resolve_path(args[0])
                try:
                    os.mkdir(target)
                    self.print_line(f"Папка {args[0]} создана.", C_GREEN)
                except Exception as e:
                    self.print_line(f"Ошибка создания: {e}", C_RED)

        # 9. DEL / RM
        elif cmd in ["DEL", "RM"]:
            if not args:
                self.print_line("Синтаксис: DEL <имя_файла>", C_GRAY)
            else:
                target = self.resolve_path(args[0])
                try:
                    os.remove(target)
                    self.print_line(f"Файл {args[0]} удален.", C_WHITE)
                except Exception as e:
                    self.print_line(f"Ошибка удаления: {e}", C_RED)

        # 10. MEM
        elif cmd == "MEM":
            gc.collect()
            free = gc.mem_free()
            alloc = gc.mem_alloc()
            total = free + alloc
            freq_mhz = machine.freq() // 1000000
            self.print_line(f"Частота CPU: {freq_mhz} МГц (DVI 60Hz)", C_CYAN)
            self.print_line(f"ОЗУ занято:  {alloc // 1024} КБ", C_WHITE)
            self.print_line(f"ОЗУ свободно:{free // 1024} КБ", C_GREEN)
            self.print_line(f"Всего ОЗУ:   {total // 1024} КБ SRAM", C_WHITE)

        # 11. PY / PYTHON / RUN
        elif cmd in ["PY", "PYTHON", "RUN"]:
            if not args:
                self.print_line("Синтаксис: PY <имя_скрипта.py>", C_GRAY)
            else:
                target = self.resolve_path(args[0])
                self.print_line(f"Исполнение {args[0]}...", C_YELLOW)
                self.draw_terminal()
                self.tft.show()
                try:
                    with open(target, "r") as f:
                        code = f.read()
                    exec(code, {"__name__": "__main__"})
                    self.print_line("[Программа успешно завершена]", C_GREEN)
                except Exception as e:
                    self.print_line(f"Ошибка выполнения: {e}", C_RED)

        # 12. ECHO
        elif cmd == "ECHO":
            self.print_line(" ".join(args), C_WHITE)

        # 13. REBOOT
        elif cmd in ["REBOOT", "RESTART"]:
            self.print_line("Перезагрузка микрокомпьютера...", C_YELLOW)
            self.draw_terminal()
            self.tft.show()
            time.sleep(0.5)
            machine.reset()

        # 14. EXIT
        elif cmd in ["EXIT", "QUIT"]:
            return "EXIT"

        # 15. PING
        elif cmd == "PING":
            target = args[0] if args else "55.0.0.0"
            self.print_line(f"Обмен пакетами с {target} по 32 байт:", C_WHITE)
            self.draw_terminal()
            self.tft.show()
            time.sleep_ms(300)

            times = [18, 14, 22, 19]
            for i in range(4):
                ms_time = times[i]
                self.beep(1600, 10)
                self.print_line(f"Ответ от {target}: байт=32 время={ms_time}мс TTL=54", C_TEXT)
                self.draw_terminal()
                self.tft.show()
                time.sleep_ms(400)
                if self.inputs.get_event() in ['ESC', 'BACK']:
                    break

            self.print_line(f"Статистика Ping для {target}:", C_YELLOW)
            self.print_line("  Пакетов: отправлено = 4, получено = 4, потерь = 0%", C_GREEN)

        # 16. CONNECT
        elif cmd == "CONNECT":
            target = args[0] if args else "55.0.0.0"
            steps = [
                (f"Попытка связи с {target}:8080...", C_GRAY, 400),
                ("Обход защищенного прокси ЦРУ... [OK]", C_YELLOW, 500),
                ("Подбор ключа квантового шифрования...", C_CYAN, 600),
                ("Взлом фаервола Pentagon Gateway... [OK]", C_GREEN, 500),
                ("СОЕДИНЕНИЕ УСТАНОВЛЕНО! ДОСТУП: ROOT", rgb(0, 255, 200), 300)
            ]
            for text, col, delay in steps:
                self.beep(1400, 15)
                self.print_line(text, col)
                self.draw_terminal()
                self.tft.show()
                time.sleep_ms(delay)
                if self.inputs.get_event() in ['ESC', 'BACK']:
                    self.print_line("Соединение прервано.", C_RED)
                    break
            else:
                # Дошли до конца без ESC - теперь приглашение root@ip
                self.remote_host = target

        # 16b. DISCONNECT (если не подключены - сообщаем об этом)
        elif cmd == "DISCONNECT":
            self.print_line("Нет активного соединения.", C_GRAY)

        # 17. DOWNLOAD FILES (имя файла отдельной строкой, под ней полоска)
        elif cmd == "DOWNLOAD":
            self.print_line("Connected to secret server...", C_YELLOW)
            self.draw_terminal()
            self.tft.show()
            time.sleep_ms(600)

            secret_files = [
                "pentagon_passwords.txt",
                "important.txt (1).txt (2).txt (3).txt",
                "Macron_Wife_Agent_John_Smith.doc",
                "Angela_Merkel_nude_photos.zip",
                "Snowden_Salary.xlsx",
                "Kim_Jong_Un_Salary.xlsx",
                "Windows7_Update_Notice.txt",
                "X_Files_all_seasons.torrent",
                "Epstein_island_guests2024.pdf",
                "Trump_hairstyle_formula.docx",
                "Iran_nuclear_programm_v3_password_12345.txt",
                "analyses_of_Putin's_shit.pdf",
                "Maduro_lunch_menu.docx",
                "White_House_press_secretaries_nude_photos.rar",
                "otkuda_na_Belarus_gotovilos_napadeniye.png",
                "Zelenskiy_CS2_results.log",
                "CIA_MAX_account.txt",
                "HalfLife3.torrent"
            ]

            total_all_kb = 0
            for idx, fname in enumerate(secret_files):
                # "Размер" файла - псевдослучайный, но всегда одинаковый для одного имени
                total_kb = 40 + (len(fname) * 37 + idx * 53) % 900
                total_all_kb += total_kb

                # Имя файла целиком (длинные переносятся), под ним - полоска,
                # которая обновляется на месте. Всё белым цветом.
                pct = 0
                self.print_line(fname, C_WHITE)
                self.print_line(self._dl_bar(pct, total_kb), C_WHITE)
                self.draw_terminal()
                self.tft.show()

                while pct < 100:
                    pct = min(100, pct + 3 + (time.ticks_ms() + idx) % 9)
                    self.lines[-1] = (self._dl_bar(pct, total_kb), C_WHITE)
                    self.beep(1800 + pct * 5, 6)
                    self.draw_terminal()
                    self.tft.show()
                    time.sleep_ms(30)
                    if self.inputs.get_event() in ['ESC', 'BACK']:
                        self.print_line("Загрузка прервана пользователем.", C_RED)
                        return None
                time.sleep_ms(120)

            self.beep(2400, 50)
            self.print_line("--------------------------------------", C_BORDER)
            self.print_line("[DOWNLOAD COMPLETE] All files complete!", rgb(0, 255, 150))
            self.print_line(f"Загружено: {len(secret_files)} файлов, {total_all_kb} KB", C_WHITE)
            self.print_line("Files downloaded to /dev/null ;)", C_YELLOW)

        else:
            self.print_line(f"'{cmd}' не является командой. Введите HELP.", C_RED)

        gc.collect()
        return None

    # ------------------------------------------------------------ Отрисовка
    def draw_terminal(self):
        # 1. Шапка окна CMD (Y = 0 .. 19)
        self.tft.fill_rect(0, 0, W, 20, C_TITLE_BG)
        self.tft.line(0, 19, W, 19, C_BORDER)

        # Иконка консоли >_
        self.tft.fill_rect(8, 5, 13, 10, C_BG)
        self.tft.rect(8, 5, 13, 10, rgb(100, 110, 130))
        self.tft.text(">", 10, 6, C_WHITE)

        draw_text(self.tft, "Командная строка", 26, 6, C_WHITE)

        # Индикатор прокрутки: сколько строк отмотано вверх
        if self.scroll > 0:
            self.tft.text("^%d" % self.scroll, 250, 6, C_YELLOW)
        self.tft.text("Esc", 294, 6, C_WHITE)

        # 2. Чёрное поле терминала (Y = 20 .. 217)
        self.tft.fill_rect(0, 20, W, 198, C_BG)

        # Вывод строк из буфера
        prompt = self.get_prompt()
        curr_input_line = prompt + self.cmd_buffer

        disp_lines = []
        for item in self.lines:
            if isinstance(item, tuple):
                disp_lines.append(item)
            else:
                disp_lines.append((item, C_TEXT))

        # Окно просмотра с учётом прокрутки
        end = len(disp_lines) - self.scroll
        if end < 0:
            end = 0
        start = end - VIS_LINES
        if start < 0:
            start = 0
        vis = disp_lines[start:end]

        y = 24
        for text, color in vis:
            draw_text(self.tft, text[:MAX_COLS], 6, y, color)
            y += ROW_H

        # Строка ввода и курсор показываем только внизу (не при прокрутке)
        if self.scroll == 0:
            # Если строка длиннее экрана - показываем её хвост (где курсор)
            draw_text(self.tft, curr_input_line[-MAX_COLS:], 6, y, C_WHITE)

            # Мигающий курсор
            if self.cursor_blink:
                cur_x = 6 + min(len(curr_input_line), MAX_COLS) * 8
                if cur_x <= W - 10:
                    self.tft.fill_rect(cur_x, y + 8, 7, 2, C_WHITE)
        else:
            draw_text(self.tft, "-- PgDn: вниз --", 6, y, C_GRAY)

        # 3. Системная панель задач RobotOS (Y = 218 .. 239)
        draw_system_taskbar(self.tft, self.cfg, active_tab="CMD", tab_icon="cmd")

    def run(self):
        try:
            self._loop()
        finally:
            # При любом выходе из программы возвращаемся к локальному диску C:/D:
            self.remote_host = None
            self.scroll = 0

    def _loop(self):
        self.draw_terminal()
        self.tft.show()

        while True:
            now = time.ticks_ms()
            if time.ticks_diff(now, self.last_blink) > 400:
                self.last_blink = now
                self.cursor_blink = not self.cursor_blink
                self.draw_terminal()
                self.tft.show()

            ev = self.inputs.get_event()
            if not ev:
                time.sleep_ms(20)
                continue

            # Прокрутка вывода (подстрой названия событий под свой inputs)
            if ev in ['PGUP', 'PAGEUP', 'LEFT']:
                self.scroll_by(SCROLL_STEP)
                self.beep(900, 5)
                self.draw_terminal()
                self.tft.show()
                continue
            elif ev in ['PGDN', 'PAGEDOWN', 'RIGHT']:
                self.scroll_by(-SCROLL_STEP)
                self.beep(900, 5)
                self.draw_terminal()
                self.tft.show()
                continue
            elif ev == 'HOME':
                self.scroll_by(MAX_LINES)   # в самое начало
                self.draw_terminal()
                self.tft.show()
                continue
            elif ev == 'END':
                self.scroll = 0             # в самый конец
                self.draw_terminal()
                self.tft.show()
                continue

            # Любой другой ввод возвращает экран вниз
            if self.scroll != 0 and ev not in ['ESC', 'BACK']:
                self.scroll = 0

            # Выход по ESC
            if ev in ['ESC', 'BACK']:
                if self.scroll != 0:
                    self.scroll = 0
                elif not self.cmd_buffer:
                    self.beep(600, 20)
                    return
                else:
                    self.cmd_buffer = ""
                    self.beep(750, 8)

            # Выполнение команды (ENTER)
            elif ev == 'ENTER':
                self.beep(1200, 15)
                prompt = self.get_prompt()
                self.print_line(prompt + self.cmd_buffer, C_WHITE)
                res = self.execute_command(self.cmd_buffer)
                self.cmd_buffer = ""
                if res == "EXIT":
                    return

            # История команд (Стрелка ВВЕРХ)
            elif ev == 'UP':
                if self.history and self.hist_idx > 0:
                    self.hist_idx -= 1
                    self.cmd_buffer = self.history[self.hist_idx]
                    self.beep(850, 8)

            # История команд (Стрелка ВНИЗ)
            elif ev == 'DOWN':
                if self.history and self.hist_idx < len(self.history) - 1:
                    self.hist_idx += 1
                    self.cmd_buffer = self.history[self.hist_idx]
                    self.beep(850, 8)
                else:
                    self.hist_idx = len(self.history)
                    self.cmd_buffer = ""

            # Удаление символа (BACKSPACE)
            elif ev == 'BACKSPACE':
                if len(self.cmd_buffer) > 0:
                    self.cmd_buffer = self.cmd_buffer[:-1]
                    self.beep(650, 8)

            # Ввод текста
            elif len(ev) == 1 or ev == '  ':
                if len(self.cmd_buffer) < 30:
                    self.cmd_buffer += ev
                    self.beep(1100, 6)

            self.cursor_blink = True
            self.last_blink = now
            self.draw_terminal()
            self.tft.show()
