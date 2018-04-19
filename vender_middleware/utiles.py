from io import BytesIO
import qrcode


def mk_qrcode(url: str):
    with BytesIO as f:
        qrcode.make(url).save(f)
        return f
