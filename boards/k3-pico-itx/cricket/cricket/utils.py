from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer, QObject
import os
import qrcode

def get_product_name():
    path = '/proc/device-tree/model'
    if os.path.exists(path):
        with open(path, 'r') as f:
            model = f.readline().strip(b'\0x00'.decode())
            return model.replace('spacemit', '').replace('board', '').strip()

def create_qrcode(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=0,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    # Convert PIL Image to QImage
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimage = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimage)

