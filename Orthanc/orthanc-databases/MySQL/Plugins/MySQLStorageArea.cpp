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


#include "MySQLStorageArea.h"

#include "../../Framework/Common/BinaryStringValue.h"
#include "../../Framework/MySQL/MySQLDatabase.h"
#include "../../Framework/MySQL/MySQLTransaction.h"
#include "MySQLDefinitions.h"

#include <Compatibility.h>  // For std::unique_ptr<>
#include <Logging.h>

#include <boost/math/special_functions/round.hpp>


namespace OrthancDatabases
{
  void MySQLStorageArea::ConfigureDatabase(MySQLDatabase& db,
                                           const MySQLParameters& parameters,
                                           bool clearAll)
  {
    {
      MySQLDatabase::TransientAdvisoryLock lock(db, MYSQL_LOCK_DATABASE_SETUP);    
      MySQLTransaction t(db, TransactionType_ReadWrite);

      int64_t size;
      if (db.LookupGlobalIntegerVariable(size, "max_allowed_packet"))
      {
        int mb = boost::math::iround(static_cast<double>(size) /
                                     static_cast<double>(1024 * 1024));
        LOG(WARNING) << "Your MySQL server cannot "
                     << "store DICOM files larger than " << mb << "MB";
        LOG(WARNING) << "  => Consider increasing \"max_allowed_packet\" "
                     << "in \"my.cnf\" if this limit is insufficient for your use";
      }
      else
      {
        LOG(WARNING) << "Unable to auto-detect the maximum size of DICOM "
                     << "files that can be stored in this MySQL server";
      }
               
      if (clearAll)
      {
        db.ExecuteMultiLines("DROP TABLE IF EXISTS StorageArea", false);
      }

      db.ExecuteMultiLines("CREATE TABLE IF NOT EXISTS StorageArea("
                           "uuid VARCHAR(64) NOT NULL PRIMARY KEY,"
                           "content LONGBLOB NOT NULL,"
                           "type INTEGER NOT NULL)", false);

      t.Commit();
    }

    /**
     * WARNING: This lock must be acquired after
     * "MYSQL_LOCK_DATABASE_SETUP" is released. Indeed, in MySQL <
     * 5.7, it is impossible to acquire more than one lock at a time,
     * as calling "SELECT GET_LOCK()" releases all the
     * previously-acquired locks.
     * https://dev.mysql.com/doc/refman/5.7/en/locking-functions.html
     **/
    if (parameters.HasLock())
    {
      db.AdvisoryLock(MYSQL_LOCK_STORAGE);
    }
  }


  MySQLStorageArea::MySQLStorageArea(const MySQLParameters& parameters,
                                     bool clearAll) :
    StorageBackend(MySQLDatabase::CreateDatabaseFactory(parameters),
                   parameters.GetMaxConnectionRetries())
  {
    {
      AccessorBase accessor(*this);
      MySQLDatabase& database = dynamic_cast<MySQLDatabase&>(accessor.GetManager().GetDatabase());
      ConfigureDatabase(database, parameters, clearAll);
    }
  }


  class MySQLStorageArea::Accessor : public StorageBackend::AccessorBase
  {
  public:
    explicit Accessor(MySQLStorageArea& backend) :
      AccessorBase(backend)
    {
    }

    virtual void ReadRange(IFileContentVisitor& visitor,
                           const std::string& uuid,
                           OrthancPluginContentType type,
                           uint64_t start,
                           size_t length) ORTHANC_OVERRIDE
    {
      DatabaseManager::Transaction transaction(GetManager(), TransactionType_ReadOnly);

      {
        // https://stackoverflow.com/a/6545557/881731
        DatabaseManager::CachedStatement statement(
          STATEMENT_FROM_HERE, GetManager(),
          "SELECT SUBSTRING(content, ${start}, ${length}) FROM StorageArea WHERE uuid=${uuid} AND type=${type}");
     
        statement.SetParameterType("uuid", ValueType_Utf8String);
        statement.SetParameterType("type", ValueType_Integer64);
        statement.SetParameterType("start", ValueType_Integer64);
        statement.SetParameterType("length", ValueType_Integer64);

        Dictionary args;
        args.SetUtf8Value("uuid", uuid);
        args.SetIntegerValue("type", type);
        args.SetIntegerValue("length", length);

        /**
         * "For all forms of SUBSTRING(), the position of the first
         * character in the string from which the substring is to be
         * extracted is reckoned as 1." => hence the "+ 1"
         * https://dev.mysql.com/doc/refman/8.0/en/string-functions.html#function_substring
         **/
        args.SetIntegerValue("start", start + 1);
     
        statement.Execute(args);

        if (statement.IsDone())
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
        }
        else if (statement.GetResultFieldsCount() != 1)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);        
        }
        else
        {
          const IValue& value = statement.GetResultField(0);
      
          if (value.GetType() == ValueType_BinaryString)
          {
            const std::string& content = dynamic_cast<const BinaryStringValue&>(value).GetContent();

            if (static_cast<uint64_t>(content.size()) == length)
            {
              visitor.Assign(content);
            }
            else
            {
              throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRange);
            }
          }
          else
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);        
          }
        }
      }

      transaction.Commit();

      if (!visitor.IsSuccess())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Could not read range from the storage area");
      }
    }
  };
  

  StorageBackend::IAccessor* MySQLStorageArea::CreateAccessor()
  {
    return new Accessor(*this);
  }
}
