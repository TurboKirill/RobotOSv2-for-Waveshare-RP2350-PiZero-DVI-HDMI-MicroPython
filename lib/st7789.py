# lib/st7789.py - мостик совместимости приложений RobotOS с DVI экраном
from dvi_display import DVIDisplay, color565

# Для вызовов st7789.color565(r, g, b)
# и st7789.ST7789.color565(r, g, b)
class ST7789(DVIDisplay):
    @staticmethod
    def color565(r, g, b):
        return color565(r, g, b)