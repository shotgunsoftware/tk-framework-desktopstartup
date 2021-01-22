# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import six

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, InvalidKey, UnsupportedAlgorithm, _Reasons
)
from cryptography.hazmat.backends.interfaces import HMACBackend
from cryptography.hazmat.primitives import constant_time, hmac, interfaces


@utils.register_interface(interfaces.KeyDerivationFunction)
class HKDF(object):
    def __init__(self, algorithm, length, salt, info, backend):
        if not isinstance(backend, HMACBackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement HMACBackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        self._algorithm = algorithm

        if not isinstance(salt, bytes) and salt is not None:
            raise TypeError("salt must be bytes.")

        if salt is None:
            salt = b"\x00" * (self._algorithm.digest_size // 8)

        self._salt = salt

        self._backend = backend

        self._hkdf_expand = HKDFExpand(self._algorithm, length, info, backend)

    def _extract(self, key_material):
        h = hmac.HMAC(self._salt, self._algorithm, backend=self._backend)
        h.update(key_material)
        return h.finalize()

    def derive(self, key_material):
        if not isinstance(key_material, bytes):
            raise TypeError("key_material must be bytes.")

        return self._hkdf_expand.derive(self._extract(key_material))

    def verify(self, key_material, expected_key):
        if not constant_time.bytes_eq(self.derive(key_material), expected_key):
            raise InvalidKey


@utils.register_interface(interfaces.KeyDerivationFunction)
class HKDFExpand(object):
    def __init__(self, algorithm, length, info, backend):
        if not isinstance(backend, HMACBackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement HMACBackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        self._algorithm = algorithm

        self._backend = backend

        max_length = 255 * (algorithm.digest_size // 8)

        if length > max_length:
            raise ValueError(
                "Can not derive keys larger than {0} octets.".format(
                    max_length
                ))

        self._length = length

        if not isinstance(info, bytes) and info is not None:
            raise TypeError("info must be bytes.")

        if info is None:
            info = b""

        self._info = info

        self._used = False

    def _expand(self, key_material):
        output = [b""]
        counter = 1

        while (self._algorithm.digest_size // 8) * len(output) < self._length:
            h = hmac.HMAC(key_material, self._algorithm, backend=self._backend)
            h.update(output[-1])
            h.update(self._info)
            h.update(six.int2byte(counter))
            output.append(h.finalize())
            counter += 1

        return b"".join(output)[:self._length]

    def derive(self, key_material):
        if not isinstance(key_material, bytes):
            raise TypeError("key_material must be bytes.")

        if self._used:
            raise AlreadyFinalized

        self._used = True
        return self._expand(key_material)

    def verify(self, key_material, expected_key):
        if not constant_time.bytes_eq(self.derive(key_material), expected_key):
            raise InvalidKey
