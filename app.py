import gradio as gr
from sketch2svg import sketch2svg
import subprocess
import os,sys
import asyncio

if sys.platform == "win32":
    # 切换到基于 select 的事件循环，避免 Proactor 在 pipe 关闭时抛错
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

def prepend_last_frame(input_video: str, output_video: str):
    """
    将 input_video 的最后一帧添加到视频最前面，生成新的 output_video。
    要求系统已安装 ffmpeg。
    """
    base = os.path.splitext(input_video)[0]
    last_frame_img = f"{base}_last_frame.png"
    last_frame_video = f"{base}_last_frame.mp4"
    temp1_ts = f"{base}_temp1.ts"
    temp2_ts = f"{base}_temp2.ts"

    try:
        # 1. 提取最后一帧
        subprocess.run([
            "ffmpeg", "-y", "-sseof", "-1", "-i", input_video,
            "-vframes", "1", last_frame_img
        ], check=True)

        # 2. 把图片转换为 1 秒视频
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", last_frame_img,
            "-c:v", "libx264", "-t", "1", "-pix_fmt", "yuv420p",
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            last_frame_video
        ], check=True)

        # 3. 转为 ts 格式准备拼接
        subprocess.run([
            "ffmpeg", "-y", "-i", last_frame_video,
            "-c", "copy", "-bsf:v", "h264_mp4toannexb",
            "-f", "mpegts", temp1_ts
        ], check=True)

        subprocess.run([
            "ffmpeg", "-y", "-i", input_video,
            "-c", "copy", "-bsf:v", "h264_mp4toannexb",
            "-f", "mpegts", temp2_ts
        ], check=True)

        # 4. 拼接并生成最终视频
        subprocess.run([
            "ffmpeg", "-y", "-i", f"concat:{temp1_ts}|{temp2_ts}",
            "-c", "copy", "-bsf:a", "aac_adtstoasc", output_video
        ], check=True)

    finally:
        # 清理中间文件
        for f in [last_frame_img, last_frame_video, temp1_ts, temp2_ts]:
            if os.path.exists(f):
                os.remove(f)

def convert_svg_to_mp4(svg_path: str, manim_dur: float = 10.0, manim_delay: float = 0.1, manim_scale:float = 2.0, manim_draw: str = "smooth") -> str:
    """Convert SVG to MP4 using Manim.
    Args:
        svg_path (str): Path to the SVG file.
        manim_dur (float): Duration for the video.
        manim_delay (float): Delay between subpaths in the animation.
    Returns:
        str: Path to the generated MP4 video file.
    """
    print(f"Converting SVG to MP4: {svg_path}")
    filename = os.path.splitext(os.path.basename(svg_path))[0]
    cmd = [
        "manim",
        "-qh",  # low quality for quick rendering
        "--disable_caching",
        "--media_dir", ".\\media",
        "--output_file", f"{filename}",
        "svg2mp4.py",
        "DrawSVG",
        svg_path,
        f"{manim_dur}",
        f"{manim_delay}",
        f"{manim_scale}",
        f"{manim_draw}"
    ]
    try:
        subprocess.run(cmd, check=True)
        video_path = f"media\\videos\\svg2mp4\\1080p60\\{filename}.mp4"
        out_path = f"media\\videos\\svg2mp4\\1080p60\\{filename}-final.mp4"
        prepend_last_frame(video_path, out_path)  # 添加最后一帧
        print(f"Last frame prepended to video: {out_path}", file=sys.stderr)
        return out_path
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        return None



with gr.Blocks() as demo:
    gr.Markdown("### Doodle to Sketch to Video with Multiple Callbacks")
    with gr.Accordion("参数设置", open=True):
        with gr.Row():
            manim_dur = gr.Slider(minimum=0.5, maximum=20, step=0.5, value=10.0, label="生成视频时长", interactive=True)
            manim_delay = gr.Slider(minimum=0.1, maximum=1.0, step=0.1, value=0.1, label="子路径延迟（比例)", interactive=True)
            manim_scale = gr.Slider(minimum=0.1, maximum=5.0, step=0.1, value=2.0, label="缩放比例", interactive=True)
            manim_drawtype = gr.Dropdown(
                choices=["linear", "smooth", "there_and_back", "wiggle"],
                value="smooth",
                label="绘制方式",
                interactive=True
            )
    with gr.Row():
        input_img = gr.Image(label="Input Doodle/Photo", type="filepath")
        sketch_preview = gr.Image(label="Sketch Preview", type="filepath")
        video_preview = gr.Video(label="Video Preview", autoplay=True)
    with gr.Row():
        btn_sketch = gr.Button("生成线稿")
        btn_video = gr.Button("生成视频")
        save_video = gr.Button("没有卵用")
    svg_path = gr.State(value="")

    # 绑定回调
    btn_sketch.click(fn=sketch2svg, inputs=input_img, outputs=[sketch_preview,svg_path])
    btn_video.click(fn=convert_svg_to_mp4, inputs=[svg_path,manim_dur,manim_delay, manim_scale, manim_drawtype], outputs=video_preview)


demo.launch(server_port=7880)
