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


#include "EncryptionHelpers.h"
#include <assert.h>

#include <boost/lexical_cast.hpp>
#include <iostream>

#include <cryptopp/cryptlib.h>
#include <cryptopp/modes.h>
#include <cryptopp/hex.h>
#include <cryptopp/base64.h>
#include <cryptopp/gcm.h>
#include <cryptopp/files.h>
#include <cryptopp/filters.h>

const std::string EncryptionHelpers::HEADER_VERSION = "A1";

using namespace  CryptoPP;

std::string EncryptionHelpers::ToHexString(const void* block, size_t size)
{
  std::string blockAsString = std::string(reinterpret_cast<const char*>(block), size);

  return ToHexString(blockAsString);
}

std::string EncryptionHelpers::ToHexString(const std::string& block)
{
  std::string hexString;
  StringSource ss(block, true,
                   new HexEncoder(
                     new StringSink(hexString)
                     ) // StreamTransformationFilter
                   ); // StringSource

  return hexString;
}

std::string EncryptionHelpers::ToHexString(const SecByteBlock& block)
{
  return ToHexString(ToString(block));
}

std::string EncryptionHelpers::ToString(const CryptoPP::SecByteBlock& block)
{
  return std::string(reinterpret_cast<const char*>(block.data()), block.size());
}

std::string EncryptionHelpers::ToString(uint32_t value)
{
  return std::string(reinterpret_cast<const char*>(&value), 4);
}

void EncryptionHelpers::ReadKey(CryptoPP::SecByteBlock& key, const std::string& path)
{
  try
  {
    FileSource fs(path.c_str(), true,
                  new Base64Decoder(
                    new ArraySink(key.begin(), key.size())
                    )
                  );

    // std::cout << "ReadKey " << ToHexString(key) << std::endl;
  }
  catch (CryptoPP::Exception& ex)
  {
    throw EncryptionException("unabled to read key from file '" + path + "': " + ex.what());
  }
}

void EncryptionHelpers::SetCurrentMasterKey(uint32_t id, const std::string& path)
{
  SecByteBlock key(AES_KEY_SIZE);

  ReadKey(key, path);
  SetCurrentMasterKey(id, key);
}

void EncryptionHelpers::AddPreviousMasterKey(uint32_t id, const std::string& path)
{
  SecByteBlock key(AES_KEY_SIZE);

  ReadKey(key, path);
  AddPreviousMasterKey(id, key);
}

EncryptionHelpers::EncryptionHelpers(size_t maxConcurrentInputSize)
  : concurrentInputSizeSemaphore_(maxConcurrentInputSize),
    maxConcurrentInputSize_(maxConcurrentInputSize)
{
}

void EncryptionHelpers::SetCurrentMasterKey(uint32_t id, const CryptoPP::SecByteBlock& key)
{
  encryptionMasterKey_ = key;
  encryptionMasterKeyId_ = ToString(id);
}

void EncryptionHelpers::AddPreviousMasterKey(uint32_t id, const CryptoPP::SecByteBlock& key)
{
  previousMasterKeys_[ToString(id)] = key;
}

const CryptoPP::SecByteBlock& EncryptionHelpers::GetMasterKey(const std::string& keyId)
{
  if (encryptionMasterKeyId_ == keyId)
  {
    return encryptionMasterKey_;
  }

  if (previousMasterKeys_.find(keyId) == previousMasterKeys_.end())
  {
    throw EncryptionException("The master key whose id is '" + ToHexString(keyId) + "' could not be found.  Unable to decrypt file");
  }

  return previousMasterKeys_.at(keyId);
}

void EncryptionHelpers::GenerateKey(CryptoPP::SecByteBlock& key)
{
  AutoSeededRandomPool prng;

  SecByteBlock tempKey(AES_KEY_SIZE);
  prng.GenerateBlock( tempKey, tempKey.size() );
  key = tempKey;
}

void EncryptionHelpers::Encrypt(std::string &output, const std::string &input)
{
  Encrypt(output, input.data(), input.size());
}

void EncryptionHelpers::Encrypt(std::string &output, const char* data, size_t size)
{
  if (size > maxConcurrentInputSize_)
  {
    throw EncryptionException("The file is too large to encrypt: " + boost::lexical_cast<std::string>(size) + " bytes.  Try increasing the MaxConcurrentInputSize");
  }

  Orthanc::Semaphore::Locker lock(concurrentInputSizeSemaphore_, size);

  EncryptInternal(output, data, size, encryptionMasterKey_);
}

void EncryptionHelpers::Decrypt(std::string &output, const std::string &input)
{
  output.resize(input.size() - OVERHEAD_SIZE);
  Decrypt(const_cast<char*>(output.data()), input.data(), input.size());
}

void EncryptionHelpers::Decrypt(char* output, const char* data, size_t size)
{
  if (size > maxConcurrentInputSize_)
  {
    throw EncryptionException("The file is too large to decrypt: " + boost::lexical_cast<std::string>(size) + " bytes.  Try increasing the MaxConcurrentInputSize");
  }

  Orthanc::Semaphore::Locker lock(concurrentInputSizeSemaphore_, size);

  if (size < HEADER_VERSION_SIZE)
  {
    throw EncryptionException("Unable to decrypt data, no header found");
  }

  std::string version = std::string(data, HEADER_VERSION_SIZE);

  if (version != "A1")
  {
    throw EncryptionException("Unable to decrypt data, version '" + version + "' is not supported");
  }

  if (size < (HEADER_VERSION_SIZE + MASTER_KEY_ID_SIZE))
  {
    throw EncryptionException("Unable to decrypt data, no master key id found");
  }

  std::string decryptionMasterKeyId = std::string(data + HEADER_VERSION_SIZE, MASTER_KEY_ID_SIZE);

  const SecByteBlock& decryptionMasterKey = GetMasterKey(decryptionMasterKeyId);
  DecryptInternal(output, data, size, decryptionMasterKey);
}

void EncryptionHelpers::EncryptPrefixSecBlock(std::string& output, const CryptoPP::SecByteBlock& input, const CryptoPP::SecByteBlock& masterKey)
{
  try
  {
    SecByteBlock iv(16);
    memset(iv.data(), 0, iv.size());

    CTR_Mode<AES>::Encryption e;
    e.SetKeyWithIV(masterKey, masterKey.size(), iv.data(), iv.size());

    std::string inputString = ToString(input);

    // The StreamTransformationFilter adds padding
    //  as required. ECB and CBC Mode must be padded
    //  to the block size of the cipher.
    StringSource ss(inputString, true,
        new StreamTransformationFilter(e,
            new StringSink(output)
        ) // StreamTransformationFilter
    ); // StringSource
  }
  catch (CryptoPP::Exception& e)
  {
    throw EncryptionException(e.what());
  }

  assert(output.size() == input.size());
}

void EncryptionHelpers::DecryptPrefixSecBlock(CryptoPP::SecByteBlock& output, const std::string& input, const CryptoPP::SecByteBlock& masterKey)
{
  try
  {
    SecByteBlock iv(16);
    memset(iv.data(), 0, iv.size());

    CTR_Mode<AES>::Decryption  d;
    d.SetKeyWithIV(masterKey, masterKey.size(), iv.data(), iv.size());

    std::string outputString;

    // The StreamTransformationFilter adds padding
    //  as required. ECB and CBC Mode must be padded
    //  to the block size of the cipher.
    StringSource ss(input, true,
        new StreamTransformationFilter(d,
            new StringSink(outputString)
        ) // StreamTransformationFilter
    ); // StringSource

    output.Assign((const byte*)outputString.data(), outputString.size());
  }
  catch (CryptoPP::Exception& e)
  {
    throw EncryptionException(e.what());
  }

  assert(output.size() == input.size());
}


void EncryptionHelpers::EncryptInternal(std::string& output, const char* data, size_t size, const CryptoPP::SecByteBlock& masterKey)
{
  // std::cout << "EncryptInternal" << std::endl;
  // std::cout << "masterKey " << ToHexString(masterKey) << std::endl;

  SecByteBlock iv(IV_SIZE);
  randomGenerator_.GenerateBlock(iv, iv.size());  // with GCM, the iv is supposed to be a nonce (not a random number).  However, since each dataKey is used only once, we consider a random number is fine.

  SecByteBlock dataKey;
  GenerateKey(dataKey);

  // std::cout << "dataKey " << ToHexString(dataKey) << std::endl;
  // std::cout << "iv " << ToHexString(iv) << std::endl;
  std::string encryptedDataKey;
  std::string encryptedIv;

  EncryptPrefixSecBlock(encryptedIv, iv, masterKey);
  EncryptPrefixSecBlock(encryptedDataKey, dataKey, masterKey);

  // std::cout << "encryptedIv " << ToHexString(encryptedIv) << std::endl;
  // std::cout << "encryptedDataKey " << ToHexString(encryptedDataKey) << std::endl;

  std::string prefix = HEADER_VERSION + encryptionMasterKeyId_ + encryptedIv + encryptedDataKey;

  try
  {
    GCM<AES>::Encryption e;
    e.SetKeyWithIV(dataKey, dataKey.size(), iv, iv.size());

    // the output text starts with the unencrypted prefix
    output = prefix;

    AuthenticatedEncryptionFilter ef(e,
                                      new StringSink(output), false, INTEGRITY_CHECK_TAG_SIZE
                                      );


    // AuthenticatedEncryptionFilter::ChannelPut
    //  defines two channels: "" (empty) and "AAD"
    //   channel "" is encrypted and authenticated
    //   channel "AAD" is authenticated
    ef.ChannelPut("AAD", (const byte*)prefix.data(), prefix.size());
    ef.ChannelMessageEnd("AAD");

    // Authenticated data *must* be pushed before
    //  Confidential/Authenticated data. Otherwise
    //  we must catch the BadState exception
    ef.ChannelPut("", (const byte*)data, size);
    ef.ChannelMessageEnd("");
  }
  catch(CryptoPP::Exception& e)
  {
    throw EncryptionException(e.what());
  }
}

void EncryptionHelpers::DecryptInternal(char* output, const char* data, size_t size, const CryptoPP::SecByteBlock& masterKey)
{
  // std::cout << "DecryptInternal" << std::endl;
  // std::cout << "masterKey " << ToHexString(masterKey) << std::endl;

  size_t prefixSize = HEADER_VERSION_SIZE + MASTER_KEY_ID_SIZE + IV_SIZE + AES_KEY_SIZE;

  std::string prefix = std::string(data, prefixSize);
  std::string mac = std::string(data + size - INTEGRITY_CHECK_TAG_SIZE, INTEGRITY_CHECK_TAG_SIZE);

  // std::cout << "prefix " << ToHexString(prefix) << std::endl;
  // std::cout << "mac " << ToHexString(mac) << std::endl;

  std::string encryptedIv = prefix.substr(HEADER_VERSION_SIZE + MASTER_KEY_ID_SIZE, IV_SIZE);
  std::string encryptedDataKey = prefix.substr(HEADER_VERSION_SIZE + MASTER_KEY_ID_SIZE + IV_SIZE, AES_KEY_SIZE);

  // std::cout << "encryptedIv " << ToHexString(encryptedIv) << std::endl;
  // std::cout << "encryptedDataKey " << ToHexString(encryptedDataKey) << std::endl;

  SecByteBlock dataKey;
  SecByteBlock iv;

  DecryptPrefixSecBlock(iv, encryptedIv, masterKey);
  DecryptPrefixSecBlock(dataKey, encryptedDataKey, masterKey);
  // std::cout << "dataKey " << ToHexString(dataKey) << std::endl;
  // std::cout << "iv " << ToHexString(iv) << std::endl;

  GCM<AES>::Decryption d;
  d.SetKeyWithIV(dataKey, dataKey.size(), iv, iv.size());

  try {
    AuthenticatedDecryptionFilter df(d, NULL,
                                      AuthenticatedDecryptionFilter::MAC_AT_BEGIN |
                                      AuthenticatedDecryptionFilter::THROW_EXCEPTION, INTEGRITY_CHECK_TAG_SIZE);

    // The order of the following calls are important
    df.ChannelPut("", (const byte*)mac.data(), mac.size());
    df.ChannelPut("AAD", (const byte*)prefix.data(), prefix.size());
    df.ChannelPut("", (const byte*)(data) + prefixSize, size - INTEGRITY_CHECK_TAG_SIZE - prefixSize);

    // If the object throws, it will most likely occur
    //  during ChannelMessageEnd()
    df.ChannelMessageEnd("AAD");
    df.ChannelMessageEnd("");

    // If the object does not throw, here's the only
    // opportunity to check the data's integrity
    if (!df.GetLastResult())
    {
      throw EncryptionException("The decryption filter failed for some unknown reason.  Integrity check failed ?");
    }

    // Remove data from channel
    size_t n = (size_t)-1;

    // Recover plain text
    df.SetRetrievalChannel("");
    n = (size_t)df.MaxRetrievable();

    if(n > 0)
    {
      assert(n == size - OVERHEAD_SIZE);

      df.Get((byte*)output, n);
    }
  }
  catch (CryptoPP::Exception& ex)
  {
    throw EncryptionException(ex.what());
  }
}
