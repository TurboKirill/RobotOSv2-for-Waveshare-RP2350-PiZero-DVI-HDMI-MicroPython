# app_editor.py - Редактор Notepad++ для RobotOS (DVI 320x240)
# Стиль Windows 10: 35 колонок текста, системная панель задач, модальные меню
import os
import time
import math
import struct
import gc
from dvi_display import color565 as rgb
from gui import draw_text, draw_system_taskbar

W, H = 320, 240
TB_H = 22                 # Высота панели задач
WIN_H = H - TB_H          # Рабочая область редактора (218px)

# ---------------------------------------------------------------- Палитра
C_BG        = rgb(14, 18, 28)       # Тёмно-синий фон текстового поля
C_HEADER    = rgb(28, 32, 44)       # Шапка окна
C_BORDER    = rgb(45, 52, 70)       # Разделительные линии
C_LINE_NUM  = rgb(80, 100, 130)     # Номера строк
C_TEXT      = 0xFFFF                # Основной текст
C_WHITE     = 0xFFFF
C_CURSOR    = rgb(0, 220, 255)      # Неоновый курсор
C_GLOW      = rgb(0, 210, 255)
C_GRAY      = rgb(140, 150, 170)
C_MENU_BG   = rgb(26, 32, 46)       # Фон меню и диалогов
C_SEL_BG    = rgb(0, 110, 210)      # Выделенный пункт меню

MAX_ROWS = 13
MAX_COLS = 35
ROW_H    = 13


class NotepadApp:
    def __init__(self, tft, audio, inputs, config=None, filepath="/sd/notes.txt"):
        self.tft = tft
        self.audio = audio
        self.inputs = inputs
        self.cfg = config if config else {"vol_ui": 30, "mute": False, "hour": 20, "minute": 45}
        self.filepath = filepath

        self.lines = [""]
        self.cur_row = 0
        self.cur_col = 0
        self.scroll_row = 0
        self.scroll_col = 0
        self.is_modified = False

        self.load_file()

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
        for _ in range(max(1, int((ms / 1000) * freq))):
            self.audio.write(cycle)

    def load_file(self):
        try:
            with open(self.filepath, "r") as f:
                raw = [l.rstrip("\r\n") for l in f.readlines()]
                self.lines = raw if raw else [""]
        except:
            if self.filepath.endswith(".py"):
                self.lines = ["# Python Script", "print('Hello RobotOS!')", ""]
            else:
                self.lines = ["# RobotOS Notepad++", "Type notes here...", ""]
        self.is_modified = False

    def save_file(self):
        try:
            with open(self.filepath, "w") as f:
                for line in self.lines:
                    f.write(line + "\n")
            self.is_modified = False
            self.beep(1600, 30)
            return True
        except Exception as e:
            print("Save error:", e)
            return False

    def prompt_save_as(self):
        """Модальный диалог Сохранить как..."""
        drives = ["/sd/", "/"]
        drive_idx = 0 if self.filepath.startswith("/sd") else 1

        name = self.filepath.split("/")[-1]
        if not name:
            name = "notes.txt"

        active_field = 1
        bw, bh = 240, 130
        bx = (W - bw) // 2
        by = (WIN_H - bh) // 2

        while True:
            self.tft.fill_rect(bx, by, bw, bh, C_MENU_BG)
            self.tft.rect(bx, by, bw, bh, C_GLOW)

            self.tft.fill_rect(bx + 2, by + 2, bw - 4, 18, rgb(40, 48, 66))
            draw_text(self.tft, "Сохранить как...", bx + 8, by + 6, C_WHITE)

            # Поле 1: Накопитель
            c1 = C_GLOW if active_field == 0 else C_WHITE
            draw_text(self.tft, "1. Диск:", bx + 12, by + 28, C_GRAY)
            drive_label = "< MicroSD: /sd/ >" if drive_idx == 0 else "< Flash: / >"
            self.tft.fill_rect(bx + 12, by + 40, bw - 24, 18, rgb(16, 20, 30))
            if active_field == 0:
                self.tft.rect(bx + 12, by + 40, bw - 24, 18, C_GLOW)
            self.tft.text(drive_label, bx + 18, by + 45, c1)

            # Поле 2: Имя файла
            c2 = C_GLOW if active_field == 1 else C_WHITE
            draw_text(self.tft, "2. Имя файла:", bx + 12, by + 64, C_GRAY)
            self.tft.fill_rect(bx + 12, by + 76, bw - 24, 18, rgb(16, 20, 30))
            if active_field == 1:
                self.tft.rect(bx + 12, by + 76, bw - 24, 18, C_GLOW)
            disp_name = (name[-22:] + "_") if active_field == 1 else name[-22:]
            self.tft.text(disp_name, bx + 18, by + 81, c2)

            # Подсказки
            self.tft.line(bx, by + 102, bx + bw, by + 102, C_BORDER)
            draw_text(self.tft, "ENTER:Сохранить  ESC:Отмена", bx + 14, by + 110, C_GRAY)
            self.tft.show()

            while True:
                ev = self.inputs.get_event()
                if ev:
                    if ev in ['UP', 'DOWN']:
                        active_field = 1 - active_field
                        self.beep(850, 10); break
                    elif ev in ['LEFT', 'RIGHT'] and active_field == 0:
                        drive_idx = 1 - drive_idx
                        self.beep(950, 10); break
                    elif ev in ['ESC', 'BACK']:
                        return 'CANCEL'
                    elif ev == 'ENTER':
                        clean_name = name.strip()
                        if clean_name:
                            self.filepath = (drives[drive_idx] + clean_name).replace("//", "/")
                            self.save_file()
                            return 'SAVED'
                    elif active_field == 1:
                        if ev == 'BACKSPACE':
                            if len(name) > 0:
                                name = name[:-1]
                                self.beep(650, 8); break
                        elif len(ev) == 1 and ev not in [' ', '/']:
                            name += ev
                            self.beep(1200, 6); break
                time.sleep_ms(20)

    def adjust_scroll(self):
        if self.cur_row < self.scroll_row:
            self.scroll_row = self.cur_row
        elif self.cur_row >= self.scroll_row + MAX_ROWS:
            self.scroll_row = self.cur_row - MAX_ROWS + 1

        if self.cur_col < self.scroll_col:
            self.scroll_col = self.cur_col
        elif self.cur_col >= self.scroll_col + MAX_COLS:
            self.scroll_col = self.cur_col - MAX_COLS + 1

    def draw_editor(self, update_screen=True):
        # 1. Шапка окна (Y = 0 .. 19)
        self.tft.fill_rect(0, 0, W, 20, C_HEADER)
        self.tft.line(0, 19, W, 19, C_BORDER)

        fname = self.filepath.split("/")[-1][:16]
        mod_mark = "*" if self.is_modified else ""
        self.tft.text(f"{fname}{mod_mark}", 8, 6, C_WHITE)

        pos_str = f"Ln {self.cur_row + 1}, Col {self.cur_col + 1}"
        self.tft.text(pos_str, 175, 6, C_GLOW)
        self.tft.text("Esc", 294, 6, C_WHITE)

        # 2. Область редактирования (Y = 20 .. 193)
        self.tft.fill_rect(0, 20, W, 174, C_BG)

        # Разделитель между номерами строк и кодом
        self.tft.line(28, 20, 28, 193, rgb(36, 44, 60))

        y = 22
        for r_idx in range(self.scroll_row, min(len(self.lines), self.scroll_row + MAX_ROWS)):
            line = self.lines[r_idx]
            # Номер строки
            self.tft.text(f"{r_idx+1:02d}", 4, y + 2, C_LINE_NUM)

            # Текст строки (до 35 символов на экран)
            visible_text = line[self.scroll_col : self.scroll_col + MAX_COLS]
            draw_text(self.tft, visible_text, 34, y + 2, C_TEXT)

            # Курсор
            if r_idx == self.cur_row:
                cx = 34 + (self.cur_col - self.scroll_col) * 8
                if 34 <= cx <= 312:
                    self.tft.fill_rect(cx, y + 11, 7, 2, C_CURSOR)

            y += ROW_H

        # 3. Панель подсказок снизу (Y = 194 .. 217)
        self.tft.fill_rect(0, 194, W, 24, rgb(12, 15, 22))
        self.tft.line(0, 194, W, 194, C_BORDER)
        draw_text(self.tft, "ENTER:След. строка   BKSP:Стереть", 6, 198, C_WHITE)
        draw_text(self.tft, "ESC:Меню / Выход", 6, 208, C_GLOW)

        # 4. Системная панель задач RobotOS (Y = 218 .. 239)
        draw_system_taskbar(self.tft, self.cfg, active_tab="Editor", tab_icon="notepad")

        if update_screen:
            self.tft.show()

    def show_exit_dialog(self):
        opts = [
            "1. Сохранить",
            "2. Сохранить как...",
            "3. Закрыть без сохр.",
            "4. Отмена"
        ]
        sel = 0

        # Фон рисуется один раз в буфер
        self.draw_editor(update_screen=False)

        bw, bh = 240, 120
        bx = (W - bw) // 2
        by = (WIN_H - bh) // 2

        while True:
            self.tft.fill_rect(bx, by, bw, bh, C_MENU_BG)
            self.tft.rect(bx, by, bw, bh, C_GLOW)
            self.tft.fill_rect(bx + 2, by + 2, bw - 4, 18, rgb(40, 48, 66))
            draw_text(self.tft, "Меню редактора", bx + 8, by + 6, C_WHITE)

            y = by + 26
            for i, o in enumerate(opts):
                is_act = (i == sel)
                if is_act:
                    self.tft.fill_rect(bx + 6, y - 2, bw - 12, 18, C_SEL_BG)
                    draw_text(self.tft, f"> {o}", bx + 10, y + 2, C_WHITE)
                else:
                    draw_text(self.tft, f"  {o}", bx + 10, y + 2, C_GRAY)
                y += 22

            self.tft.show()

            while True:
                ev = self.inputs.get_event()
                if ev:
                    if ev == 'UP':
                        sel = (sel - 1) % len(opts)
                        self.beep(850, 10); break
                    elif ev == 'DOWN':
                        sel = (sel + 1) % len(opts)
                        self.beep(750, 10); break
                    elif ev == 'ENTER':
                        if sel == 0:
                            self.save_file()
                            return 'EXIT'
                        elif sel == 1:
                            res = self.prompt_save_as()
                            if res == 'SAVED':
                                return 'EXIT'
                            self.draw_editor(update_screen=False)
                            break
                        elif sel == 2:
                            return 'EXIT'
                        elif sel == 3:
                            return 'CANCEL'
                    elif ev in ['ESC', 'BACK']:
                        return 'CANCEL'
                time.sleep_ms(20)

    def run(self):
        while True:
            self.adjust_scroll()
            self.draw_editor()

            ev = self.inputs.get_event()
            if not ev:
                time.sleep_ms(20)
                continue

            cur_line = self.lines[self.cur_row]

            # Вызов меню / Выход
            if ev in ['ESC', 'BACK']:
                res = self.show_exit_dialog()
                if res == 'EXIT':
                    break

            # Стрелки
            elif ev == 'UP':
                if self.cur_row > 0:
                    self.cur_row -= 1
                    self.cur_col = min(self.cur_col, len(self.lines[self.cur_row]))
                    self.beep(900, 8)

            elif ev == 'DOWN':
                if self.cur_row < len(self.lines) - 1:
                    self.cur_row += 1
                    self.cur_col = min(self.cur_col, len(self.lines[self.cur_row]))
                    self.beep(800, 8)

            elif ev == 'LEFT':
                if self.cur_col > 0:
                    self.cur_col -= 1
                elif self.cur_row > 0:
                    self.cur_row -= 1
                    self.cur_col = len(self.lines[self.cur_row])
                self.beep(950, 8)

            elif ev == 'RIGHT':
                if self.cur_col < len(cur_line):
                    self.cur_col += 1
                elif self.cur_row < len(self.lines) - 1:
                    self.cur_row += 1
                    self.cur_col = 0
                self.beep(950, 8)

            # Перевод строки (ENTER)
            elif ev == 'ENTER':
                left_part = cur_line[:self.cur_col]
                right_part = cur_line[self.cur_col:]
                self.lines[self.cur_row] = left_part
                self.lines.insert(self.cur_row + 1, right_part)
                self.cur_row += 1
                self.cur_col = 0
                self.scroll_col = 0
                self.is_modified = True
                self.beep(1200, 15)

            # Стирание символов (BACKSPACE)
            elif ev == 'BACKSPACE':
                if self.cur_col > 0:
                    self.lines[self.cur_row] = cur_line[:self.cur_col-1] + cur_line[self.cur_col:]
                    self.cur_col -= 1
                    self.is_modified = True
                    self.beep(650, 8)
                elif self.cur_row > 0:
                    prev_len = len(self.lines[self.cur_row - 1])
                    self.lines[self.cur_row - 1] += cur_line
                    self.lines.pop(self.cur_row)
                    self.cur_row -= 1
                    self.cur_col = prev_len
                    self.is_modified = True
                    self.beep(650, 8)

            # Ввод текста или табуляции
            elif len(ev) == 1 or ev == '  ':
                self.lines[self.cur_row] = cur_line[:self.cur_col] + ev + cur_line[self.cur_col:]
                self.cur_col += len(ev)
                self.is_modified = True
                self.beep(1300, 6)