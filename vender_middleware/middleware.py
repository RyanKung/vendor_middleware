from redis import Redis
import simplejson as json
from poim import Client
from poim.event import make, LoginEvent
from poim.storage.redis import RedisStore
from poim.utils.login import mk_qr_code_cls


from .types import VendorMeta, VendorRouter
from .utils import mk_qrcode

from werkzeug.wrappers import Request, Response, ResponseStream
from werkzeug.routing import Map, Rule


redis_client = Redis()
store = RedisStore(redis_client)
QRCode = mk_qr_code_cls(storage_backend=store)
session_id = "1"


class VendorMiddleware:
    def __init__(self, wsgi, vendor: VendorMeta, router: VendorRouter):
        self.wsgi = Request.application(wsgi)
        self.vendor = vendor
        self.adapter = Map([
            Rule(router.callback, endpoint='callback', methods=['POST']),
            Rule(router.qr_code, endpoint='qr_code', methods=['GET']),
            Rule(router.qr_code_status, endpoint='qr_code_status', methods=['GET'])
        ])
        self.router = router
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
        return ResponseStream(fp)

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

    @Request.application
    def __call__(self, request):
        return self.adapter.dispatch(
            lambda e, v: self.router.get(e, self.wsgi)(request, v),
            catch_http_exception=True
        )
