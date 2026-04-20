# -*- coding: utf-8 -*-

"""Pibooth plugin: share photos via web server + QR code on screen."""

import os.path as osp
import socket
import pygame
import pibooth
from pibooth.utils import LOGGER

try:
    import qrcode
except ImportError:
    qrcode = None

__name__ = 'pibooth-share'
__version__ = '1.0.0'

# Module-level state
_server = None
_qr_surface = None
_photo_qr_surface = None
_ip = None


def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_qr_surface(url, size=150):
    """Generate a pygame surface with a QR code."""
    if not qrcode:
        LOGGER.warning("qrcode module not installed, QR code disabled")
        return None

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((size, size))

    raw = img.convert('RGB').tobytes()
    surface = pygame.image.fromstring(raw, img.size, 'RGB')
    return surface


@pibooth.hookimpl
def pibooth_configure(cfg):
    """Add plugin configuration options."""
    cfg.add_option('SHARE', 'share_enabled', True,
                   "Enable photo sharing via web server",
                   "Share enabled", ['True', 'False'])
    cfg.add_option('SHARE', 'share_port', 8080,
                   "Web server port for photo sharing")
    cfg.add_option('SHARE', 'share_title', 'Photobooth',
                   "Title displayed on the gallery page")
    cfg.add_option('SHARE', 'share_qrcode_size', 150,
                   "QR code size in pixels on screen")
    cfg.add_option('SHARE', 'share_show_qrcode', True,
                   "Show QR code of last photo on finish/wait screen",
                   "Show QR code", ['True', 'False'])


@pibooth.hookimpl
def pibooth_startup(cfg, app):
    """Start the web server."""
    global _server, _ip, _qr_surface

    if not cfg.getboolean('SHARE', 'share_enabled'):
        return

    from pibooth_share.server import ShareServer

    photo_dir = cfg.gettuple('GENERAL', 'directory', 'path')[0]
    port = cfg.getint('SHARE', 'share_port')
    title = cfg.get('SHARE', 'share_title')

    _server = ShareServer(photo_dir, port, title)
    _server.start()

    _ip = get_local_ip()
    gallery_url = f"http://{_ip}:{port}/"
    LOGGER.info("Gallery available at %s", gallery_url)

    qr_size = cfg.getint('SHARE', 'share_qrcode_size')
    _qr_surface = generate_qr_surface(gallery_url, qr_size)


@pibooth.hookimpl
def pibooth_cleanup(app):
    """Stop the web server."""
    global _server
    if _server:
        _server.stop()
        _server = None


@pibooth.hookimpl
def state_processing_exit(cfg, app):
    """Generate thumbnail and QR code for the last photo."""
    global _photo_qr_surface, _server, _ip

    if not _server or not app.previous_picture_file:
        return

    filename = osp.basename(app.previous_picture_file)
    _server.generate_thumbnail(filename)

    if cfg.getboolean('SHARE', 'share_show_qrcode'):
        port = cfg.getint('SHARE', 'share_port')
        photo_url = f"http://{_ip}:{port}/view/{filename}"
        qr_size = cfg.getint('SHARE', 'share_qrcode_size')
        _photo_qr_surface = generate_qr_surface(photo_url, qr_size)


@pibooth.hookimpl
def state_finish_enter(cfg, app, win):
    """Display QR code on finish screen."""
    if cfg.getboolean('SHARE', 'share_show_qrcode'):
        _draw_qr(win)


@pibooth.hookimpl
def state_wait_enter(cfg, app, win):
    """Display QR code on wait screen."""
    if cfg.getboolean('SHARE', 'share_show_qrcode') and app.previous_picture_file:
        _draw_qr(win)


def _draw_qr(win):
    """Draw the photo QR code on screen."""
    surface = _photo_qr_surface or _qr_surface
    if not surface:
        return

    screen = pygame.display.get_surface()
    if screen:
        margin = 10
        x = screen.get_width() - surface.get_width() - margin
        y = screen.get_height() - surface.get_height() - margin
        screen.blit(surface, (x, y))
