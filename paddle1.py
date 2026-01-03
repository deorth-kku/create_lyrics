import os
from collections.abc import Generator
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
# 初始化 PaddleOCR 实例
def getfiles(source:str)->Generator[str]:
    for file in os.listdir(source):
        yield os.path.join(source,file)

def fakelist(source:str,count:int)->Generator[str]:
    for i in range(1,count):
        yield os.path.join(source,"%05d.png"%i)

from config import source,dist

def dopaddleocr(files:list[str],outdir:str):
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    lang="japan")
    result = ocr.predict_iter(
        input=files)
    
    pool=ThreadPoolExecutor(max_workers=5)
    # 可视化结果并保存 json 结果
    for res in result:
        pool.submit(res.save_to_img,outdir)
        pool.submit(res.save_to_json,outdir)

if __name__=="__main__":
    
    for file in getfiles(source):
        os.remove(file)
    
    for file in getfiles(dist):
        os.remove(file)

    


    #args=["ffmpeg","-threads","1","-i",sys.argv[1], "-vf", "crop=434:40:206:320,negate",os.path.join(source,"%05d.png")]
    args=["ffmpeg","-threads","1","-i",sys.argv[1],os.path.join(source,"%05d.png")]

    subprocess.Popen(args,creationflags=subprocess.IDLE_PRIORITY_CLASS)

    dopaddleocr(list(fakelist(source,10000)),dist)
    