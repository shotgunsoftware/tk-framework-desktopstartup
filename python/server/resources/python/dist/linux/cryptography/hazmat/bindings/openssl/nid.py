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

INCLUDES = ""

TYPES = """
static const int Cryptography_HAS_ECDSA_SHA2_NIDS;

static const int NID_undef;
static const int NID_dsa;
static const int NID_dsaWithSHA;
static const int NID_dsaWithSHA1;
static const int NID_md2;
static const int NID_md4;
static const int NID_md5;
static const int NID_mdc2;
static const int NID_ripemd160;
static const int NID_sha;
static const int NID_sha1;
static const int NID_sha256;
static const int NID_sha384;
static const int NID_sha512;
static const int NID_sha224;
static const int NID_sha;
static const int NID_ecdsa_with_SHA1;
static const int NID_ecdsa_with_SHA224;
static const int NID_ecdsa_with_SHA256;
static const int NID_ecdsa_with_SHA384;
static const int NID_ecdsa_with_SHA512;
static const int NID_crl_reason;
static const int NID_pbe_WithSHA1And3_Key_TripleDES_CBC;
static const int NID_subject_alt_name;
static const int NID_issuer_alt_name;
static const int NID_X9_62_c2pnb163v1;
static const int NID_X9_62_c2pnb163v2;
static const int NID_X9_62_c2pnb163v3;
static const int NID_X9_62_c2pnb176v1;
static const int NID_X9_62_c2tnb191v1;
static const int NID_X9_62_c2tnb191v2;
static const int NID_X9_62_c2tnb191v3;
static const int NID_X9_62_c2onb191v4;
static const int NID_X9_62_c2onb191v5;
static const int NID_X9_62_c2pnb208w1;
static const int NID_X9_62_c2tnb239v1;
static const int NID_X9_62_c2tnb239v2;
static const int NID_X9_62_c2tnb239v3;
static const int NID_X9_62_c2onb239v4;
static const int NID_X9_62_c2onb239v5;
static const int NID_X9_62_c2pnb272w1;
static const int NID_X9_62_c2pnb304w1;
static const int NID_X9_62_c2tnb359v1;
static const int NID_X9_62_c2pnb368w1;
static const int NID_X9_62_c2tnb431r1;
static const int NID_X9_62_prime192v1;
static const int NID_X9_62_prime192v2;
static const int NID_X9_62_prime192v3;
static const int NID_X9_62_prime239v1;
static const int NID_X9_62_prime239v2;
static const int NID_X9_62_prime239v3;
static const int NID_X9_62_prime256v1;
static const int NID_secp112r1;
static const int NID_secp112r2;
static const int NID_secp128r1;
static const int NID_secp128r2;
static const int NID_secp160k1;
static const int NID_secp160r1;
static const int NID_secp160r2;
static const int NID_sect163k1;
static const int NID_sect163r1;
static const int NID_sect163r2;
static const int NID_secp192k1;
static const int NID_secp224k1;
static const int NID_secp224r1;
static const int NID_secp256k1;
static const int NID_secp384r1;
static const int NID_secp521r1;
static const int NID_sect113r1;
static const int NID_sect113r2;
static const int NID_sect131r1;
static const int NID_sect131r2;
static const int NID_sect193r1;
static const int NID_sect193r2;
static const int NID_sect233k1;
static const int NID_sect233r1;
static const int NID_sect239k1;
static const int NID_sect283k1;
static const int NID_sect283r1;
static const int NID_sect409k1;
static const int NID_sect409r1;
static const int NID_sect571k1;
static const int NID_sect571r1;
static const int NID_wap_wsg_idm_ecid_wtls1;
static const int NID_wap_wsg_idm_ecid_wtls3;
static const int NID_wap_wsg_idm_ecid_wtls4;
static const int NID_wap_wsg_idm_ecid_wtls5;
static const int NID_wap_wsg_idm_ecid_wtls6;
static const int NID_wap_wsg_idm_ecid_wtls7;
static const int NID_wap_wsg_idm_ecid_wtls8;
static const int NID_wap_wsg_idm_ecid_wtls9;
static const int NID_wap_wsg_idm_ecid_wtls10;
static const int NID_wap_wsg_idm_ecid_wtls11;
static const int NID_wap_wsg_idm_ecid_wtls12;
static const int NID_ipsec3;
static const int NID_ipsec4;
static const char *const SN_X9_62_c2pnb163v1;
static const char *const SN_X9_62_c2pnb163v2;
static const char *const SN_X9_62_c2pnb163v3;
static const char *const SN_X9_62_c2pnb176v1;
static const char *const SN_X9_62_c2tnb191v1;
static const char *const SN_X9_62_c2tnb191v2;
static const char *const SN_X9_62_c2tnb191v3;
static const char *const SN_X9_62_c2onb191v4;
static const char *const SN_X9_62_c2onb191v5;
static const char *const SN_X9_62_c2pnb208w1;
static const char *const SN_X9_62_c2tnb239v1;
static const char *const SN_X9_62_c2tnb239v2;
static const char *const SN_X9_62_c2tnb239v3;
static const char *const SN_X9_62_c2onb239v4;
static const char *const SN_X9_62_c2onb239v5;
static const char *const SN_X9_62_c2pnb272w1;
static const char *const SN_X9_62_c2pnb304w1;
static const char *const SN_X9_62_c2tnb359v1;
static const char *const SN_X9_62_c2pnb368w1;
static const char *const SN_X9_62_c2tnb431r1;
static const char *const SN_X9_62_prime192v1;
static const char *const SN_X9_62_prime192v2;
static const char *const SN_X9_62_prime192v3;
static const char *const SN_X9_62_prime239v1;
static const char *const SN_X9_62_prime239v2;
static const char *const SN_X9_62_prime239v3;
static const char *const SN_X9_62_prime256v1;
static const char *const SN_secp112r1;
static const char *const SN_secp112r2;
static const char *const SN_secp128r1;
static const char *const SN_secp128r2;
static const char *const SN_secp160k1;
static const char *const SN_secp160r1;
static const char *const SN_secp160r2;
static const char *const SN_sect163k1;
static const char *const SN_sect163r1;
static const char *const SN_sect163r2;
static const char *const SN_secp192k1;
static const char *const SN_secp224k1;
static const char *const SN_secp224r1;
static const char *const SN_secp256k1;
static const char *const SN_secp384r1;
static const char *const SN_secp521r1;
static const char *const SN_sect113r1;
static const char *const SN_sect113r2;
static const char *const SN_sect131r1;
static const char *const SN_sect131r2;
static const char *const SN_sect193r1;
static const char *const SN_sect193r2;
static const char *const SN_sect233k1;
static const char *const SN_sect233r1;
static const char *const SN_sect239k1;
static const char *const SN_sect283k1;
static const char *const SN_sect283r1;
static const char *const SN_sect409k1;
static const char *const SN_sect409r1;
static const char *const SN_sect571k1;
static const char *const SN_sect571r1;
static const char *const SN_wap_wsg_idm_ecid_wtls1;
static const char *const SN_wap_wsg_idm_ecid_wtls3;
static const char *const SN_wap_wsg_idm_ecid_wtls4;
static const char *const SN_wap_wsg_idm_ecid_wtls5;
static const char *const SN_wap_wsg_idm_ecid_wtls6;
static const char *const SN_wap_wsg_idm_ecid_wtls7;
static const char *const SN_wap_wsg_idm_ecid_wtls8;
static const char *const SN_wap_wsg_idm_ecid_wtls9;
static const char *const SN_wap_wsg_idm_ecid_wtls10;
static const char *const SN_wap_wsg_idm_ecid_wtls11;
static const char *const SN_wap_wsg_idm_ecid_wtls12;
static const char *const SN_ipsec3;
static const char *const SN_ipsec4;
"""

FUNCTIONS = """
"""

MACROS = """
"""

CUSTOMIZATIONS = """
/* OpenSSL 0.9.8g+ */
#if OPENSSL_VERSION_NUMBER >= 0x0090807fL
static const long Cryptography_HAS_ECDSA_SHA2_NIDS = 1;
#else
static const long Cryptography_HAS_ECDSA_SHA2_NIDS = 0;
static const int NID_ecdsa_with_SHA224 = 0;
static const int NID_ecdsa_with_SHA256 = 0;
static const int NID_ecdsa_with_SHA384 = 0;
static const int NID_ecdsa_with_SHA512 = 0;
#endif
"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_ECDSA_SHA2_NIDS": [
        "NID_ecdsa_with_SHA224",
        "NID_ecdsa_with_SHA256",
        "NID_ecdsa_with_SHA384",
        "NID_ecdsa_with_SHA512",
    ],
}
