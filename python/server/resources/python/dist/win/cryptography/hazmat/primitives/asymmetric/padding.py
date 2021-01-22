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
from cryptography.hazmat.primitives import interfaces


@utils.register_interface(interfaces.AsymmetricPadding)
class PKCS1v15(object):
    name = "EMSA-PKCS1-v1_5"


@utils.register_interface(interfaces.AsymmetricPadding)
class PSS(object):
    MAX_LENGTH = object()
    name = "EMSA-PSS"

    def __init__(self, mgf, salt_length):
        self._mgf = mgf

        if (not isinstance(salt_length, six.integer_types) and
                salt_length is not self.MAX_LENGTH):
            raise TypeError("salt_length must be an integer.")

        if salt_length is not self.MAX_LENGTH and salt_length < 0:
            raise ValueError("salt_length must be zero or greater.")

        self._salt_length = salt_length


@utils.register_interface(interfaces.AsymmetricPadding)
class OAEP(object):
    name = "EME-OAEP"

    def __init__(self, mgf, algorithm, label):
        if not isinstance(algorithm, interfaces.HashAlgorithm):
            raise TypeError("Expected instance of interfaces.HashAlgorithm.")

        self._mgf = mgf
        self._algorithm = algorithm
        self._label = label


class MGF1(object):
    MAX_LENGTH = object()

    def __init__(self, algorithm):
        if not isinstance(algorithm, interfaces.HashAlgorithm):
            raise TypeError("Expected instance of interfaces.HashAlgorithm.")

        self._algorithm = algorithm
