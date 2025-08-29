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


#include "IResult.h"

#include "Utf8StringValue.h"

#include <Compatibility.h>
#include <OrthancException.h>

#include <cassert>
#include <list>
#include <vector>
#include <ostream>

namespace OrthancDatabases
{
  static void PrintSeparators(std::ostream& stream,
                              char c,
                              size_t count)
  {
    for (size_t i = 0; i < count; i++)
    {
      stream << c;
    }
  }

  
  static void PrintHeader(std::ostream& stream,
                          const std::vector<size_t>& maxWidth)
  {
    for (size_t i = 0; i < maxWidth.size(); i++)
    {
      stream << '+';
      PrintSeparators(stream, '-', maxWidth[i] + 2);
    }

    stream << '+' << std::endl;
  }
    

  void IResult::Print(std::ostream& stream,
                      IResult& result)
  {
    typedef std::list< std::vector<std::string> > Table;

    Table table;

    const size_t columns = result.GetFieldsCount();

    std::vector<size_t> maxWidth(columns);    
    
    while (!result.IsDone())
    {
      table.push_back(std::vector<std::string>(columns));
      
      for (size_t i = 0; i < columns; i++)
      {
        std::string value;

        try
        {
          std::unique_ptr<IValue> converted(
            result.GetField(i).Convert(ValueType_Utf8String));
          value = dynamic_cast<Utf8StringValue&>(*converted).GetContent();
        }
        catch (Orthanc::OrthancException&)
        {
          value = "?";
        }

        if (value.size() > maxWidth[i])
        {
          maxWidth[i] = value.size();
        }

        table.back() [i] = value;
      }
            
      result.Next();
    }

    PrintHeader(stream, maxWidth);

    for (Table::const_iterator it = table.begin(); it != table.end(); ++it)
    {
      assert(it->size() == maxWidth.size());
      
      for (size_t i = 0; i < it->size(); i++)
      {
        const std::string& value = (*it) [i];
        
        stream << "| " << value << ' ';

        for (size_t j = value.size(); j < maxWidth[i]; j++)
        {
          stream << ' ';
        }
      }

      stream << '|' << std::endl;
    }

    PrintHeader(stream, maxWidth);
  }
}
