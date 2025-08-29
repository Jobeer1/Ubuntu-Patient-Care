/**
 * Transfers accelerator plugin for Orthanc
 * Copyright (C) 2018-2023 Osimis S.A., Belgium
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


#include "TransferToolbox.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <Logging.h>
#include <OrthancException.h>

#include <boost/math/special_functions/round.hpp>
#include <boost/thread/thread.hpp>


namespace OrthancPlugins
{
  unsigned int ConvertToMegabytes(uint64_t value)
  {
    return static_cast<unsigned int>
      (boost::math::round(static_cast<float>(value) / static_cast<float>(MB)));
  }


  unsigned int ConvertToKilobytes(uint64_t value)
  {
    return static_cast<unsigned int>
      (boost::math::round(static_cast<float>(value) / static_cast<float>(KB)));
  }


  BucketCompression StringToBucketCompression(const std::string& value)
  {
    if (value == "gzip")
    {
      return BucketCompression_Gzip;
    }
    else if (value == "none")
    {
      return BucketCompression_None;
    }
    else
    {
      LOG(ERROR) << "Valid compression methods are \"gzip\" and \"none\", but found: " << value;
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }


  const char* EnumerationToString(BucketCompression compression)
  {
    switch (compression)
    {
      case BucketCompression_Gzip:
        return "gzip";

      case BucketCompression_None:
        return "none";
        
      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }


  bool DoPostPeer(Json::Value& answer,
                  const OrthancPeers& peers,
                  size_t peerIndex,
                  const std::string& uri,
                  const std::string& body,
                  unsigned int maxRetries,
                  const std::map<std::string, std::string>& headers,
                  unsigned int timeout
)
  {
    std::map<std::string, std::string> answerHeadersNotUsed;
    return DoPostPeer(answer, 
                      answerHeadersNotUsed,
                      peers,
                      peerIndex,
                      uri,
                      body,
                      maxRetries,
                      headers,
                      timeout);
  }


  bool DoPostPeer(Json::Value& answer,
                  std::map<std::string, std::string>& answerHeaders,
                  const OrthancPeers& peers,
                  size_t peerIndex,
                  const std::string& uri,
                  const std::string& body,
                  unsigned int maxRetries,
                  const std::map<std::string, std::string>& headers,
                  unsigned int timeout
)
  {
    unsigned int retry = 0;

    for (;;)
    {
      try
      {
        if (peers.DoPost(answer, answerHeaders, peerIndex, uri, body, headers, timeout))
        {
          return true;
        }
      }
      catch (Orthanc::OrthancException&)
      {
      }

      if (retry >= maxRetries)
      {
        return false;
      }
      else
      {
        // Wait 1 second before retrying
        boost::this_thread::sleep(boost::posix_time::seconds(1));
        retry++;
      }
    }
  }


  bool DoPostPeer(Json::Value& answer,
                  const OrthancPeers& peers,
                  size_t peerIndex,
                  const std::string& uri,
                  const std::string& body,
                  unsigned int maxRetries,
                  const std::map<std::string, std::string>& headers
)
  {
    unsigned int retry = 0;

    for (;;)
    {
      try
      {
        if (peers.DoPost(answer, peerIndex, uri, body, headers))
        {
          return true;
        }
      }
      catch (Orthanc::OrthancException&)
      {
      }

      if (retry >= maxRetries)
      {
        return false;
      }
      else
      {
        // Wait 1 second before retrying
        boost::this_thread::sleep(boost::posix_time::seconds(1));
        retry++;
      }
    }
  }


  bool DoPostPeer(Json::Value& answer,
                  const OrthancPeers& peers,
                  const std::string& peerName,
                  const std::string& uri,
                  const std::string& body,
                  unsigned int maxRetries,
                  const std::map<std::string, std::string>& headers)
  {
    size_t index;

    return (peers.LookupName(index, peerName) &&
            DoPostPeer(answer, peers, index, uri, body, maxRetries, headers));
  }


  bool DoDeletePeer(const OrthancPeers& peers,
                    size_t peerIndex,
                    const std::string& uri,
                    unsigned int maxRetries,
                    const std::map<std::string, std::string>& headers)
  {
    unsigned int retry = 0;

    for (;;)
    {
      try
      {
        if (peers.DoDelete(peerIndex, uri, headers))
        {
          return true;
        }
      }
      catch (Orthanc::OrthancException&)
      {
      }
      
      if (retry >= maxRetries)
      {
        return false;
      }
      else
      {
        // Wait 1 second before retrying
        boost::this_thread::sleep(boost::posix_time::seconds(1));
        retry++;
      }
    }
  }
}
