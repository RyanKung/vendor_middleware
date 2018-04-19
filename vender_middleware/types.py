from typing import NamedTuple
from typing import NewType

URL = NewType('str')

Vendor = NamedTuple('Vendor', [
    ('name', str),
    ('secret', str),
    ('aes_key', str)
])

VendorRouter = NamedTuple('VendorRouter', [
    ('callback', URL),
    ('qr_code', URL),
    ('qr_code_status', URL)
])
