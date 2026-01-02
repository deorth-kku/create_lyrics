import os
from collections.abc import Generator
from paddleocr import PaddleOCR
import subprocess
import sys
# 初始化 PaddleOCR 实例
def getfiles(source:str)->Generator[str]:
    for file in os.listdir(source):
        yield os.path.join(source,file)

if __name__=="__main__":
    ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    lang="japan")

    source=r"E:\ocr\source"
    dist=r"E:\ocr\dst"

    
    for file in getfiles(source):
        os.remove(file)
    
    for file in getfiles(dist):
        os.remove(file)

    subprocess.call(args=["ffmpeg","-i",sys.argv[1],os.path.join(source,"%05d.png")])


    # 对示例图像执行 OCR 推理 
    result = ocr.predict_iter(
        input=list(getfiles(source)))
    
    from concurrent.futures import ThreadPoolExecutor

    pool=ThreadPoolExecutor(max_workers=5)


    # 可视化结果并保存 json 结果
    for res in result:
        pool.submit(res.save_to_img,dist)
        pool.submit(res.save_to_json,dist)