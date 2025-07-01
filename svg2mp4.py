from manim import *
import sys

svg_file = sys.argv[-1] if sys.argv[-1].endswith(".svg") else "sketch.svg"

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
        paths.scale(2)
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
                lag_ratio=0.1,   # 子路径间延迟 10%
                run_time=10,
                rate_func=smooth
            )
        )
        self.wait(1)

# 执行：
# manim -pql manim_svg_to_video.py DrawSVG

