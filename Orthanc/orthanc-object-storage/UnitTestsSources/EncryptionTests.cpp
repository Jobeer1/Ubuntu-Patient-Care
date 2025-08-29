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


#include "gtest/gtest.h"

#include "../Common/EncryptionHelpers.h"
#include <boost/chrono/chrono.hpp>
#include <boost/date_time.hpp>

TEST(EncryptionHelpers, GenerateKey)
{
  CryptoPP::SecByteBlock key1, key2;
  EncryptionHelpers::GenerateKey(key1);
  EncryptionHelpers::GenerateKey(key2);

//  std::cout << EncryptionHelpers::ToHexString(key1) << std::endl;
//  std::cout << EncryptionHelpers::ToHexString(key2) << std::endl;

  ASSERT_NE(key1, key2);

  ASSERT_EQ(32u, key1.size()); // right now, we work with 256bits key
  ASSERT_EQ(32u * 2u, EncryptionHelpers::ToHexString(key1).size());
}

TEST(EncryptionHelpers, EncryptDecryptSimpleText)
{
  CryptoPP::SecByteBlock masterKey;
  EncryptionHelpers::GenerateKey(masterKey);

  EncryptionHelpers crypto;
  crypto.SetCurrentMasterKey(1, masterKey);

  std::string plainTextMessage = "Plain text message";
  std::string encryptedMessage;

  crypto.Encrypt(encryptedMessage, plainTextMessage);

  std::string decryptedMessage;

  crypto.Decrypt(decryptedMessage, encryptedMessage);

  ASSERT_EQ(plainTextMessage, decryptedMessage);
}

TEST(EncryptionHelpers, EncryptDecrypt1byteText)
{
  CryptoPP::SecByteBlock masterKey;
  EncryptionHelpers::GenerateKey(masterKey);

  EncryptionHelpers crypto;
  crypto.SetCurrentMasterKey(1, masterKey);

  std::string plainTextMessage = "P";
  std::string encryptedMessage;

  crypto.Encrypt(encryptedMessage, plainTextMessage);

  std::string decryptedMessage;

  crypto.Decrypt(decryptedMessage, encryptedMessage);

  ASSERT_EQ(plainTextMessage, decryptedMessage);
}

TEST(EncryptionHelpers, EncryptDecrypt0byteText)
{
  CryptoPP::SecByteBlock masterKey;
  EncryptionHelpers::GenerateKey(masterKey);

  EncryptionHelpers crypto;
  crypto.SetCurrentMasterKey(1, masterKey);

  std::string plainTextMessage = "";
  std::string encryptedMessage;

  crypto.Encrypt(encryptedMessage, plainTextMessage);

  std::string decryptedMessage;

  crypto.Decrypt(decryptedMessage, encryptedMessage);

  ASSERT_EQ(plainTextMessage, decryptedMessage);
}

TEST(EncryptionHelpers, EncryptDecryptTampering)
{
  CryptoPP::SecByteBlock masterKey;
  EncryptionHelpers::GenerateKey(masterKey);

  EncryptionHelpers crypto;
  crypto.SetCurrentMasterKey(1, masterKey);

  std::string plainTextMessage = "Plain text message";
  std::string encryptedMessage;
  std::string decryptedMessage;

  crypto.Encrypt(encryptedMessage, plainTextMessage);

  {
    std::string tamperedEncryptedMessage = encryptedMessage;
    // change the header
    tamperedEncryptedMessage[0] = 'B';
    ASSERT_THROW(crypto.Decrypt(decryptedMessage, tamperedEncryptedMessage), EncryptionException);
  }

  {
    std::string tamperedEncryptedMessage = encryptedMessage;
    // tamper the masterKeyId:
    tamperedEncryptedMessage[EncryptionHelpers::HEADER_VERSION_SIZE + 2] = 0xAF;
    ASSERT_THROW(crypto.Decrypt(decryptedMessage, tamperedEncryptedMessage), EncryptionException);
  }

  {
    std::string tamperedEncryptedMessage = encryptedMessage;
    // tamper the iv:
    tamperedEncryptedMessage[EncryptionHelpers::HEADER_VERSION_SIZE + EncryptionHelpers::MASTER_KEY_ID_SIZE + 2] = 0;
    ASSERT_THROW(crypto.Decrypt(decryptedMessage, tamperedEncryptedMessage), EncryptionException);
  }

  {
    std::string tamperedEncryptedMessage = encryptedMessage;
    // tamper the encrypted text:
    tamperedEncryptedMessage[EncryptionHelpers::HEADER_VERSION_SIZE + EncryptionHelpers::MASTER_KEY_ID_SIZE + EncryptionHelpers::IV_SIZE + 2] = 0;
    ASSERT_THROW(crypto.Decrypt(decryptedMessage, tamperedEncryptedMessage), EncryptionException);
  }

  {
    std::string tamperedEncryptedMessage = encryptedMessage;
    // tamper the mac:
    tamperedEncryptedMessage[tamperedEncryptedMessage.size() - 2] = 0;
    ASSERT_THROW(crypto.Decrypt(decryptedMessage, tamperedEncryptedMessage), EncryptionException);
  }

  {
    std::string tamperedEncryptedMessage = encryptedMessage;
    // extend the file content
    tamperedEncryptedMessage = tamperedEncryptedMessage + "TAMPER";
    ASSERT_THROW(crypto.Decrypt(decryptedMessage, tamperedEncryptedMessage), EncryptionException);
  }

  {
    std::string tamperedEncryptedMessage = encryptedMessage;
    // reduce the file content
    tamperedEncryptedMessage = tamperedEncryptedMessage.substr(0, tamperedEncryptedMessage.size() - 5);
    ASSERT_THROW(crypto.Decrypt(decryptedMessage, tamperedEncryptedMessage), EncryptionException);
  }
}


TEST(EncryptionHelpers, EncryptDecrypt2TimesSameText)
{
  CryptoPP::SecByteBlock masterKey;
  EncryptionHelpers::GenerateKey(masterKey);

  EncryptionHelpers crypto;
  crypto.SetCurrentMasterKey(1, masterKey);

  std::string plainTextMessage = "Plain text message";
  std::string encryptedMessage1;
  std::string encryptedMessage2;

  crypto.Encrypt(encryptedMessage1, plainTextMessage);
  crypto.Encrypt(encryptedMessage2, plainTextMessage);

  ASSERT_NE(encryptedMessage1, encryptedMessage2);

  std::string decryptedMessage1;
  std::string decryptedMessage2;

  crypto.Decrypt(decryptedMessage1, encryptedMessage1);
  crypto.Decrypt(decryptedMessage2, encryptedMessage2);

  ASSERT_EQ(plainTextMessage, decryptedMessage1);
  ASSERT_EQ(plainTextMessage, decryptedMessage2);
}

TEST(EncryptionHelpers, RotateMasterKeys)
{
  std::string plainTextMessage = "Plain text message";
  std::string encryptedMessage1;
  std::string encryptedMessage2;
  std::string decryptedMessage;

  CryptoPP::SecByteBlock masterKey1;
  CryptoPP::SecByteBlock masterKey2;
  EncryptionHelpers::GenerateKey(masterKey1);
  EncryptionHelpers::GenerateKey(masterKey2);

  {
    EncryptionHelpers crypto;
    crypto.SetCurrentMasterKey(1, masterKey1);
    crypto.Encrypt(encryptedMessage1, plainTextMessage);

    crypto.SetCurrentMasterKey(2, masterKey2);
    crypto.AddPreviousMasterKey(1, masterKey1);

    crypto.Encrypt(encryptedMessage2, plainTextMessage);

    // ensure that we can decrypt messages encrypted with both master keys
    crypto.Decrypt(decryptedMessage, encryptedMessage1);
    ASSERT_EQ(plainTextMessage, decryptedMessage);

    crypto.Decrypt(decryptedMessage, encryptedMessage2);
    ASSERT_EQ(plainTextMessage, decryptedMessage);
  }

  {
    // if we don't know the old key, check we can not decrypt the old message
    EncryptionHelpers crypto;
    crypto.SetCurrentMasterKey(2, masterKey2);

    ASSERT_THROW(crypto.Decrypt(decryptedMessage, encryptedMessage1), EncryptionException);
  }
}


void MeasurePerformance(size_t sizeInMB, EncryptionHelpers& crypto)
{
  std::string encryptedMessage;
  std::string decryptedMessage;

  {
    const std::string largePlainText(sizeInMB * 1024 * 1024, 'A');

    auto start = boost::posix_time::microsec_clock::local_time();
    crypto.Encrypt(encryptedMessage, largePlainText);

    auto end = boost::posix_time::microsec_clock::local_time();
    boost::posix_time::time_duration diff = end - start;
    std::cout << "encryption of " << sizeInMB << " MB file took " << diff.total_milliseconds() << " ms" << std::endl;
  }

  {
    auto start = boost::posix_time::microsec_clock::local_time();
    crypto.Decrypt(decryptedMessage, encryptedMessage);

    auto end = boost::posix_time::microsec_clock::local_time();
    boost::posix_time::time_duration diff = end - start;
    std::cout << "decryption of " << sizeInMB << " MB file took " << diff.total_milliseconds() << " ms" << std::endl;
  }

}

TEST(EncryptionHelpers, Performance)
{
  CryptoPP::SecByteBlock masterKey;
  EncryptionHelpers::GenerateKey(masterKey);

  EncryptionHelpers crypto;
  crypto.SetCurrentMasterKey(1, masterKey);

  MeasurePerformance(1, crypto);
  MeasurePerformance(10, crypto);
//  MeasurePerformance(100, crypto);
//  MeasurePerformance(400, crypto);
}
