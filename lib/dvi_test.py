# dvi_test.py - проверка вывода на монитор. Запустить: import dvi_test
import time
import dvi
from dvi_display import DVIDisplay

d = DVIDisplay()                       # 320x240, RGB565
W, H = d.width, d.height
c = d.color565

# 1. Цветные полосы + градиент серого + рамка
bars = [(255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
        (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0)]
bw = W // len(bars)
d.fill(c(20, 20, 20))
for i, col in enumerate(bars):
    d.fill_rect(i * bw, 0, bw, 120, c(*col))
for x in range(W):
    g = x * 255 // (W - 1)
    d.fill_rect(x, 120, 1, 40, c(g, g, g))
d.rect(0, 0, W, H, c(255, 255, 255))
d.text("RobotOS + DVI 640x480", 8, 170, c(0, 240, 255))
d.text("RP2350 %d MHz" % (__import__("machine").freq() // 1000000), 8, 184, c(255, 255, 255))
d.show()
print("bars on screen; info:", dvi.info())
time.sleep(3)

# 2. Анимация + счётчик FPS
x, y, dx, dy = 20, 30, 3, 2
t0 = time.ticks_ms()
n = 0
while time.ticks_diff(time.ticks_ms(), t0) < 8000:
    d.fill(c(0, 0, 40))
    d.fill_rect(x, y, 40, 30, c(255, 140, 0))
    d.rect(x, y, 40, 30, c(255, 255, 255))
    d.text("frame %d" % n, 8, 8, c(255, 255, 255))
    d.show()
    x += dx
    y += dy
    if x < 0 or x > W - 40:
        dx = -dx
    if y < 24 or y > H - 30:
        dy = -dy
    n += 1
fps = n * 1000 / time.ticks_diff(time.ticks_ms(), t0)
print("show() rate: %.1f fps" % fps)

d.fill(0)
d.text("fps: %.1f" % fps, 8, 8, c(0, 255, 0))
d.text("OK. Picture stays on until reset.", 8, 24, c(255, 255, 255))
d.show()
