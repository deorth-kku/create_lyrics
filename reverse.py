from PIL import Image, ImageOps

def invert_if_black_bg_white_text(png_path: str, threshold: float = 128.0) -> bool:
    """
    检测 PNG 是否为黑底白字，如果是则反色并覆盖原文件。

    :param png_path: PNG 文件路径
    :param threshold: 平均亮度阈值，越小越“黑”
    :return: 是否执行了反色
    """
    img = Image.open(png_path).convert("RGB")

    # 转为灰度计算亮度
    gray = img.convert("L")
    pixels = gray.getdata()

    avg_luminance = sum(pixels) / len(pixels)

    if avg_luminance < threshold:
        inverted = ImageOps.invert(img)
        inverted.save(png_path)
        return True

    return False

from config import source,dist
import os
from collections.abc import Generator
from paddle1 import dopaddleocr

def reversefiles()->Generator[str]:
    for file in os.listdir(source):
        file=os.path.join(source,file)
        if invert_if_black_bg_white_text(file,10):
            print("reversed file %s"%file)
            yield file

if __name__=="__main__":
    files=list(reversefiles())
    dopaddleocr(files,dist)