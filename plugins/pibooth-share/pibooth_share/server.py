# -*- coding: utf-8 -*-

"""Lightweight web server to share photos and serve a gallery."""

import os
import os.path as osp
import threading
import logging
from io import BytesIO
from PIL import Image
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

LOGGER = logging.getLogger("pibooth")

GALLERY_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a2e;
            color: #fff;
            min-height: 100vh;
        }}
        .header {{
            text-align: center;
            padding: 20px;
            background: #16213e;
        }}
        .header h1 {{
            font-size: 1.5em;
            margin-bottom: 5px;
        }}
        .header p {{
            color: #8899aa;
            font-size: 0.9em;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 8px;
            padding: 10px;
        }}
        .gallery a {{
            display: block;
            aspect-ratio: 1;
            overflow: hidden;
            border-radius: 8px;
        }}
        .gallery img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.2s;
        }}
        .gallery img:active {{
            transform: scale(0.95);
        }}
        .photo-view {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.95);
            z-index: 100;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}
        .photo-view.active {{ display: flex; }}
        .photo-view img {{
            max-width: 95%;
            max-height: 80vh;
            border-radius: 8px;
        }}
        .photo-view .actions {{
            margin-top: 15px;
            display: flex;
            gap: 15px;
        }}
        .photo-view .actions a, .photo-view .actions button {{
            color: #fff;
            background: #0f3460;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            text-decoration: none;
        }}
        .photo-view .close {{
            position: absolute;
            top: 15px;
            right: 15px;
            font-size: 2em;
            color: #fff;
            cursor: pointer;
            background: none;
            border: none;
        }}
        .photo-view .nav {{
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            font-size: 2.5em;
            color: #fff;
            background: rgba(0,0,0,0.4);
            border: none;
            cursor: pointer;
            padding: 15px 12px;
            border-radius: 8px;
        }}
        .photo-view .nav-left {{ left: 10px; }}
        .photo-view .nav-right {{ right: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>{count} photos</p>
    </div>
    <div class="gallery">
        {thumbnails}
    </div>
    <div class="photo-view" id="viewer" onclick="if(event.target===this)closeViewer()">
        <button class="close" onclick="closeViewer()">&times;</button>
        <button class="nav nav-left" id="nav-prev" onclick="navigatePhoto(-1)">&#10094;</button>
        <img id="viewer-img" src="">
        <button class="nav nav-right" id="nav-next" onclick="navigatePhoto(1)">&#10095;</button>
        <div class="actions">
            <a id="viewer-download" href="" download>Télécharger</a>
            <button onclick="closeViewer()">Fermer</button>
        </div>
        <p class="hint" style="color:#8899aa;font-size:0.85em;margin-top:8px;">ou appuyez longuement sur la photo pour l'ajouter à votre galerie</p>
    </div>
    <script>
        var photos = [{photo_list}];
        var currentIndex = 0;

        function openViewer(src) {{
            currentIndex = photos.indexOf(src);
            showPhoto(src);
            document.getElementById('viewer').classList.add('active');
        }}
        function showPhoto(src) {{
            document.getElementById('viewer-img').src = src;
            document.getElementById('viewer-download').href = src;
            document.getElementById('nav-prev').style.display = currentIndex > 0 ? 'block' : 'none';
            document.getElementById('nav-next').style.display = currentIndex < photos.length - 1 ? 'block' : 'none';
        }}
        function navigatePhoto(dir) {{
            currentIndex = Math.max(0, Math.min(photos.length - 1, currentIndex + dir));
            showPhoto(photos[currentIndex]);
        }}
        function closeViewer() {{
            document.getElementById('viewer').classList.remove('active');
        }}
        // Swipe support for mobile
        var touchStartX = 0;
        document.getElementById('viewer').addEventListener('touchstart', function(e) {{
            touchStartX = e.changedTouches[0].screenX;
        }});
        document.getElementById('viewer').addEventListener('touchend', function(e) {{
            var diff = e.changedTouches[0].screenX - touchStartX;
            if (Math.abs(diff) > 50) {{
                navigatePhoto(diff > 0 ? -1 : 1);
            }}
        }});
    </script>
</body>
</html>"""

PHOTO_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Photo</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a2e;
            color: #fff;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 15px;
        }}
        img {{
            max-width: 95%;
            max-height: 75vh;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }}
        .actions {{
            margin-top: 20px;
            display: flex;
            gap: 15px;
        }}
        .actions a, .actions button {{
            color: #fff;
            background: #0f3460;
            border: none;
            padding: 14px 28px;
            border-radius: 10px;
            font-size: 1.1em;
            text-decoration: none;
            cursor: pointer;
        }}
        .hint {{
            margin-top: 12px;
            color: #8899aa;
            font-size: 0.85em;
            text-align: center;
        }}
    </style>
</head>
<body>
    <img src="/photo/{filename}">
    <div class="actions">
        <a href="/photo/{filename}" download>Télécharger</a>
        <a href="/">Galerie</a>
    </div>
    <p class="hint">ou appuyez longuement sur la photo pour l'ajouter à votre galerie</p>
</body>
</html>"""


class ShareServer:
    """Lightweight HTTP server to share photos."""

    def __init__(self, photo_dir, port=8080, title="Photobooth"):
        self.photo_dir = osp.abspath(osp.expanduser(photo_dir))
        self.thumb_dir = osp.join(self.photo_dir, '.thumbnails')
        self.port = port
        self.title = title
        self._server = None
        self._thread = None

    def _get_thumbnail(self, filename):
        """Get or create thumbnail for a photo."""
        thumb_path = osp.join(self.thumb_dir, filename)
        if not osp.isfile(thumb_path):
            src_path = osp.join(self.photo_dir, filename)
            if not osp.isfile(src_path):
                return None
            if not osp.isdir(self.thumb_dir):
                os.makedirs(self.thumb_dir)
            try:
                img = Image.open(src_path)
                img.thumbnail((300, 300))
                img.save(thumb_path, 'JPEG', quality=80)
            except Exception as ex:
                LOGGER.warning("Failed to create thumbnail for %s: %s", filename, ex)
                return None
        return thumb_path

    def _list_photos(self):
        """List all photos sorted by date (newest first)."""
        if not osp.isdir(self.photo_dir):
            return []
        photos = [f for f in os.listdir(self.photo_dir)
                  if f.endswith('.jpg') and not f.startswith('.')]
        photos.sort(reverse=True)
        return photos

    def _create_handler(self):
        """Create HTTP request handler with access to server state."""
        server = self

        class Handler(SimpleHTTPRequestHandler):

            def log_message(self, format, *args):
                """Suppress default HTTP logging."""
                pass

            def handle(self):
                """Handle request, silently ignore client disconnections."""
                try:
                    super().handle()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self):
                try:
                    if self.path == '/' or self.path == '/gallery':
                        self._serve_gallery()
                    elif self.path.startswith('/photo/'):
                        self._serve_photo(self.path[7:])
                    elif self.path.startswith('/thumb/'):
                        self._serve_thumbnail(self.path[7:])
                    elif self.path.startswith('/view/'):
                        self._serve_photo_page(self.path[6:])
                    else:
                        self.send_error(404)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # Client disconnected, ignore

            def _serve_gallery(self):
                photos = server._list_photos()
                thumbnails = '\n'.join(
                    f'<a href="javascript:openViewer(\'/photo/{p}\')">'
                    f'<img src="/thumb/{p}" loading="lazy" alt="{p}"></a>'
                    for p in photos
                )
                photo_list = ', '.join(f"'/photo/{p}'" for p in photos)
                html = GALLERY_HTML.format(
                    title=server.title,
                    count=len(photos),
                    thumbnails=thumbnails,
                    photo_list=photo_list
                )
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))

            def _serve_photo_page(self, filename):
                filepath = osp.join(server.photo_dir, filename)
                if not osp.isfile(filepath):
                    self.send_error(404)
                    return
                html = PHOTO_HTML.format(filename=filename)
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))

            def _serve_photo(self, filename):
                filepath = osp.join(server.photo_dir, filename)
                if not osp.isfile(filepath):
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(osp.getsize(filepath)))
                self.end_headers()
                with open(filepath, 'rb') as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        self.wfile.write(chunk)

            def _serve_thumbnail(self, filename):
                thumb_path = server._get_thumbnail(filename)
                if not thumb_path:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(osp.getsize(thumb_path)))
                self.end_headers()
                with open(thumb_path, 'rb') as f:
                    self.wfile.write(f.read())

        return Handler

    def get_photo_url(self, filename):
        """Return the URL to view a specific photo."""
        return f"http://{{ip}}:{self.port}/view/{filename}"

    def get_gallery_url(self):
        """Return the URL to the gallery."""
        return f"http://{{ip}}:{self.port}/"

    def start(self):
        """Start the web server in a background thread."""

        class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
            daemon_threads = True

        handler = self._create_handler()
        self._server = ThreadedHTTPServer(('0.0.0.0', self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        LOGGER.info("Share server started on port %s", self.port)

    def stop(self):
        """Stop the web server."""
        if self._server:
            self._server.shutdown()
            LOGGER.info("Share server stopped")

    def generate_thumbnail(self, filename):
        """Pre-generate thumbnail for a photo (call after saving)."""
        self._get_thumbnail(filename)
