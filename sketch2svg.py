import io
import  sys
import subprocess
from PIL import Image

if sys.platform == "win32":
    executable_path = "potrace.exe"
else:
    executable_path = "potrace"

def sketch2svg(
    img_path: str,
    output_path: str =""
        ):
    
    print(f"Processing image: {img_path}", file=sys.stderr)
    im = Image.open(img_path)
    gray = im.convert("L")
    bw = gray.point(lambda x: 0 if x < 128 else 1, mode='1')
    buf = io.BytesIO()
    bw.save(buf, format='BMP')
    pbm_data = buf.getvalue()
    
    proc = subprocess.run(
            [f"{executable_path}", "-s", "--group", "-o", "-"],
            input=pbm_data,
            stdout=subprocess.PIPE,
            check=True
    )
    svg_data = proc.stdout
    if not output_path:
        output_path = img_path.rsplit('.', 1)[0] + ".svg"
    with open(output_path, "wb") as f:
        f.write(svg_data)

    print(f"SVG saved to: {output_path}", file=sys.stderr)
    
    return output_path, output_path
