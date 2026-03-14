import json
import pathlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from emulator.runtime_state import snapshot


def _length_to_feet(length_label):
    if str(length_label).strip().lower() == "25 yards":
        return 75.0
    return 164.042


def _load_pool_profile():
    root = pathlib.Path(__file__).resolve().parents[1]
    pools_path = root / "db" / "pools.json"
    with pools_path.open("r", encoding="utf-8") as f:
        pools_data = json.load(f)

    default_name = pools_data.get("defaultPool")
    pool = pools_data.get("pools", {}).get(default_name, {})
    segments = pool.get("Segments", [])
    return {
        "pool_name": default_name,
        "length_feet": _length_to_feet(pool.get("Length", "")),
        "pixel_count": int(pool.get("PixelCount", 0)),
        "segments": [
            {
                "first_pixel": int(s.get("FirstPixel", 0)),
                "distance": float(s.get("Distance", 0.0)),
                "depth": float(s.get("Depth", s.get("depth", 0.0))),
            }
            for s in segments
        ],
    }


_POOL_PROFILE = _load_pool_profile()
_POOL_PROFILE_JSON = json.dumps(_POOL_PROFILE)


_HTML = """<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Rabbit Emulator Viewer</title>
  <style>
    body { font-family: monospace; margin: 0; padding: 16px; background: #0f1115; color: #d7dde5; }
    h1 { margin: 0 0 8px 0; font-size: 18px; }
    a { color: #5bc0eb; }
    .row { display: grid; grid-template-columns: 1fr; gap: 14px; }
    .panel { border: 1px solid #2a2f3a; border-radius: 8px; padding: 12px; background: #171b22; }
    #ledwrap { background: #121720; border: 1px solid #2a2f3a; padding: 8px; border-radius: 6px; }
    #led { width: 100%; height: 220px; display: block; }
    .status { margin: 6px 0; color: #d0d7e2; }
    #oled { border: 1px solid #333; padding: 8px; min-height: 72px; background: #000; color: #8aff8a; white-space: pre-wrap; }
    .meta { color: #9aa4b2; margin-top: 8px; }
  </style>
</head>
<body>
  <h1>Rabbit Emulator</h1>
  <div><a href=\"http://127.0.0.1:8080/\" target=\"_blank\">Open Rabbit Web UI</a></div>
  <div class=\"row\">
    <div class=\"panel\">
      <div><strong>LED Strand</strong></div>
      <div id=\"status\" class=\"status\">loading...</div>
      <div id=\"ledwrap\"><canvas id=\"led\"></canvas></div>
      <div id=\"ledmeta\" class=\"meta\"></div>
    </div>
    <div class=\"panel\">
      <div><strong>OLED Display</strong></div>
      <div id=\"oled\"></div>
      <div id=\"oledmeta\" class=\"meta\"></div>
    </div>
  </div>
<script>
var POOL_PROFILE = __POOL_PROFILE_JSON__;

function buildControlPoints(profile) {
  var pts = [];
  for (var i = 0; i < profile.segments.length; i += 1) {
    pts.push({
      fp: profile.segments[i].first_pixel,
      dist: profile.segments[i].distance,
      depth: profile.segments[i].depth
    });
  }
  pts.sort(function (a, b) { return a.fp - b.fp; });

  if (pts.length === 0) {
    pts.push({ fp: 0, dist: 0, depth: 0 });
  }
  if (pts[0].dist > 0) {
    pts.unshift({ fp: pts[0].fp, dist: 0, depth: pts[0].depth });
  }

  var poolLen = profile.length_feet > 0 ? profile.length_feet : 75.0;
  var poolPix = profile.pixel_count > 0 ? profile.pixel_count : pts[pts.length - 1].fp;
  if (poolPix > pts[pts.length - 1].fp) {
    pts.push({ fp: poolPix, dist: poolLen, depth: pts[pts.length - 1].depth });
  } else if (poolLen > pts[pts.length - 1].dist) {
    pts.push({ fp: pts[pts.length - 1].fp, dist: poolLen, depth: pts[pts.length - 1].depth });
  }
  return pts;
}

function buildDepthProfile(profile) {
  return buildControlPoints(profile);
}

function pointForPixel(pixel, profilePts) {
  if (pixel <= profilePts[0].fp) {
    return { dist: profilePts[0].dist, depth: profilePts[0].depth };
  }
  for (var i = 0; i < profilePts.length - 1; i += 1) {
    var a = profilePts[i];
    var b = profilePts[i + 1];
    if (pixel <= b.fp) {
      var denom = (b.fp - a.fp);
      var t = denom > 0 ? (pixel - a.fp) / denom : 0;
      return {
        dist: a.dist + (b.dist - a.dist) * t,
        depth: a.depth + (b.depth - a.depth) * t
      };
    }
  }
  var last = profilePts[profilePts.length - 1];
  return { dist: last.dist, depth: last.depth };
}

function refresh() {
  var status = document.getElementById('status');
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/state', true);
  xhr.onreadystatechange = function () {
    if (xhr.readyState !== 4) {
      return;
    }
    if (xhr.status < 200 || xhr.status >= 300) {
      status.textContent = 'fetch error: HTTP ' + xhr.status;
      document.getElementById('ledmeta').textContent = 'no LED state available';
      return;
    }

    var state;
    try {
      state = JSON.parse(xhr.responseText);
    } catch (e) {
      status.textContent = 'parse error: ' + e.message;
      document.getElementById('ledmeta').textContent = 'invalid LED state';
      return;
    }

    var led = document.getElementById('led');
    var wrap = document.getElementById('ledwrap');
    led.width = Math.max(1, wrap.clientWidth - 16);
    led.height = 220;
    var ctx = led.getContext('2d');
    ctx.clearRect(0, 0, led.width, led.height);
    ctx.fillStyle = '#1c222d';
    ctx.fillRect(0, 0, led.width, led.height);

    var lit = 0;
    var count = state.led.pixels.length;
    var profilePts = buildDepthProfile(POOL_PROFILE);
    var poolLen = POOL_PROFILE.length_feet > 0 ? POOL_PROFILE.length_feet : 75.0;
    var maxDepth = 0.0;
    for (var d = 0; d < profilePts.length; d += 1) {
      if (profilePts[d].depth > maxDepth) {
        maxDepth = profilePts[d].depth;
      }
    }
    if (maxDepth <= 0) {
      maxDepth = 1.0;
    }

    var pad = 10;
    var usableW = Math.max(1, led.width - pad * 2);
    var usableH = Math.max(1, led.height - pad * 2);

    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (var pi = 0; pi < profilePts.length; pi += 1) {
      var px = pad + (profilePts[pi].dist / poolLen) * usableW;
      var py = pad + (profilePts[pi].depth / maxDepth) * usableH;
      if (pi === 0) {
        ctx.moveTo(px, py);
      } else {
        ctx.lineTo(px, py);
      }
    }
    ctx.stroke();

    for (var i = 0; i < count; i += 1) {
      var p = state.led.pixels[i];
      var pos = pointForPixel(i, profilePts);
      var x = pad + (pos.dist / poolLen) * usableW;
      var y = pad + (pos.depth / maxDepth) * usableH;
      if (p[0] !== 0 || p[1] !== 0 || p[2] !== 0) {
        lit += 1;
      }
      ctx.fillStyle = 'rgb(' + p[0] + ', ' + p[1] + ', ' + p[2] + ')';
      ctx.beginPath();
      ctx.arc(x, y, 2.5, 0, 2 * Math.PI);
      ctx.fill();
    }

    document.getElementById('ledmeta').textContent =
      'pool=' + POOL_PROFILE.pool_name + ', pixels=' + state.led.count + ', lit=' + lit + ', writes=' + state.led.write_count;
    status.textContent = 'ok';

    var oled = document.getElementById('oled');
    var lines = [];
    for (var j = 0; j < state.display.ops.length; j += 1) {
      var o = state.display.ops[j];
      lines.push('[' + o.x + ',' + o.y + '] ' + o.text);
    }
    oled.textContent = lines.join('\\n');
    document.getElementById('oledmeta').textContent =
      'size=' + state.display.width + 'x' + state.display.height + ', shows=' + state.display.show_count;
  };
  xhr.send();
}

setInterval(refresh, 300);
refresh();
</script>
</body>
</html>"""
_HTML = _HTML.replace("__POOL_PROFILE_JSON__", _POOL_PROFILE_JSON)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._send_text(_HTML, content_type="text/html; charset=utf-8")
            return
        if self.path == "/state":
            self._send_json(snapshot())
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        _ = (format, args)

    def _send_text(self, body, content_type="text/plain; charset=utf-8"):
        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, obj):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def start_viewer(host="127.0.0.1", port=8081):
    server = ThreadingHTTPServer((host, int(port)), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
