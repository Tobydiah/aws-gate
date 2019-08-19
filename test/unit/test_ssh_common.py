import unittest
from unittest.mock import patch, mock_open, MagicMock, call

from hypothesis import given, example
from hypothesis.strategies import text, integers, sampled_from

from aws_gate.ssh_common import GateKey, SUPPORTED_KEY_TYPES, KEY_MIN_SIZE
from aws_gate.config import DEFAULT_GATE_KEY_PATH


class TestSSHCommon(unittest.TestCase):
    @given(sampled_from(SUPPORTED_KEY_TYPES), integers(min_value=KEY_MIN_SIZE))
    def test_initialize_key(self, key_type, key_size):
        key = GateKey(key_type=key_type)

        self.assertTrue(key.key_path, DEFAULT_GATE_KEY_PATH)
        self.assertTrue(key.key_type, key_type)
        self.assertTrue(key.key_size, key_size)

    @given(sampled_from(SUPPORTED_KEY_TYPES))
    def test_ssh_public_key(self, key_type):
        key = GateKey(key_type=key_type)
        key.generate()

        if key_type == 'rsa':
            key_start_str = 'ssh-rsa'
        else:
            key_start_str = 'ssh-ed25519'

        self.assertTrue(key.public_key.decode().startswith(key_start_str))

    @given(text())
    def test_initialize_key_unsupported_key_type(self, key_type):
        with self.assertRaises(ValueError):
            GateKey(key_type=key_type)

    @given(integers(max_value=KEY_MIN_SIZE))
    @example(0)
    @example(-1024)
    def test_initialize_key_unsupported_key_size(self, key_size):
        with self.assertRaises(ValueError):
            GateKey(key_size=key_size)

    def test_initialize_key_invalid_key_path(self):
        with self.assertRaises(ValueError):
            GateKey(key_path='')

    @given(sampled_from(SUPPORTED_KEY_TYPES))
    def test_initialize_key_as_context_manager(self, key_type):
        with patch('builtins.open', new_callable=mock_open()) as open_mock, \
                patch('aws_gate.ssh_common.os.remove'):
            with GateKey(key_type=key_type):
                self.assertTrue(open_mock.called)
                open_mock.assert_called_with(DEFAULT_GATE_KEY_PATH, 'wb')

    def test_delete_key(self):
        with patch('builtins.open', new_callable=mock_open()), \
                patch('aws_gate.ssh_common.os', new_callable=MagicMock()) as m:
            key = GateKey()
            key.generate()
            key.write_to_file()
            key.delete()

            self.assertTrue(m.remove.called)
            self.assertEqual(m.remove.call_args, call(DEFAULT_GATE_KEY_PATH))
