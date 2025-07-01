import cv2
import sys
import numpy as np
from typing import Optional, Tuple

def photo_to_sketch(
    img_path: str,
    sigma_s: float = 60,
    sigma_r: float = 0.07,
    shade_factor: float = 0.02,
    output_path: Optional[str] = None
) -> Tuple[np.ndarray]:
    """
    将普通照片转换为简笔画 (铅笔草图)。
    
    参数:
      img_path:       输入照片文件路径。
      sigma_s:        空间高斯滤波的 sigma，范围 [0,200]。
      sigma_r:        颜色相似度阈值，范围 [0,1]。
      shade_factor:   阴影强度因子，范围 [0,0.1]。
      output_path:    如果不为 None，则将生成的线稿图保存到该路径（PNG/JPG 均可）。
    
    返回:
      sketch_gray:  单通道灰度线稿图 (铅笔效果)。
    
    用法示例:
      sketch_gray, _ = photo_to_sketch("photo.jpg", output_path="sketch.png")
    """
    # 1. 读取原图
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"无法读取图像: {img_path}")

    # 预去噪
    denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

    # pencilSketch
    sketch_gray, sketch_color = cv2.pencilSketch(
        src=denoised,
        sigma_s=sigma_s,
        sigma_r=sigma_r,
        shade_factor=shade_factor
    )

    # 1) 二值化：将线稿中微弱灰度当作背景
    _, binary = cv2.threshold(
        sketch_gray,
        128, 255,
        cv2.THRESH_BINARY_INV  # 黑线为前景
    )
    # 2) 开操作：去掉小噪点
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

    fine_gray = cv2.bitwise_not(clean)

    if output_path:
        cv2.imwrite(output_path, fine_gray)

    return fine_gray 

if __name__ == "__main__":
    # 转换并保存
    sketch = photo_to_sketch(
        img_path= sys.argv[1],
        sigma_s=40,           # 更大值可保留更大范围的细节
        sigma_r=0.05,          # 调整颜色相似度
        shade_factor=0.01,    # 微调阴影深浅
        output_path= sys.argv[2]
    )
