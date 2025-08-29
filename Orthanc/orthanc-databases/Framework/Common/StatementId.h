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


#pragma once

#include <string>

#define STATEMENT_FROM_HERE  ::OrthancDatabases::StatementId(__FILE__, __LINE__)
#define STATEMENT_FROM_HERE_DYNAMIC(sql)  ::OrthancDatabases::StatementId(__FILE__, __LINE__, sql)


namespace OrthancDatabases
{
  class StatementId
  {
  private:
    const char* file_;
    int line_;
    std::string statement_;
    std::string hash_;

    StatementId(); // Forbidden
    
  public:
    StatementId(const char* file,
                int line);

    StatementId(const char* file,
                int line,
                const std::string& statement);

    const char* GetFile() const
    {
      return file_;
    }

    int GetLine() const
    {
      return line_;
    }
    
    const std::string& GetDynamicStatement() const
    {
      return statement_;
    }

    bool operator< (const StatementId& other) const;
  };
}
