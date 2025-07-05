from manim import LaggedStart, SVGMobject, FullScreenRectangle
from manim import Scene, config, WHITE, BLACK, ORIGIN
from manim import linear, smooth, there_and_back, wiggle
import sys

svg_file = sys.argv[-5] if sys.argv[-5].endswith(".svg") else "sketch.svg"
duration = float(sys.argv[-4]) if sys.argv[-4].replace('.', '', 1).isdigit() else 10.0
delay = float(sys.argv[-3]) if sys.argv[-3].replace('.', '', 1).isdigit() else 0.1
scale = float(sys.argv[-2]) if sys.argv[-2].replace('.', '', 1).isdigit() else 2.0
draw_type = sys.argv[-1] if sys.argv[-1] in ["linear", "smooth", "there_and_back", "wiggle"] else "smooth"

# 设置 Manim 配置
draw_dict = {
    "linear": linear,
    "smooth": smooth,
    "there_and_back": there_and_back,
    "wiggle": wiggle}

config.background_color = BLACK  # we’ll cover it anyway

class DrawSVG(Scene):
    def construct(self):
        bg = FullScreenRectangle(
                fill_color=WHITE, fill_opacity=1, stroke_opacity=0
        )
        self.add(bg)

        paths = SVGMobject(svg_file)
        paths.set_fill(BLACK, opacity=1).set_stroke(opacity=0)

        # 将 SVG 放置在屏幕中央并缩放
        paths.scale(scale)
        paths.move_to(ORIGIN)

        # 初始将所有子路径填充透明
        for subpath in paths:
            subpath.set_fill(BLACK, opacity=0)

        #paths= sorted(paths, key=lambda p: p.get_width()*p.get_height())
        animations = [subpath.animate.set_fill(BLACK, 1) for subpath in paths]

        # 动画：使用 Create 绘制路径
        self.play(
            LaggedStart(
                *animations,
                lag_ratio=delay, 
                run_time=duration,
                rate_func= draw_dict.get(draw_type, smooth)
            )
        )
        self.wait(1)

# 执行：
# manim -pql svg2mp4.py DrawSVG


