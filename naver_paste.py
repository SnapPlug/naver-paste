#!/usr/bin/env python3
"""naver_paste — 마크다운 원고를 네이버 블로그 편집기에 문단씩 붙여 넣는다 (macOS + Google Chrome).

사람이 메모장에서 문단을 복사해 붙이는 방식이다. 맥의 진짜 키 입력을 쓴다.
발행 버튼은 누르지 않는다. 사진 설명·발행 창 태그·발행은 직접 한다.

쓰는 법:
  python3 naver_paste.py 원고.md --dry   # 어떻게 나뉘는지만 본다
  python3 naver_paste.py --sample        # 짧은 시험 글
  python3 naver_paste.py 원고.md         # 실제 입력

원고 형식(예시.md 참고):
  # 제목            ← 첫 번째 '# ' 줄이 제목
  ## 소제목 또는 **소제목**   ← 굵게 들어간다
  ![사진 설명](사진.png)    ← 사진(원고 파일 기준 경로, png)
  나머지 줄          ← 문단 하나씩, 사이에 빈 줄

준비: 크롬에서 네이버 블로그 글쓰기 화면을 연다. 시작하면 8초 안에 제목 칸을 클릭한다.
멈추기: 터미널에서 Ctrl+C. 크롬이 맨 앞에서 내려가면 스크립트가 스스로 멈춘다.
권한: 스크립트를 돌리는 터미널 앱에 '손쉬운 사용' 권한이 있어야 한다.
"""
import html
import random
import re
import subprocess
import sys
import time
from pathlib import Path


SAMPLE = """# 시험 제목입니다

첫 문단입니다. 붙여 넣기가 되는지 봅니다.

## 굵은 소제목 시험

소제목 다음 문단입니다. 이 문단은 굵으면 안 됩니다.

#시험태그 #블로그
"""


def osa(script: str) -> None:
    subprocess.run(["osascript", "-e", script], check=True)


def key(k: str, mods: str = "") -> None:
    """mods 예: 'command down' / 'command down, shift down'. k는 글자 또는 key code 숫자."""
    using = f" using {{{mods}}}" if mods else ""
    if k.isdigit():
        osa(f'tell application "System Events" to key code {k}{using}')
    else:
        osa(f'tell application "System Events" to keystroke "{k}"{using}')


ENTER, V, B = "36", "9", "11"  # 키 번호. 글자("v")로 보내면 한글 입력기에서 Cmd+V가 안 먹는다


def frontmost() -> str:
    return subprocess.run(["osascript", "-e", 'tell application "System Events" to name of first process whose frontmost is true'],
                          capture_output=True, text=True).stdout.strip()


def guard() -> None:
    """크롬이 맨 앞이 아니면 멈춘다. 다른 앱(Finder·터미널)에 Enter·붙여넣기가 새는 것을 막는다."""
    front = frontmost()
    if front != "Google Chrome":
        sys.exit(f"\n멈춤: 맨 앞 창이 크롬이 아니라 '{front}'입니다. 크롬 편집기를 확인한 뒤 다시 시작하세요.")


def clip_text(text: str, bold: bool = False) -> None:
    """글을 클립보드에 넣는다. 굵게는 HTML로 넣어 편집기가 서식을 받게 한다."""
    body = html.escape(text)
    h = (f"<b>{body}</b>" if bold else f"<span>{body}</span>").encode().hex()
    plain = text.replace("\\", "\\\\").replace('"', '\\"')
    osa(f'set the clipboard to {{«class HTML»:«data HTML{h}», string:"{plain}"}}')


def clip_image(p: Path) -> None:
    osa(f'set the clipboard to (read (POSIX file "{p}") as «class PNGf»)')


def pause(text: str = "") -> None:
    # ponytail: 문단 길이에 비례한 쉼 + 가끔 긴 쉼. 사람 기록으로 맞춘 값은 아니다.
    t = random.uniform(1.5, 4.0) + len(text) * random.uniform(0.01, 0.03)
    if random.random() < 0.12:
        t += random.uniform(5, 15)
    time.sleep(t)


def parse(md: str, base: Path):
    """원고를 (제목, 할 일 목록)으로 나눈다. 할 일 = ('text'|'bold'|'image', 값)."""
    title, steps = None, []
    for line in (l.strip() for l in md.splitlines()):
        if not line:
            continue
        if title is None and line.startswith("# "):
            title = line[2:].strip()
        elif m := re.fullmatch(r"!\[(.*?)\]\((.+?)\)", line):
            steps.append(("image", ((base / m.group(2)).resolve(), m.group(1))))
        elif m := re.fullmatch(r"#{2,6} (.+)|\*\*(.+)\*\*", line):
            steps.append(("bold", m.group(1) or m.group(2)))
        else:
            steps.append(("text", line.replace("**", "")))  # ponytail: 문단 안 일부 굵게는 버린다
    assert title, "첫 '# 제목' 줄이 없습니다."
    return title, steps


def run(title: str, steps) -> None:
    for s in range(8, 0, -1):
        print(f"\r{s}초 안에 크롬 편집기의 제목 칸을 클릭하세요…", end="", flush=True)
        time.sleep(1)
    print()
    osa('tell application "Google Chrome" to activate')
    time.sleep(0.5)
    print("실행 중에는 맥을 만지지 마세요. 크롬이 앞에서 내려가면 바로 멈춥니다.")
    clip_text(title)
    guard()
    key(V, "command down")
    pause()
    guard()
    key(ENTER)  # 제목에서 Enter = 본문 첫 줄
    captions = []
    for n, (kind, val) in enumerate(steps, 1):
        if kind == "image":
            path, cap = val
            clip_image(path)
            captions.append(cap)
        else:
            clip_text(val, bold=(kind == "bold"))
        guard()
        key(V, "command down")
        time.sleep(random.uniform(0.6, 1.2) if kind != "image" else 4)  # 사진 올라가는 시간
        if n < len(steps):
            guard()
            key(ENTER)
            if kind == "bold":
                guard()
                key(B, "command down")  # 굵게가 다음 줄로 이어진다 → 끈다
            guard()
            key(ENTER)  # 문단 사이 빈 줄
        print(f"{n}/{len(steps)} {kind} {str(val)[:30]}")
        pause(val if isinstance(val, str) else "")
    print("\n끝. 발행은 누르지 않았습니다. 사진 설명을 넣어 주세요:")
    for i, c in enumerate(captions):
        print(f"  {i + 1}. {c}")


def main() -> None:
    args = sys.argv[1:]
    if "--sample" in args:
        md, base = SAMPLE, Path.cwd()
    else:
        src = Path(next(a for a in args if not a.startswith("--")))
        md, base = src.read_text(), src.parent
    title, steps = parse(md, base)
    missing = [v[0] for k, v in steps if k == "image" and not v[0].exists()]
    assert not missing, f"사진 파일 없음: {missing}"
    if "--dry" in args:
        print("제목:", title)
        for k, v in steps:
            print(f"[{k}] {str(v)[:70]}")
        return
    run(title, steps)


if __name__ == "__main__":
    main()
