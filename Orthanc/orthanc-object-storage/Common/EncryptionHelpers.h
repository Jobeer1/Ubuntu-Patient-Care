/**
 * Cloud storage plugins for Orthanc
 * Copyright (C) 2020-2023 Osimis S.A., Belgium
 * Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Affero General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


#pragma once

#include <memory.h>
#include <cryptopp/secblock.h>
#include <cryptopp/osrng.h>
#include <boost/thread/mutex.hpp>
#include <MultiThreading/Semaphore.h>

class EncryptionException : public std::runtime_error
{
public:
  explicit EncryptionException(const std::string& what)
    : std::runtime_error(what)
  {
  }
};

class EncryptionHelpers
{
public:
  static const size_t HEADER_VERSION_SIZE = 2;
  static const size_t MASTER_KEY_ID_SIZE = 4;
  static const size_t AES_KEY_SIZE = 32;                  // length of AES keys (in bytes)
  static const size_t IV_SIZE = 32;                       // length of IVs (in bytes)
  static const size_t INTEGRITY_CHECK_TAG_SIZE = 16;      // length of the TAG that is used to check the integrity of data (in bytes)

  static const size_t OVERHEAD_SIZE = HEADER_VERSION_SIZE + MASTER_KEY_ID_SIZE + AES_KEY_SIZE + IV_SIZE + INTEGRITY_CHECK_TAG_SIZE;


  static const std::string HEADER_VERSION;

private:
  Orthanc::Semaphore                concurrentInputSizeSemaphore_;
  size_t                            maxConcurrentInputSize_;

  CryptoPP::AutoSeededRandomPool    randomGenerator_;

  CryptoPP::SecByteBlock            encryptionMasterKey_;  // at a given time, there's only one master key that is used for encryption
  std::string                       encryptionMasterKeyId_;

  std::map<std::string, CryptoPP::SecByteBlock> previousMasterKeys_; // for decryption, we might use older master keys too

public:

  // since the memory used during encryption/decryption can grow up to a bit more than 2 times the input,
  // we want to limit the number of threads doing concurrent processing according to the available memory
  // instead of the number of concurrent threads
  EncryptionHelpers(size_t maxConcurrentInputSize = 1024*1024*1024);

  void SetCurrentMasterKey(uint32_t id, const std::string& path);

  void SetCurrentMasterKey(uint32_t id, const CryptoPP::SecByteBlock& key);

  void AddPreviousMasterKey(uint32_t id, const std::string& path);

  void AddPreviousMasterKey(uint32_t id, const CryptoPP::SecByteBlock& key);

  // input: plain text data
  // output: prefix/encrypted data/integrity check tag
  void Encrypt(std::string& output, const std::string& input);
  void Encrypt(std::string& output, const char* data, size_t size);

  // input: prefix/encrypted data/integrity check tag
  // output: plain text data
  void Decrypt(std::string& output, const std::string& input);
  void Decrypt(char* output, const char* data, size_t size);

  static void GenerateKey(CryptoPP::SecByteBlock& key);

private:

  void EncryptInternal(std::string& output, const char* data, size_t size, const CryptoPP::SecByteBlock& masterKey);

  void DecryptInternal(char* output, const char* data, size_t size, const CryptoPP::SecByteBlock& masterKey);

  void EncryptPrefixSecBlock(std::string& output, const CryptoPP::SecByteBlock& input, const CryptoPP::SecByteBlock& masterKey);

  void DecryptPrefixSecBlock(CryptoPP::SecByteBlock& output, const std::string& input, const CryptoPP::SecByteBlock& masterKey);

  std::string GetMasterKeyIdentifier(const CryptoPP::SecByteBlock& masterKey);

  const CryptoPP::SecByteBlock& GetMasterKey(const std::string& keyId);

public:

  static std::string ToHexString(const void* block, size_t size);
  static std::string ToHexString(const std::string& block);
  static std::string ToHexString(const CryptoPP::SecByteBlock& block);
  static std::string ToString(const CryptoPP::SecByteBlock& block);
  static std::string ToString(uint32_t value);

  static void ReadKey(CryptoPP::SecByteBlock& key, const std::string& path);
  //static void EncryptionHelpers::Encrypt(std::string& output, const std::string& input, const std::string& key, const std::string& iv);
};

