import os
import sys
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

import gradio as gr
from sketch2svg import sketch2svg  # must return (sketch_preview_path, svg_path)


# ----- Async/subprocess compatibility on Windows -----
if sys.platform == "win32":
    # Use selector loop for asyncio + subprocess compatibility on Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ----- Utilities -----
def _check_cmd_available(cmd: str, ver:str) -> None:
    """Ensure an external command (e.g., ffmpeg, manim) is available."""
    try:
        subprocess.run([cmd, f"{ver}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except Exception as e:
        raise RuntimeError(f"Required command not available: {cmd!r}. Error: {e}") from e
    


def _run(cmd: list[str], cwd: Optional[Path] = None) -> None:
    """Run a subprocess command with unified error handling."""
    try:
        subprocess.run(cmd, check=True, cwd=str(cwd) if cwd else None)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nExit code: {e.returncode}") from e


# ----- Video processing -----
def prepend_last_frame(input_video: str, output_video: str, freeze_sec: float = 1.0) -> None:
    """
    Prepend the last frame of a video as a short still segment.
    Args:
        input_video: path to input video.
        output_video: path to final output video.
        freeze_sec: duration (seconds) of the prepended still segment.
    """
    _check_cmd_available("ffmpeg", "-version")

    in_path = Path(input_video)
    out_path = Path(output_video)
    base = in_path.with_suffix("")

    last_frame_img = base.parent / f"{base.name}_last_frame.png"
    last_frame_video = base.parent / f"{base.name}_last_frame.mp4"
    temp1_ts = base.parent / f"{base.name}_temp1.ts"
    temp2_ts = base.parent / f"{base.name}_temp2.ts"

    try:
        # Extract last frame to an image
        _run([
            "ffmpeg", "-y", "-sseof", "-1", "-i", str(in_path),
            "-vframes", "1", str(last_frame_img)
        ])

        # Create a short video from the last frame; ensure even dimensions
        _run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(last_frame_img),
            "-t", f"{freeze_sec}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            str(last_frame_video)
        ])

        # Convert both clips to MPEG-TS for safe concatenation
        _run([
            "ffmpeg", "-y", "-i", str(last_frame_video),
            "-c", "copy", "-bsf:v", "h264_mp4toannexb",
            "-f", "mpegts", str(temp1_ts)
        ])

        _run([
            "ffmpeg", "-y", "-i", str(in_path),
            "-c", "copy", "-bsf:v", "h264_mp4toannexb",
            "-f", "mpegts", str(temp2_ts)
        ])

        # Concatenate TS streams and remux to MP4
        _run([
            "ffmpeg", "-y", "-i", f"concat:{temp1_ts}|{temp2_ts}",
            "-c", "copy", "-bsf:a", "aac_adtstoasc", str(out_path)
        ])
    finally:
        # Best-effort cleanup for temporary artifacts
        for f in (last_frame_img, last_frame_video, temp1_ts, temp2_ts):
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass


def convert_svg_to_mp4(
    svg_path: str,
    manim_dur: float = 10.0,
    manim_delay: float = 0.1,
    manim_scale: float = 2.0,
    manim_draw: str = "smooth"
) -> Optional[str]:
    """
    Render an SVG into an animated MP4 using Manim, then prepend the last frame for a short still.
    Returns the final video path, or None on failure.
    """
    if not svg_path:
        print("No SVG path provided.", file=sys.stderr)
        return None

    _check_cmd_available("manim", "--version")
    _check_cmd_available("ffmpeg", "-version")

    svg_p = Path(svg_path)
    if not svg_p.exists():
        print(f"SVG not found: {svg_p}", file=sys.stderr)
        return None

    media_dir = Path("media")
    manim_scene_file = Path("svg2mp4.py")  # must exist locally
    scene_class = "DrawSVG"                # must exist inside svg2mp4.py

    filename = svg_p.stem
    cmd = [
        "manim",
        "-qh",  # fast rendering; consider -ql for even faster development quality
        "--disable_caching",
        "--media_dir", str(media_dir),
        "--output_file", filename,
        str(manim_scene_file),
        scene_class,
        str(svg_p),
        f"{manim_dur}",
        f"{manim_delay}",
        f"{manim_scale}",
        f"{manim_draw}",
    ]

    try:
        _run(cmd)

        # Locate rendered video (Manim output layout may vary across versions)
        video_path = media_dir / "videos" / manim_scene_file.stem / "1080p60" / f"{filename}.mp4"
        if not video_path.exists():
            candidates = list((media_dir / "videos").rglob(f"{filename}.mp4"))
            if candidates:
                video_path = candidates[0]
            else:
                print("Rendered video not found under media/videos/*", file=sys.stderr)
                return None

        out_path = video_path.with_name(f"{video_path.stem}-final.mp4")
        prepend_last_frame(str(video_path), str(out_path), freeze_sec=1.0)
        print(f"[OK] Video created: {out_path}", file=sys.stderr)
        return str(out_path)
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        return None


# ----- Gradio UI -----
with gr.Blocks(title="Sketch to Motion") as demo:
    gr.Markdown("## Doodle → Sketch → Video")

    with gr.Accordion("Parameters", open=True):
        with gr.Row():
            manim_dur = gr.Slider(
                minimum=0.5, maximum=20.0, step=0.5, value=10.0,
                label="Animation duration (s)", interactive=True
            )
            manim_delay = gr.Slider(
                minimum=0.05, maximum=1.0, step=0.05, value=0.1,
                label="Subpath delay ratio", interactive=True
            )
            manim_scale = gr.Slider(
                minimum=0.1, maximum=5.0, step=0.1, value=2.0,
                label="scale factor", interactive=True
            )
            manim_drawtype = gr.Dropdown(
                choices=["linear", "smooth", "there_and_back", "wiggle"],
                value="smooth",
                label="Drawing style",
                interactive=True
            )

    with gr.Row():
        input_img = gr.Image(label="Input doodle/photo", type="filepath")
        sketch_preview = gr.Image(label="Sketch preview", type="filepath")
        video_preview = gr.Video(label="Video preview", autoplay=True)

    with gr.Row():
        btn_sketch = gr.Button("Generate sketch")
        btn_video = gr.Button("Generate video")
        useless = gr.Button("(╯°□°）╯︵ ┻━┻")  # Just for fun, no functionality


    svg_path_state = gr.State(value="")

    # Contract: sketch2svg(image_path) -> (sketch_preview_path, svg_path)
    btn_sketch.click(
        fn=sketch2svg,
        inputs=input_img,
        outputs=[sketch_preview, svg_path_state]
    )

    def _guard_convert(svg_path, dur, delay, scale, drawtype):
        """Guard against empty SVG path before conversion."""
        if not svg_path:
            return None
        return convert_svg_to_mp4(svg_path, dur, delay, scale, drawtype)

    btn_video.click(
        fn=_guard_convert,
        inputs=[svg_path_state, manim_dur, manim_delay, manim_scale, manim_drawtype],
        outputs=video_preview
    )

# Consider configuring the port via environment variable in production
demo.launch(server_port=7880)
