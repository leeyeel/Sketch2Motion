import io
import  sys
import subprocess
from PIL import Image


def sketch2svg(
    img_path: str,
    output_path: str 
        ):
    im = Image.open(img_path)
    gray = im.convert("L")
    bw = gray.point(lambda x: 0 if x < 128 else 1, mode='1')
    buf = io.BytesIO()
    bw.save(buf, format='BMP')
    pbm_data = buf.getvalue()
    
    proc = subprocess.run(
            ["potrace", "-s", "--group", "-o", "-"],
            input=pbm_data,
            stdout=subprocess.PIPE,
            check=True
    )
    svg_data = proc.stdout
    with open(output_path, "wb") as f:
        f.write(svg_data)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"usage: {sys.argv[0]} [input] [output]")
    sketch2svg(sys.argv[1], sys.argv[2])
