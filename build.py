#!/usr/bin/env python3
"""Génère dark_mode.svg / light_mode.svg (profil style neofetch) pour g-amoros."""
import json, os, subprocess, sys
from html import escape
from PIL import Image, ImageOps, ImageEnhance

USER = "g-amoros"
COLS = 96
ART_FS, ART_LH = 7, 8.4
ART_W = COLS * ART_FS * 0.6   # police ASCII ; interligne = 2 x largeur de caractère
RAMP = " .,:;-=+*#%@"

def ascii_art(invert):
    cut = os.path.exists("avatar_cutout.png")
    raw = Image.open("avatar_cutout.png" if cut else "avatar.png").convert("RGBA")
    alpha = raw.getchannel("A")
    src = raw.convert("RGB")
    w, h = src.size
    opaque = not cut and alpha.getextrema()[0] == 255
    # photo sans transparence : cadrage serré sur la tête + masque elliptique
    box = (int(w*.20), int(h*.24), int(w*.66), int(h*.70)) if opaque else (int(w*.14), int(h*.11), int(w*.88), int(h*.99))
    if cut:
        l, t, r, b = alpha.point(lambda a: 255 if a > 128 else 0).getbbox()
        box = (l, t, r, t + int((b - t) * .72))  # tête + épaules
    src = src.crop(box)
    alpha = alpha.crop(box).resize((COLS, int(COLS * src.size[1] / src.size[0] * 0.5)), Image.BOX).load()
    hsv = src.convert("HSV")
    gray = ImageOps.autocontrast(src.convert("L"), cutoff=1)
    rows = int(COLS * src.size[1] / src.size[0] * 0.5)
    gray = gray.resize((COLS, rows), Image.LANCZOS)
    # contraste local (unsharp fort) pour faire ressortir yeux, sourcils, nez, barbe
    from PIL import ImageFilter
    gray = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=160, threshold=0))
    hsv = hsv.resize((COLS, rows), Image.BOX)
    g, hp = gray.load(), hsv.load()
    def is_bg(x, y):
        hh, ss, _ = hp[x, y]
        if opaque:
            dx, dy = (x / COLS - .5) / .46, (y / rows - .5) / .5
            return dx * dx + dy * dy > 1
        return alpha[x, y] < 128 or (not cut and 35 < hh < 125 and ss > 55)
    vals = sorted(g[x, y] for y in range(rows) for x in range(COLS) if not is_bg(x, y))
    lo, hi = vals[int(len(vals) * .03)], vals[int(len(vals) * .97)]
    out = []
    for y in range(rows):
        line = ""
        for x in range(COLS):
            # fond = vert/jaune (teinte ~ 40-120 sur 255) ou transparent ; la peau est orangée (<30)
            if is_bg(x, y):
                line += " "
                continue
            lum = min(1, max(0, (g[x, y] - lo) / (hi - lo)))
            v = (lum if invert else 1 - lum) ** 0.5
            line += RAMP[min(len(RAMP) - 1, int(v * len(RAMP)))]
        out.append(line.rstrip())
    return out

def gql(query, **vars):
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in vars.items():
        args += ["-F", f"{k}={v}"]
    return json.loads(subprocess.check_output(args))["data"]

def stats():
    d = gql("""query($u:String!){user(login:$u){createdAt followers{totalCount}
      repositories(first:100,ownerAffiliations:OWNER){totalCount nodes{stargazerCount}}
      repositoriesContributedTo(first:1,contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){totalCount}
      contributionsCollection{totalCommitContributions restrictedContributionsCount}}}""", u=USER)["user"]
    from datetime import datetime, timezone
    year0 = int(d["createdAt"][:4])
    commits = 0
    for y in range(year0, datetime.now(timezone.utc).year + 1):
        c = gql("""query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){contributionsCollection(from:$f,to:$t){
          totalCommitContributions restrictedContributionsCount}}}""", u=USER, f=f"{y}-01-01T00:00:00Z", t=f"{y}-12-31T23:59:59Z")["user"]["contributionsCollection"]
        commits += c["totalCommitContributions"] + c["restrictedContributionsCount"]
    return {
        "repos": d["repositories"]["totalCount"],
        "contributed": d["repositoriesContributedTo"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in d["repositories"]["nodes"]),
        "commits": commits,
        "followers": d["followers"]["totalCount"],
        "since": year0,
    }

def lines(s):
    """(type, key, value) ; type: head | kv | blank"""
    return [
        ("head", "gael@amoros", ""),
        ("kv", "OS", "macOS"),
        ("kv", "Coding.Since", f"{s['since']} ({datetime_years(s['since'])} ans)"),
        ("kv", "Role", "Fondateur & développeur"),
        ("kv", "Company", "Chauffleet (SaaS gestion de flotte VTC)"),
        ("kv", "Studies", "Avignon Université (CERI)"),
        ("kv", "IDE", "VS Code, Claude Code"),
        ("blank", "", ""),
        ("kv", "Languages.Programming", "TypeScript, Rust, SQL, C++"),
        ("kv", "Languages.Computer", "HTML, CSS, JSON, YAML"),
        ("kv", "Languages.Real", "Français, English"),
        ("blank", "", ""),
        ("kv", "Stack", "React, Next.js, Node, Postgres, Supabase"),
        ("kv", "Infra", "Docker, Redis, gRPC, Coolify"),
        ("blank", "", ""),
        ("head", "- GitHub Stats", ""),
        ("kv", "Repos", f"{s['repos']} {{Contributed: {s['contributed']}}}"),
        ("kv", "Stars", str(s["stars"])),
        ("kv", "Commits", f"{s['commits']:,}".replace(",", " ")),
        ("kv", "Followers", str(s["followers"])),
    ]

def datetime_years(y):
    from datetime import date
    return date.today().year - y

THEMES = {
    "dark_mode":  dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", val="#a5d6ff", head="#ffa657", dots="#616e7f"),
    "light_mode": dict(bg="#f6f8fa", fg="#24292f", key="#953800", val="#0a3069", head="#953800", dots="#a2a9b1"),
}
FS, LH, CW = 14, 20, 8.4   # font-size, line-height, largeur caractère (Courier-ish)
RIGHT_COLS = 62

def svg(theme, art, rows):
    t = THEMES[theme]
    x_art, x_txt = 16, 16 + int(ART_W) + 30
    h = max(len(art) * ART_LH, len(rows) * LH) + 40
    w = x_txt + int((RIGHT_COLS + 2) * CW) + 16
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">',
         f'<rect width="100%" height="100%" rx="15" fill="{t["bg"]}"/>',
         f'<g font-size="{ART_FS}" fill="{t["fg"]}">']
    for i, l in enumerate(art):
        cs = [(j, c) for j, c in enumerate(l) if c != " "]
        if not cs:
            continue
        xs = " ".join(f"{x_art + j * ART_FS * 0.6:.1f}" for j, _ in cs)
        o.append(f'<text x="{xs}" y="{28 + i*ART_LH:.1f}">{escape("".join(c for _, c in cs))}</text>')
    o.append('</g>')
    o.append(f'<text x="{x_txt}" y="30" font-size="{FS}" fill="{t["fg"]}" xml:space="preserve">')
    for i, (typ, k, v) in enumerate(rows):
        y = 30 + i * LH
        if typ == "head":
            n = RIGHT_COLS - len(k) - 1
            o.append(f'<tspan x="{x_txt}" y="{y}" fill="{t["head"]}">{escape(k)}</tspan><tspan fill="{t["dots"]}"> {"—"*n}</tspan>')
        elif typ == "kv":
            n = max(2, RIGHT_COLS - len(k) - len(v) - 5)
            o.append(f'<tspan x="{x_txt}" y="{y}" fill="{t["dots"]}">. </tspan><tspan fill="{t["key"]}">{escape(k)}</tspan>:<tspan fill="{t["dots"]}"> {"."*n} </tspan><tspan fill="{t["val"]}">{escape(v)}</tspan>')
    o.append('</text></svg>')
    return "\n".join(o)

if __name__ == "__main__":
    s = json.load(open("stats.json")) if "--offline" in sys.argv else stats()
    json.dump(s, open("stats.json", "w"))
    rows = lines(s)
    for name in THEMES:
        open(f"{name}.svg", "w").write(svg(name, ascii_art(name == "dark_mode"), rows))
    print(s)
