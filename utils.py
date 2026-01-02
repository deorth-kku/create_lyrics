

def conv_pv_num(pv:str)->int:
    if pv.startswith("pv_"):
        return int(pv[3:])
    else:
        return int(pv)

def ask_yes_no(prompt: str) -> bool:
    """询问用户 (y/n)，返回 True 或 False。"""
    while True:
        ans = input(f"{prompt} (y/n): ").strip().lower()
        if ans in {"y", "yes"}:
            return True
        elif ans in {"n", "no"}:
            return False
        print("please enter y or n")

def ask_for_num(prompt: str) -> int:
    while True:
        ans = input(f"{prompt}: ").strip().lower()
        try:
            num=int(ans)
        except:
            print("please enter a number")
        else:
            return num
