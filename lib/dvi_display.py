# dvi_display.py - экран 320x240 на DVI/HDMI (640x480@60), замена lib/st7789.py
#
# Использование (почти как st7789):
#     from dvi_display import DVIDisplay
#     tft = DVIDisplay()              # RGB565, 65536 цветов
#     tft.fill(0)
#     tft.text("Hello", 10, 10, tft.color565(255, 255, 255))
#     tft.show()                      # показать кадр (без разрывов)
#
# Рисовать можно всем, что есть в framebuf: fill, fill_rect, rect, line,
# text, pixel, blit, scroll ...  Буфер лежит в быстрой ОЗУ.
import framebuf
import dvi

WIDTH = 320
HEIGHT = 240

_bpp = 16


def color565(r, g, b):
    """RGB (0..255) -> число цвета для текущего режима экрана.

    Внимание: в отличие от st7789.color565 байты НЕ переставлены местами,
    framebuf и DVI используют одинаковый порядок.
    """
    if _bpp == 16:
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return (r & 0xE0) | ((g & 0xE0) >> 3) | (b >> 6)     # RGB332


class DVIDisplay(framebuf.FrameBuffer):
    def __init__(self, bpp=16, pins=None, invert=False):
        global _bpp
        if bpp not in (8, 16):
            raise ValueError("bpp must be 8 or 16")
        dvi.init(fmt=dvi.RGB565 if bpp == 16 else dvi.RGB332, pins=pins, invert=invert)
        _bpp = bpp
        self.bpp = bpp
        self.width = WIDTH
        self.height = HEIGHT
        # буфер для рисования; на экран попадает после show()
        self.buffer = dvi.buffer(0)
        super().__init__(self.buffer, WIDTH, HEIGHT,
                         framebuf.RGB565 if bpp == 16 else framebuf.GS8)

    # --- как у ST7789 -----------------------------------------------------
    def show(self, wait=True):
        """Показать нарисованное. wait=False - не ждать окончания копирования
        (тогда до dvi.busy()==False в буфер лучше не рисовать)."""
        dvi.show(wait=wait)

    @staticmethod
    def color565(r, g, b):
        return color565(r, g, b)

    def rgb(self, r, g, b):
        return color565(r, g, b)

    # --- DVI-специфичное --------------------------------------------------
    def wait_frame(self):
        dvi.wait_frame()

    def frames(self):
        return dvi.frame()

    def deinit(self):
        dvi.deinit()
