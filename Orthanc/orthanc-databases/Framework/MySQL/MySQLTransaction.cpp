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


#include "MySQLTransaction.h"

#include "MySQLStatement.h"

#include <Compatibility.h>  // For std::unique_ptr<>
#include <Logging.h>
#include <OrthancException.h>

#include <memory>

namespace OrthancDatabases
{
  MySQLTransaction::MySQLTransaction(MySQLDatabase& db,
                                     TransactionType type) :
    db_(db),
    active_(false)
  {
    switch (type)
    {
      case TransactionType_ReadWrite:
        db_.ExecuteMultiLines("START TRANSACTION READ WRITE", false);
        break;

      case TransactionType_ReadOnly:
        db_.ExecuteMultiLines("START TRANSACTION READ ONLY", false);
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
        
    active_ = true;
  }

  
  MySQLTransaction::~MySQLTransaction()
  {
    if (active_)
    {
      LOG(INFO) << "An active MySQL transaction was dismissed";

      try
      {
        db_.ExecuteMultiLines("ROLLBACK", false);
      }
      catch (Orthanc::OrthancException&)
      {
        // Ignore possible exceptions due to connection loss
      }
    }
  }

  
  void MySQLTransaction::Rollback()
  {
    if (active_)
    {
      db_.ExecuteMultiLines("ROLLBACK", false);
      active_ = false;
    }
    else
    {
      LOG(ERROR) << "MySQL: This transaction is already finished";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }

  
  void MySQLTransaction::Commit()
  {
    if (active_)
    {
      db_.ExecuteMultiLines("COMMIT", false);
      active_ = false;
    }
    else
    {
      LOG(ERROR) << "MySQL: This transaction is already finished";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }


  IResult* MySQLTransaction::Execute(IPrecompiledStatement& statement,
                                     const Dictionary& parameters)
  {
    return dynamic_cast<MySQLStatement&>(statement).Execute(*this, parameters);
  }


  void MySQLTransaction::ExecuteWithoutResult(IPrecompiledStatement& statement,
                                              const Dictionary& parameters)
  {
    dynamic_cast<MySQLStatement&>(statement).ExecuteWithoutResult(*this, parameters);
  }
}
