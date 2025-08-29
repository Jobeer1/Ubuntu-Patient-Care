# Cloud storage plugins for Orthanc
# Copyright (C) 2020-2023 Osimis S.A., Belgium
# Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
# Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


if (STATIC_BUILD OR NOT USE_SYSTEM_CRYPTOPP)
  # The .tar.gz package was created by "./CryptoPPPackage.sh"
  SET(CRYPTOPP_SOURCES_DIR ${CMAKE_BINARY_DIR}/cryptopp-840)
  SET(CRYPTOPP_URL "https://orthanc.uclouvain.be/downloads/third-party-downloads/cryptopp-840.tar.gz")
  SET(CRYPTOPP_MD5 "d42363e8a12c06a000720335a4da70d3")

  DownloadPackage(${CRYPTOPP_MD5} ${CRYPTOPP_URL} "${CRYPTOPP_SOURCES_DIR}")

  include_directories(
    ${CRYPTOPP_SOURCES_DIR}
    )

  # TODO - Consider adding SIMD support
  add_definitions(
    -DCRYPTOPP_DISABLE_ASM
    )

  set(CRYPTOPP_SOURCES
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/aria_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/bench1.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/bench2.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/bench3.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/blake2b_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/blake2s_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/chacha_avx.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/chacha_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/cham_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/crc_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/datatest.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/dlltest.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/fipsalgt.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/fipstest.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/gcm_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/gf2n_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/keccak_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/lea_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/neon_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/ppc_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/regtest1.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/regtest2.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/regtest3.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/regtest4.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/rijndael_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/sha_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/shacal2_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/simon128_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/sm4_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/speck128_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/sse_simd.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/test.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/validat0.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/validat1.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/validat10.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/validat2.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/validat3.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/validat4.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/validat5.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/validat6.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/validat7.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/validat8.cpp
    # ${CRYPTOPP_SOURCES_DIR}/cryptopp/validat9.cpp

    ${CRYPTOPP_SOURCES_DIR}/cryptopp/3way.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/adler32.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/algebra.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/algparam.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/allocate.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/arc4.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/aria.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/ariatab.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/asn.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/authenc.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/base32.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/base64.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/basecode.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/bfinit.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/blake2.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/blowfish.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/blumshub.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/camellia.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/cast.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/casts.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/cbcmac.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/ccm.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/chacha.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/chachapoly.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/cham.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/channels.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/cmac.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/cpu.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/crc.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/cryptlib.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/darn.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/default.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/des.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/dessp.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/dh.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/dh2.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/dll.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/donna_32.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/donna_64.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/donna_sse.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/dsa.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/eax.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/ec2n.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/eccrypto.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/ecp.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/elgamal.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/emsa2.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/eprecomp.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/esign.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/files.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/filters.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/fips140.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/gcm.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/gf256.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/gf2_32.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/gf2n.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/gfpcrypt.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/gost.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/gzip.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/hc128.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/hc256.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/hex.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/hight.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/hmac.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/hrtimer.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/ida.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/idea.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/integer.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/iterhash.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/kalyna.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/kalynatab.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/keccak.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/keccak_core.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/lea.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/luc.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/mars.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/marss.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/md2.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/md4.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/md5.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/misc.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/modes.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/mqueue.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/mqv.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/nbtheory.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/oaep.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/osrng.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/padlkrng.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/panama.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/pch.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/pkcspad.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/poly1305.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/polynomi.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/ppc_power7.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/ppc_power8.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/ppc_power9.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/pssr.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/pubkey.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/queue.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/rabbit.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/rabin.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/randpool.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/rc2.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/rc5.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/rc6.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/rdrand.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/rdtables.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/rijndael.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/ripemd.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/rng.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/rsa.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/rw.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/safer.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/salsa.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/scrypt.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/seal.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/seed.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/serpent.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/sha.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/sha3.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/shacal2.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/shake.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/shark.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/sharkbox.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/simeck.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/simon.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/simple.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/skipjack.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/sm3.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/sm4.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/sosemanuk.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/speck.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/square.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/squaretb.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/strciphr.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/tea.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/tftables.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/threefish.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/tiger.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/tigertab.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/ttmac.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/tweetnacl.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/twofish.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/vmac.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/wake.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/whrlpool.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/xed25519.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/xtr.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/xtrcrypt.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/xts.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/zdeflate.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/zinflate.cpp
    ${CRYPTOPP_SOURCES_DIR}/cryptopp/zlib.cpp
    )

  source_group(ThirdParty\\cryptopp REGULAR_EXPRESSION ${CRYPTOPP_SOURCES_DIR}/.*)

else()
  ##
  ## Inclusion of system-wide crypto++
  ##
  check_include_file_cxx(cryptopp/cryptlib.h HAVE_CRYPTOPP_H)
  if (NOT HAVE_CRYPTOPP_H)
    message(FATAL_ERROR "Please install the libcrypto++-dev package")
  endif()

  include(CheckCXXSymbolExists)
  set(CMAKE_REQUIRED_LIBRARIES cryptopp)
  check_cxx_symbol_exists("CryptoPP::SHA1::InitState" cryptopp/sha.h HAVE_LIBCRYPTOPP)
  if (NOT HAVE_LIBCRYPTOPP)
    message(FATAL_ERROR "Unable to find the cryptopp library")
  endif()

  set(CRYPTOPP_LIBRARIES cryptopp)
endif()
