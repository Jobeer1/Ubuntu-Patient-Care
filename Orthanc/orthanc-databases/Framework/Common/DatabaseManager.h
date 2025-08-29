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

#include "IDatabaseFactory.h"
#include "StatementId.h"

#include <Compatibility.h>  // For std::unique_ptr<>
#include <Enumerations.h>

#include <memory>
#include <boost/date_time/posix_time/posix_time.hpp>


namespace OrthancDatabases
{
  /**
   * WARNING: In PostgreSQL releases <= 3.3 and in MySQL releases <=
   * 3.0, this class was protected by a mutex. It is now assumed that
   * locking must be implemented at a higher level.
   *
   * This class maintains a list of precompiled statements. At any
   * time, this class handles 0 or 1 active transaction.
   *
   * "DatabaseManager" takes a "IDatabaseFactory" as input, in order
   * to be able to automatically re-open the database connection if
   * the latter gets lost.
   **/
  class DatabaseManager : public boost::noncopyable
  {
  private:
    typedef std::map<StatementId, IPrecompiledStatement*>  CachedStatements;

    std::unique_ptr<IDatabaseFactory>  factory_;
    std::unique_ptr<IDatabase>     database_;
    std::unique_ptr<ITransaction>  transaction_;
    CachedStatements               cachedStatements_;
    Dialect                        dialect_;
    boost::posix_time::ptime       creationTime_;
    boost::posix_time::ptime       lastUseTime_;

    void CloseIfUnavailable(Orthanc::ErrorCode e);

    IPrecompiledStatement* LookupCachedStatement(const StatementId& statementId) const;

    IPrecompiledStatement& CacheStatement(const StatementId& statementId,
                                          const Query& query);

    ITransaction& GetTransaction();

    void ReleaseImplicitTransaction();

  public:
    explicit DatabaseManager(IDatabaseFactory* factory);  // Takes ownership
    
    ~DatabaseManager()
    {
      Close();
    }

    IDatabase& GetDatabase();

    Dialect GetDialect() const;

    void Close();
    
    void StartTransaction(TransactionType type);

    void CommitTransaction();
    
    void RollbackTransaction();

    uint64_t GetElapsedSecondsSinceCreation() const;

    uint64_t GetElapsedSecondsSinceLastUse() const;

    // This class is only used in the "StorageBackend" and in
    // "IDatabaseBackend::ConfigureDatabase()"
    class Transaction : public boost::noncopyable
    {
    private:
      DatabaseManager&  manager_;
      IDatabase&        database_;
      bool              active_;

    public:
      explicit Transaction(DatabaseManager& manager,
                           TransactionType type);

      ~Transaction();

      void Commit();

      void Rollback();

      /**
       * WARNING: Don't call "GetDatabaseTransaction().Commit()" and
       * "GetDatabaseTransaction().Rollback()", but use the "Commit()"
       * and "Rollback()" methods above.
       **/
      ITransaction& GetDatabaseTransaction()
      {
        return manager_.GetTransaction();
      }
    };


    class StatementBase : public boost::noncopyable
    {
    private:
      DatabaseManager&          manager_;
      ITransaction&             transaction_;
      std::unique_ptr<Query>    query_;
      std::unique_ptr<IResult>  result_;

      IResult& GetResult() const;

    protected:
      DatabaseManager& GetManager() const
      {
        return manager_;
      }

      ITransaction& GetTransaction() const
      {
        return transaction_;
      }
      
      void SetQuery(Query* query);

      void SetResult(IResult* result);

      void ClearResult()
      {
        result_.reset();
      }

      Query* ReleaseQuery()
      {
        return query_.release();
      }

      void SetParametersTypes(const Dictionary& parameters);
      
    public:
      explicit StatementBase(DatabaseManager& manager);

      virtual ~StatementBase();

      // Used only by SQLite
      IDatabase& GetDatabase()
      {
        return manager_.GetDatabase();
      }

      void SetReadOnly(bool readOnly);

      void SetParameterType(const std::string& parameter,
                            ValueType type);
      
      bool IsDone() const;
      
      void Next();

      size_t GetResultFieldsCount() const;

      void SetResultFieldType(size_t field,
                              ValueType type);
      
      const IValue& GetResultField(size_t index) const;

      int32_t ReadInteger32(size_t field) const;

      int64_t ReadInteger64(size_t field) const;

      std::string ReadString(size_t field) const;

      std::string ReadStringOrNull(size_t field) const;

      bool IsNull(size_t field) const;

      void PrintResult(std::ostream& stream)
      {
        IResult::Print(stream, GetResult());
      }

      virtual void Execute(const Dictionary& parameters) = 0;
    };


    /**
     * WARNING: At any given time, there must be at most 1 object of
     * the "CachedStatement" class in the scope, otherwise error
     * "Cannot execute more than one statement in an implicit
     * transaction" is generated if no explicit transaction is
     * present.
     **/
    class CachedStatement : public StatementBase
    {
    private:
      StatementId             statementId_;
      IPrecompiledStatement*  statement_;

      void Setup(const std::string& sql,
                 const Query::Parameters& parametersTypes);
                 
    public:
      CachedStatement(const StatementId& statementId,
                      DatabaseManager& manager,
                      const std::string& sql);

      CachedStatement(const StatementId& statementId,
                      DatabaseManager& manager,
                      const std::string& sql,
                      const Query::Parameters& parametersTypes);

      void Execute()
      {
        Dictionary parameters;
        Execute(parameters);
      }

      virtual void Execute(const Dictionary& parameters) ORTHANC_OVERRIDE;

      void ExecuteWithoutResult()
      {
        Dictionary parameters;
        ExecuteWithoutResult(parameters);
      }

      void ExecuteWithoutResult(const Dictionary& parameters);

    private:
      void ExecuteInternal(const Dictionary& parameters, bool withResults);
    };


    class StandaloneStatement : public StatementBase
    {
    private:
      std::unique_ptr<IPrecompiledStatement>  statement_;
      
    public:
      StandaloneStatement(DatabaseManager& manager,
                          const std::string& sql);

      StandaloneStatement(DatabaseManager& manager,
                          const std::string& sql,
                          const Query::Parameters& parametersTypes);

      virtual ~StandaloneStatement();

      void Execute()
      {
        Dictionary parameters;
        Execute(parameters);
      }

      virtual void Execute(const Dictionary& parameters) ORTHANC_OVERRIDE;

      void ExecuteWithoutResult()
      {
        Dictionary parameters;
        ExecuteWithoutResult(parameters);
      }

      void ExecuteWithoutResult(const Dictionary& parameters);

    private:
      void ExecuteInternal(const Dictionary& parameters, bool withResults);
    };
  };
}
