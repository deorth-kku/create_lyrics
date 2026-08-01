import sys
import re
import json
import base64
import gzip
import requests
from bs4 import BeautifulSoup
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def fetch_page(movie_id):
    """请求页面，解析出 game-token, lyrics-key, csrf-token"""
    url = f"https://typing-tube.net/movie/show/{movie_id}"
    resp = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) Gecko/20100101 Firefox/153.0",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8",
    })
    resp.raise_for_status()
    html = resp.text

    soup = BeautifulSoup(html, "html.parser")

    game_token = soup.find("meta", attrs={"name": "game-token"})["content"]
    lyrics_key = soup.find("meta", attrs={"name": "lyrics-key"})["content"]
    csrf_token = soup.find("meta", attrs={"name": "csrf-token"})["content"]

    return game_token, lyrics_key, csrf_token, resp.cookies


def fetch_lyrics_raw(movie_id, game_token, csrf_token, cookies):
    """构造 API 请求，获取加密歌词数据"""
    url = f"https://typing-tube.net/api/lyrics/{movie_id}?token={game_token}"
    resp = requests.post(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) Gecko/20100101 Firefox/153.0",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-Token": csrf_token,
        "Origin": "https://typing-tube.net",
        "Referer": f"https://typing-tube.net/movie/show/{movie_id}",
    }, cookies=cookies)
    resp.raise_for_status()

    # 服务器返回的是 zstd 压缩的 JSON
    data = resp.json()
    return data


def decrypt_lyrics(lyrics_key, encrypted, iv, auth_tag):
    """使用 lyrics-key 解密歌词"""
    key_bytes = base64.b64decode(lyrics_key)
    iv_bytes = base64.b64decode(iv)
    ct_bytes = base64.b64decode(encrypted)
    tag_bytes = base64.b64decode(auth_tag)

    combined = ct_bytes + tag_bytes
    plain = AESGCM(key_bytes).decrypt(iv_bytes, combined, None)
    return plain.decode("utf-8")


def main():
    if len(sys.argv) < 2:
        movie_id = input("请输入 movie ID: ").strip()
    else:
        movie_id = sys.argv[1].strip()

    if not movie_id.isdigit():
        print("错误: 请输入有效的数字 ID")
        sys.exit(1)

    print(f"[1/4] 请求页面 https://typing-tube.net/movie/show/{movie_id} ...")
    game_token, lyrics_key, csrf_token, cookies = fetch_page(movie_id)
    print(f"  game-token: {game_token}")
    print(f"  lyrics-key: {lyrics_key}")
    print(f"  csrf-token: {csrf_token}")

    print(f"\n[2/4] 请求 API 获取加密歌词 ...")
    data = fetch_lyrics_raw(movie_id, game_token, csrf_token, cookies)
    encrypted = data["encrypted"]
    iv = data["iv"]
    auth_tag = data["auth_tag"]
    print(f"  encrypted 长度: {len(encrypted)}")
    print(f"  iv: {iv}")
    print(f"  auth_tag: {auth_tag}")

    print(f"\n[3/4] 使用 lyrics-key 解密 ...")
    lyrics = decrypt_lyrics(lyrics_key, encrypted, iv, auth_tag)

    print(f"\n[4/4] 明文歌词:")
    print("=" * 60)
    print(lyrics)
    print("=" * 60)

    # 保存到文件
    output_file = f"{movie_id}_lyrics.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(lyrics)
    print(f"\n已保存至 {output_file}")


if __name__ == "__main__":
    main()
