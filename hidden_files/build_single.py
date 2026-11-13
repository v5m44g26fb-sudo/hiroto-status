import base64, io, json, pathlib, re, sys
from PIL import Image
src = pathlib.Path.home()/"workspace/hiroto-status"
html = (src/"index.html").read_text(encoding="utf-8")
ver = re.search(r'<p class="ver">(v\d+)</p>', html).group(1)
AM = {}
for f in sorted((src/"assets").glob("*.jpg")):
    im = Image.open(f).convert("RGB")
    if im.width > 1080: im = im.resize((1080, round(im.height*1080/im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=76, optimize=True)
    AM[f"assets/{f.name}"] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
for path, uri in AM.items():
    html = html.replace(path, uri)
shim = '<script>window.__AM=' + json.dumps(AM) + ''';
(function(){var KEY="debut-status-v1";var AM=window.__AM;var rev={};for(var k in AM)rev[AM[k]]=k;
var _s=localStorage.setItem.bind(localStorage),_g=localStorage.getItem.bind(localStorage);
localStorage.setItem=function(k,v){if(k===KEY&&typeof v==="string"){for(var d in rev){if(v.indexOf(d)>=0)v=v.split(d).join(rev[d]);}}return _s(k,v);};
localStorage.getItem=function(k){var v=_g(k);if(k===KEY&&v){for(var p in AM){var q='"'+p+'"';if(v.indexOf(q)>=0)v=v.split(q).join('"'+AM[p]+'"');}}return v;};})();
</script>
<script>'''
html = html.replace("<script>\n\"use strict\"", shim + "\n\"use strict\"", 1)
out = pathlib.Path.home()/f"workspace/hiroto-status-{ver}-single.html"
out.write_text(html, encoding="utf-8")
import os; print("built:", out, round(os.path.getsize(out)/1e6,2), "MB")
