import whisperx
import json

def align_lyrics(audio_path: str, lyrics: list[str],model="large-v3") -> dict[float, str]:
    device = "cuda"
    model = whisperx.load_model(model, device)

    # Speech-to-text
    result = model.transcribe(audio_path, language="ja")
    
    # Load alignment model
    align_model, metadata = whisperx.load_align_model(
        language_code="ja", device=device
    )
    aligned = whisperx.align(
        result["segments"],
        align_model,
        metadata,
        audio_path,
        device
    )

    # 将 STT 文本与输入 lyrics 对齐（简单匹配，可升级）
    output = {}
    idx = 0
    words = aligned["word_segments"]

    for line in lyrics:
        # 简单策略：找到下一句的第一个词
        while idx < len(words) and line.strip() not in words[idx]["text"]:
            idx += 1
        if idx < len(words):
            output[round(words[idx]["start"], 2)] = line

    return output
# Example usage
if __name__ == "__main__":
    # demo
    audio = r"F:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus\mods\EdenDarkPack\rom\sound\song\pv_1315.ogg"
    lyrics = [
        "イタい芝居　子細らしい",
        "あたし能無し　アイロニー",
        "",
        "自愛　痴態　痛々しい",
        "中身の無い　人でなし",
        "",
        "餌に釣られ死んだ　この底は屠所よろしく",
        "猪口才な理想で他人を疎んでもなんにもなんないな",
        "",
        "どいつもこいつも要らない",
        "とか下衆な邪意に憑かれて",
        "",
        "ああ　地獄に堕ちるだけ",
        "",
        "なんて",
        "",
        "あらあらあら",
        "お気の毒ね",
        "それじゃ面白くなくなくない",
        "",
        "唯唯唯",
        "与太な人生",
        "",
        "誰か手放しで肯定して",
        "",
        "ほらほらほら",
        "唾棄して憎め",
        "蛇蝎の如く嫌って忌んで",
        "",
        "白々しく愛を謳う",
        "果てしなくそれは幸福でしょうね",
        "",
        "",
        "善も悪も　毒も薬も",
        "仕分けられない　馬鹿な神様",
        "",
        "「恙無い」は続かないわ",
        "救えないわ　お気の毒様",
        "",
        "",
        "嫌い　嫌い　忌々しい",
        "正しさなどないのに",
        "",
        "悲哀　擬態　見ないふり",
        "そう　お前のことだよ",
        "",
        "",
        "切っても断っても消えない",
        "やれ情だの性が邪魔して",
        "もう喉元過ぎれば甘酸苦楽もぐっちゃぐちゃになって",
        "",
        "どうにもこうにもできない",
        "屈まって耳を塞いで",
        "",
        "はー　なんとも無様な生き様だ",
        "",
        "あらあらあら",
        "お気の毒ね",
        "それじゃ面白くなくなくない",
        "",
        "まだまだまだ",
        "無駄な人生の道を這いずる",
        "天国まで",
        "",
        "つらつらつら",
        "駄文を綴る",
        "夢だの愛だの　どうだっていい",
        "",
        "甚だしく悲壮な今を",
        "生きるためアイを売ってる",
        "",
        "",
        "なんて",
        "",
        "あらあらあら",
        "お気の毒ね",
        "それじゃ面白くなくなくない",
        "",
        "唯唯唯",
        "与太な人生",
        "",
        "誰か手放しで肯定して",
        "",
        "ほらほらほら",
        "唾棄して憎め",
        "蛇蝎の如く嫌って忌んで",
        "",
        "白々しく愛を謳う",
        "果てしなくそれは幸福でしょうね",
        "",
        "",
        "善も悪も　毒も薬も",
        "仕分けられない　馬鹿な神様",
        "",
        "「恙無い」は続かないわ",
        "救えないわ　お気の毒様",
    ]
    d = align_lyrics(audio, lyrics)
    print(json.dumps(d, ensure_ascii=False, indent=2))