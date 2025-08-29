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

#include "OdbcStatement.h"

#include "../Common/Dictionary.h"
#include "../Common/GenericFormatter.h"
#include "../Common/IPrecompiledStatement.h"
#include "../Common/IResult.h"


namespace OrthancDatabases
{
  class OdbcPreparedStatement : public IPrecompiledStatement
  {
  private:
    OdbcStatement             statement_;
    GenericFormatter          formatter_;
    std::vector<int64_t>      paramsInt64_;
    std::vector<std::string>  paramsString_;
    std::vector<size_t>       paramsIndex_;

    void Setup(const Query& query);
    
  public:      
    OdbcPreparedStatement(SQLHSTMT databaseHandle,
                          Dialect dialect,
                          const Query& query);

    OdbcPreparedStatement(SQLHSTMT databaseHandle,
                          Dialect dialect,
                          const std::string& sql);

    IResult* Execute();

    IResult* Execute(const Dictionary& parameters);
  };
}
