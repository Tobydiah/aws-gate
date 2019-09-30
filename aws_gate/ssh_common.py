import logging
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519

from aws_gate.constants import DEFAULT_GATE_KEY_PATH

logger = logging.getLogger(__name__)

SUPPORTED_KEY_TYPES = ['rsa', 'ed25519']
KEY_MIN_SIZE = 2048


class SshKey:
    def __init__(self, key_path=DEFAULT_GATE_KEY_PATH, key_type='rsa', key_size=KEY_MIN_SIZE):
        self._key_path = None
        self._key_type = None
        self._key_size = None
        self._private_key = None
        self._public_key = None

        self.key_path = key_path
        self.key_type = key_type
        self.key_size = key_size

    def __enter__(self):
        self.generate()
        self.write_to_file()
        return self

    def __exit__(self, *args):
        self.delete()

    def _generate_key(self):
        self._private_key = None

        if self._key_type == 'rsa':
            self._private_key = rsa.generate_private_key(public_exponent=65537,
                                                         key_size=self._key_size,
                                                         backend=default_backend())
        elif self._key_type == 'ed25519':
            self._private_key = ed25519.Ed25519PrivateKey.generate()

        self._public_key = self._private_key.public_key()

    def generate(self):
        self._generate_key()

    def write_to_file(self):
        with open(self._key_path, 'wb') as f:
            f.write(self.private_key)

    def delete(self):
        os.remove(self._key_path)

    @property
    def public_key(self):
        return self._public_key.public_bytes(encoding=serialization.Encoding.OpenSSH,
                                             format=serialization.PublicFormat.OpenSSH)

    @property
    def private_key(self):
        return self._private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                               format=serialization.PrivateFormat.PKCS8,
                                               encryption_algorithm=serialization.NoEncryption())

    @property
    def key_type(self):
        return self._key_type

    @key_type.setter
    def key_type(self, value):
        if not value or value not in SUPPORTED_KEY_TYPES:
            raise ValueError('Unsupported or invalid key type: {}'.format(value))

        self._key_type = value

    @property
    def key_path(self):
        return self._key_path

    @key_path.setter
    def key_path(self, value):
        if not value:
            raise ValueError('Invalid key path: {}'.format(value))
        self._key_path = value

    @property
    def key_size(self):
        return self._key_size

    @key_size.setter
    def key_size(self, value):
        if value < KEY_MIN_SIZE:
            raise ValueError('Invalid key size: {}'.format(value))

        self._key_size = value
