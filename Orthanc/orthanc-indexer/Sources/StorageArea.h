/**
 * Indexer plugin for Orthanc
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


#pragma once

#include <orthanc/OrthancCPlugin.h>

#include <boost/noncopyable.hpp>
#include <string>

class StorageArea : public boost::noncopyable
{
private:
  std::string  root_;

public:
  static void ReadWholeFromPath(OrthancPluginMemoryBuffer64 *target,
                                const std::string& path);  

  static void ReadRangeFromPath(OrthancPluginMemoryBuffer64 *target,
                                const std::string& path,
                                uint64_t rangeStart);

  explicit StorageArea(const std::string& root);
  
  void Create(const std::string& uuid,
              const void *content,
              int64_t size);

  void ReadWhole(std::string& target,
                 const std::string& uuid);

  void ReadWhole(OrthancPluginMemoryBuffer64 *target,
                 const std::string& uuid);

  void ReadRange(OrthancPluginMemoryBuffer64 *target,
                 const std::string& uuid,
                 uint64_t rangeStart);

  void RemoveAttachment(const std::string& uuid);

  std::string GetPath(const std::string& uuid) const;
};
