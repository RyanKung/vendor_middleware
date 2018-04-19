from redis import Redis
import simplejson as json
from poim import Client
from poim.event import make, LoginEvent
from poim.storage.redis import RedisStore
from poim.utils.login import mk_qr_code_cls


from .types import VendorMeta, VendorRouter
from .utils import mk_qrcode

from werkzeug.wsgi import wrap_file
from werkzeug.wrappers import Request, Response


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

    @Request.application
    def callback(self, request):
        data = json.loads(request.data)

        event = make(data, aes_key=self.vendor.aes_key)
        assert isinstance(event, LoginEvent)
        code = QRCode.get_unexpired(event.qr_code_id)
        assert code
        code.mark_as_bind()
        return Response('')

    @Request.application
    def qr_code(self, request):
        qrcode = QRCode.get_or_create(
            poim_client=self.poim_client,
            session_id=session_id,
        )
        qrcode.save()
        fp = mk_qrcode(qrcode.url)
        return Response(wrap_file(request.environ, fp))

    @Request.application
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
        return Response(json.dumps(data))

    def __call__(self, environ, start_response):
        return self.wsgi(environ, start_response).get(
            environ['PATH_INFO'], self.wsgi(environ, start_response))
