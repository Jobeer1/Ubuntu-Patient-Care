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

#include "ITransaction.h"

#include <Compatibility.h>

namespace OrthancDatabases
{
  class ImplicitTransaction : public ITransaction
  {
  private:
    enum State
    {
      State_Ready,
      State_Executed,
      State_Committed
    };

    State   state_;

    void CheckStateForExecution();
    
  protected:
    virtual IResult* ExecuteInternal(IPrecompiledStatement& statement,
                                     const Dictionary& parameters) = 0;

    virtual void ExecuteWithoutResultInternal(IPrecompiledStatement& statement,
                                              const Dictionary& parameters) = 0;
    
  public:
    ImplicitTransaction();

    virtual ~ImplicitTransaction();
    
    virtual bool IsImplicit() const ORTHANC_OVERRIDE
    {
      return true;
    }
    
    virtual void Rollback() ORTHANC_OVERRIDE;
    
    virtual void Commit() ORTHANC_OVERRIDE;
    
    virtual IResult* Execute(IPrecompiledStatement& statement,
                             const Dictionary& parameters) ORTHANC_OVERRIDE;

    virtual void ExecuteWithoutResult(IPrecompiledStatement& statement,
                                      const Dictionary& parameters) ORTHANC_OVERRIDE;

    static void SetErrorOnDoubleExecution(bool isError);

    static bool IsErrorOnDoubleExecution();
  };
}
