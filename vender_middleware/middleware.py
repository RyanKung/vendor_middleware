from redis import Redis
import simplejson as json
from poim import Client
from poim.event import make, LoginEvent
from poim.storage.redis import RedisStore
from poim.utils.login import mk_qr_code_cls


from .types import VendorMeta, VendorRouter
from .utils import mk_qrcode

from werkzeug.http import http_date
from werkzeug.wsgi import wrap_file


redis_client = Redis()
store = RedisStore(redis_client)
QRCode = mk_qr_code_cls(storage_backend=store)
session_id = "1"


class VendorMiddleware:
    def __init__(self, wsgi, vendor: VendorMeta, router: VendorRouter):
        self.wsgi = wsgi
        self.vendor = vendor
        self.router = {
            router.callback: self.callback,
            router.qr_code: self.qr_code,
            router.qr_code_status: self.qr_code_status
        }
        self.bixin_client = Client(
            vendor_name=vendor.name,
            secret=vendor.secret,
            access_token=''
        )

    def callback(self, environ, start_response):
        if not environ['REQUEST_METHOD'].upper() == 'POST':
            start_response('405', 'Method not allowed')
            return

        headers = [
            ('Date', http_date()),
        ]
        body_size = int(environ.get('CONTENT_LENGTH', 0))
        body = environ['wsgi.input'].read(body_size)
        data = json.loads(body)

        event = make(data, aes_key=self.vendor.aes_key)
        if not isinstance(event, LoginEvent):
            return {}
        code = QRCode.get_unexpired(event.qr_code_id)
        if code is None:
            return {}
        code.mark_as_bind()
        start_response(headers)
        return

    def qr_code(self, environ, start_response):
        qrcode = QRCode.get_or_create(
            poim_client=self.poim_client,
            session_id=session_id,
        )
        qrcode.save()
        fp = mk_qrcode(qrcode.url)
        headers = [
            ('Date', http_date()),
            ('MimeType', 'image/png')
        ]
        start_response('200 OK', headers)
        return wrap_file(environ, fp)

    def qr_code_status(self, environ, start_response):
        code = QRCode.get_unexpired(session_id)
        if code.is_bind:
            data = {
                "session_id": session_id,
                'status': "already bind",
            }
        else:
            data = {
                "session_id": session_id,
                'status': 'not bind yet',
            }
        headers = [
            ('Date', http_date()),
        ]
        start_response(headers)
        return [json.dumps(data)]

    def __call__(self, environ, start_response):
        return self.wsgi(environ, start_response).get(
            environ['PATH_INFO'], self.wsgi(environ, start_response))
