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


from cryptography import utils
from cryptography.exceptions import UnsupportedAlgorithm, _Reasons
from cryptography.hazmat.primitives import interfaces


@utils.register_interface(interfaces.HashContext)
class _HashContext(object):
    def __init__(self, backend, algorithm, ctx=None):
        self.algorithm = algorithm

        self._backend = backend

        if ctx is None:
            ctx = self._backend._lib.EVP_MD_CTX_create()
            ctx = self._backend._ffi.gc(ctx,
                                        self._backend._lib.EVP_MD_CTX_destroy)
            evp_md = self._backend._lib.EVP_get_digestbyname(
                algorithm.name.encode("ascii"))
            if evp_md == self._backend._ffi.NULL:
                raise UnsupportedAlgorithm(
                    "{0} is not a supported hash on this backend.".format(
                        algorithm.name),
                    _Reasons.UNSUPPORTED_HASH
                )
            res = self._backend._lib.EVP_DigestInit_ex(ctx, evp_md,
                                                       self._backend._ffi.NULL)
            assert res != 0

        self._ctx = ctx

    def copy(self):
        copied_ctx = self._backend._lib.EVP_MD_CTX_create()
        copied_ctx = self._backend._ffi.gc(
            copied_ctx, self._backend._lib.EVP_MD_CTX_destroy
        )
        res = self._backend._lib.EVP_MD_CTX_copy_ex(copied_ctx, self._ctx)
        assert res != 0
        return _HashContext(self._backend, self.algorithm, ctx=copied_ctx)

    def update(self, data):
        res = self._backend._lib.EVP_DigestUpdate(self._ctx, data, len(data))
        assert res != 0

    def finalize(self):
        buf = self._backend._ffi.new("unsigned char[]",
                                     self._backend._lib.EVP_MAX_MD_SIZE)
        outlen = self._backend._ffi.new("unsigned int *")
        res = self._backend._lib.EVP_DigestFinal_ex(self._ctx, buf, outlen)
        assert res != 0
        assert outlen[0] == self.algorithm.digest_size
        res = self._backend._lib.EVP_MD_CTX_cleanup(self._ctx)
        assert res == 1
        return self._backend._ffi.buffer(buf)[:outlen[0]]
