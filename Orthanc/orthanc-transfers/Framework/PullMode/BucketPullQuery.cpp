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


#include "BucketPullQuery.h"


namespace OrthancPlugins
{
  BucketPullQuery::BucketPullQuery(DownloadArea& area,
                                   const TransferBucket& bucket,
                                   const std::string& peer,
                                   BucketCompression compression) :
    area_(area),
    bucket_(bucket),
    peer_(peer),
    compression_(compression)
  {
    bucket_.ComputePullUri(uri_, compression_);
  }


  void BucketPullQuery::ReadBody(std::string& body) const
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }

  
  void BucketPullQuery::HandleAnswer(const void* answer,
                                     size_t size)
  {
    area_.WriteBucket(bucket_, answer, size, compression_);
  }
}
