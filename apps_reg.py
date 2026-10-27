# apps_reg.py - реестр приложений RobotOS (маленький модуль: gui и установщик используют его вместе)
# Приложение "установлено", если его файл app_xxx.py (или .mpy) лежит в ROOT.
# Свои приложения можно ставить с SD-карты (папка /sd/apps): первой строкой файла пишется заголовок
#   # robotos-app: Название в меню | ИмяКласса | app        (или game)
# Класс должен принимать (tft, audio, inputs, cfg) и иметь метод run().
import os
import sys
import gc

ROOT = ""                 # папка с приложениями ("" = корень флеша, рядом с main.py)
TRASH = "/trash"          # корзина: сюда уходят удалённые приложения (можно вернуть)
SD_DIR = "/sd/apps"       # откуда можно устанавливать новые приложения

# (модуль, класс, пункт меню, название по-русски, тип, способ запуска, системное)
# тип: "app" - меню Приложения, "game" - меню Игры, "robot" - раздел Robotics
# системное: True - встроено в ОС, удалять нельзя (в списке помечено СИСТЕМА)
# запуск: 0 - (tft, audio, inputs, cfg); 1 - без cfg; 2 - блокнот (cfg, filepath=...); 3 - подменю gui.menu_robot()
REG = (
    ("app_cmd", "CmdApp", "CONSOLE (CMD)", "Командная строка CMD", "app", 0, True),
    ("app_htop", "HtopApp", "TASK MANAGER (HTOP)", "Диспетчер задач HTOP", "app", 0, True),
    ("app_winamp", "WinampApp", "WINAMP RobotOS", "Winamp Player", "app", 0, False),
    ("app_player", "MusicPlayerApp", "MUSIC PLAYER", "Аудио плеер WAV", "app", 0, True),
    ("app_gallery", "GalleryApp", "PHOTO GALLERY", "Фотогалерея", "app", 0, True),
    ("app_editor", "NotepadApp", "NOTEPAD++ (EDITOR)", "Текстовый редактор", "app", 2, True),
    ("app_browser", "BrowserApp", "INTERNET EXPLORER", "Интернет Эксплорер", "app", 0, True),
    ("app_video", "VideoPlayerApp", "MEDIA PLAYER", "Видеопроигрыватель WMP", "app", 0, True),
    ("app_calendar", "CalendarApp", "Часы и календарь", "Часы и календарь", "app", 0, True),
    ("app_eyes", "RobotEyesApp", "Глаза робота", "Глаза робота", "app", 3, True),
    ("app_servo_test", "ServoTestApp", "SERVO TEST (ROBOT)", "Тест сервоприводов", "app", 0, True),
    ("app_weather", "WeatherApp", "CLIMATE & WEATHER", "Погода и климат", "app", 0, True),

    ("app_arkanoid", "ArkanoidApp", "ARKANOID (BREAKOUT)", "Arkanoid", "game", 0, True),
    ("app_snake", "SnakeApp", "CYBER-SNAKE", "Cyber-Snake", "game", 0, True),
    ("app_doom", "DoomApp", "DOOM-LITE (RAYCAST)", "Doom-Lite", "game", 0, True),
)

# Системные - удалить нельзя (без них не работает ОС)
SYSTEM = (
    ("app_settings", "Параметры"),
    ("app_uninstaller", "Установщик приложений"),
    ("app_files", "Проводник файлов"),
    ("app_sleep", "Режим сна"),
    ("app_games", "Меню игр"),
)


def _root():
    return ROOT if ROOT else ""


def path_of(mod):
    """Путь к файлу модуля или None, если приложения нет."""
    for ext in (".py", ".mpy"):
        p = _root() + "/" + mod + ext
        try:
            os.stat(p)
            return p
        except OSError:
            pass
    return None


def exists(mod):
    return path_of(mod) is not None


def size_of(p):
    try:
        return os.stat(p)[6]
    except OSError:
        return 0


def mod_of(name):
    """app_xxx.py / app_xxx.mpy -> 'app_xxx'. Неподходящее имя -> None."""
    if name.endswith(".py"):
        b = name[:-3]
    elif name.endswith(".mpy"):
        b = name[:-4]
    else:
        return None
    if not b.startswith("app_") or len(b) < 5:
        return None
    for ch in b:
        if ord(ch) > 127 or not (ch.islower() or ch.isdigit() or ch == "_"):
            return None
    return b


def list_files(d):
    """[(модуль, имя_файла)] - только app_*.py / app_*.mpy в папке d (путь как bytes, чтобы не ловить UnicodeError)."""
    out = []
    try:
        for e in os.ilistdir((d if d else "/").encode()):
            n = e[0]
            if isinstance(n, bytes):
                try:
                    n = n.decode()
                except Exception:
                    continue
            if e[1] == 0x4000:
                continue
            m = mod_of(n)
            if m:
                out.append((m, n))
    except OSError:
        pass
    return out


def read_header(path):
    """(название, класс, тип) из строки '# robotos-app: ...' в начале файла или None."""
    try:
        with open(path, "rb") as f:
            for _ in range(8):
                ln = f.readline()
                if not ln:
                    break
                if ln.startswith(b"# robotos-app:"):
                    parts = [x.strip() for x in ln[14:].decode().split("|")]
                    if len(parts) >= 2 and parts[1]:
                        kind = parts[2] if len(parts) > 2 and parts[2] in ("app", "game") else "app"
                        return (parts[0] or parts[1], parts[1], kind)
                    return None
    except Exception:
        pass
    return None


def title_of(mod, path):
    """Красивое название для списков."""
    for r in REG:
        if r[0] == mod:
            return r[3]
    for s in SYSTEM:
        if s[0] == mod:
            return s[1]
    h = read_header(path)
    return h[0] if h else mod


def all_entries():
    """Установленные приложения: (модуль, класс, меню, название, тип, запуск, путь, системное)."""
    out = []
    known = set()
    for s in SYSTEM:
        p = path_of(s[0])
        if p:
            out.append((s[0], None, s[1], s[1], "app", 0, p, True))
        known.add(s[0])
    for r in REG:
        known.add(r[0])
        p = path_of(r[0])
        if p:
            out.append((r[0], r[1], r[2], r[3], r[4], r[5], p, r[6]))
    extra = []
    for m, n in list_files(_root()):
        if m in known:
            continue
        known.add(m)
        p = _root() + "/" + n
        h = read_header(p)
        if h:
            extra.append((m, h[1], h[0], h[0], h[2], 0, p, False))
        else:
            extra.append((m, None, m, m, "app", 0, p, False))   # без заголовка: в меню не попадёт
    extra.sort(key=lambda e: e[0])
    return out + extra


def menu_entries(kind):
    """Приложения для меню gui: только установленные и с классом (системные тоже)."""
    return [e for e in all_entries() if e[4] == kind and e[1]]


def launch(gui, e):
    """Запуск приложения из меню gui: e - запись из menu_entries().
    Импорт тоже под защитой: нехватка памяти или ошибка в файле покажет окно ошибки, а не уронит ОС."""
    mod = e[0]
    if e[5] == 3:                       # подменю робота (там свой запуск app_eyes)
        gui.menu_robot()
        return
    try:
        cls = getattr(__import__(mod), e[1])
        if e[5] == 1:
            gui.launch(lambda: cls(gui.tft, gui.audio, gui.inputs))
        elif e[5] == 2:
            gui.launch(lambda: cls(gui.tft, gui.audio, gui.inputs, gui.cfg, filepath="/sd/notes.txt"))
        else:
            gui.launch(lambda: cls(gui.tft, gui.audio, gui.inputs, gui.cfg))
    except Exception as ex:
        try:
            sys.print_exception(ex)
        except Exception:
            pass
        gui.show_error(ex)
    finally:
        cls = None
        try:
            del sys.modules[mod]
        except KeyError:
            pass
        gc.collect()
