#!/usr/bin/env python3
"""Download the spike model set into .planning/spikes/.models (resumable, header-checked). Q8 everywhere it fits, so quantisation stays out of the size comparison."""
import os, sys, urllib.request, urllib.error
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),".models"); os.makedirs(D,exist_ok=True)
MODELS=[("openbmb/MiniCPM5-1B-GGUF","MiniCPM5-1B-Q8_0.gguf"),("openbmb/MiniCPM5-2B-GGUF","MiniCPM5-2B-Q8_0.gguf"),("openbmb/MiniCPM5-2B-DSpark-GGUF","MiniCPM5-2.6B-DSpark.gguf"),
        ("Qwen/Qwen3-1.7B-GGUF","Qwen3-1.7B-Q8_0.gguf"),("Qwen/Qwen3-4B-GGUF","Qwen3-4B-Q8_0.gguf"),("Qwen/Qwen3-8B-GGUF","Qwen3-8B-Q8_0.gguf"),("Qwen/Qwen3-Embedding-0.6B-GGUF","Qwen3-Embedding-0.6B-Q8_0.gguf")]
if "--moe" in sys.argv: MODELS.append(("Qwen/Qwen3-30B-A3B-GGUF","Qwen3-30B-A3B-Q4_K_M.gguf"))
for repo,fn in MODELS:
    dest=os.path.join(D,fn); url=f"https://huggingface.co/{repo}/resolve/main/{fn}"
    have=os.path.getsize(dest) if os.path.exists(dest) else 0
    req=urllib.request.Request(url,headers={"User-Agent":"melodyscribe/1.0",**({"Range":f"bytes={have}-"} if have else {})})
    try: r=urllib.request.urlopen(req,timeout=60)
    except urllib.error.HTTPError as e:
        if e.code==416: print("done ",fn,flush=True); continue
        print("ERR",fn,e,flush=True); continue
    with open(dest,"ab" if have else "wb") as f:
        n=have
        while True:
            b=r.read(1<<20)
            if not b: break
            f.write(b); n+=len(b)
    ok=open(dest,"rb").read(4)==b"GGUF"
    print(("done " if ok else "BAD  "),fn,f"{n/1e9:.2f} GB",flush=True)
