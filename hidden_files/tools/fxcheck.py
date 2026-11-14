# Structural invariance check: the ordered sequences of fx objects, photo
# assignments, branch conditions and BUZZ keys in the working tree must be
# identical to HEAD. Used after every text-only rewrite pass.
import re, subprocess, sys

def seqs(src):
    return {
        "fx": re.findall(r"fx:\{[^}]*\}", src),
        "img": re.findall(r'img:"assets/[^"]*"', src),
        "cond": re.findall(r"cond:s=>[^,]+", src),
        "buzz": re.findall(r'\bk:"[^"]+"', src),
    }

old = subprocess.run(["git", "show", "HEAD:index.html"], capture_output=True, text=True).stdout
new = open("index.html").read()
so, sn = seqs(old), seqs(new)
ok = True
for k in so:
    same = so[k] == sn[k]
    ok &= same
    print(f"{k} count old/new: {len(so[k])} {len(sn[k])} {'IDENTICAL' if same else 'DIFFERS'}")
    if not same:
        for i, (a, b) in enumerate(zip(so[k], sn[k])):
            if a != b:
                print(f"  first diff at {i}: old={a!r} new={b!r}")
                break
sys.exit(0 if ok else 1)
