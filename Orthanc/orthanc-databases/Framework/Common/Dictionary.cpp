/**
 * Orthanc - A Lightweight, RESTful DICOM Store
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
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


#include "Dictionary.h"

#include "BinaryStringValue.h"
#include "InputFileValue.h"
#include "Integer32Value.h"
#include "Integer64Value.h"
#include "NullValue.h"
#include "Utf8StringValue.h"

#include <Logging.h>
#include <OrthancException.h>

#include <cassert>

namespace OrthancDatabases
{
  void Dictionary::Clear()
  {
    for (Values::iterator it = values_.begin(); 
         it != values_.end(); ++it)
    {
      assert(it->second != NULL);
      delete it->second;
    }

    values_.clear();
  }
  

  bool Dictionary::HasKey(const std::string& key) const
  {
    return values_.find(key) != values_.end();
  }


  void Dictionary::Remove(const std::string& key)
  {
    Values::iterator found = values_.find(key);

    if (found != values_.end())
    {
      assert(found->second != NULL);
      delete found->second;
      values_.erase(found);
    }
  }

  
  void Dictionary::SetValue(const std::string& key,
                            IValue* value)   // Takes ownership
  {
    if (value == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }

    Values::iterator found = values_.find(key);

    if (found == values_.end())
    {
      values_[key] = value;
    }
    else
    {
      assert(found->second != NULL);
      delete found->second;
      found->second = value;
    }      
  }

  
  void Dictionary::SetUtf8Value(const std::string& key,
                                const std::string& utf8)
  {
    SetValue(key, new Utf8StringValue(utf8));
  }

  
  void Dictionary::SetBinaryValue(const std::string& key,
                                  const std::string& binary)
  {
    SetValue(key, new BinaryStringValue(binary));
  }

  
  void Dictionary::SetBinaryValue(const std::string& key,
                                  const void* data,
                                  size_t size)
  {
    SetValue(key, new BinaryStringValue(data, size));
  }


  void Dictionary::SetFileValue(const std::string& key,
                                const std::string& file)
  {
    SetValue(key, new InputFileValue(file));
  }

  
  void Dictionary::SetFileValue(const std::string& key,
                                const void* content,
                                size_t size)
  {
    SetValue(key, new InputFileValue(content, size));
  }

  
  void Dictionary::SetIntegerValue(const std::string& key,
                                   int64_t value)
  {
    SetValue(key, new Integer64Value(value));
  }


  void Dictionary::SetInteger32Value(const std::string& key,
                                     int32_t value)
  {
    SetValue(key, new Integer32Value(value));
  }

  void Dictionary::SetUtf8NullValue(const std::string& key)
  {
    SetValue(key, new Utf8StringValue());
  }

  void Dictionary::SetBinaryNullValue(const std::string& key)
  {
    SetValue(key, new BinaryStringValue());
  }
  
  const IValue& Dictionary::GetValue(const std::string& key) const
  {
    Values::const_iterator found = values_.find(key);

    if (found == values_.end())
    {
      LOG(ERROR) << "Inexistent value in a dictionary: " << key;
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentItem);
    }
    else
    {
      assert(found->second != NULL);
      return *found->second;
    }
  }

  void Dictionary::GetParametersType(Query::Parameters& target) const
  {
    target.clear();

    for (Values::const_iterator it = values_.begin(); 
         it != values_.end(); ++it)
    {
      target[it->first] = it->second->GetType();
    }
  }
}
