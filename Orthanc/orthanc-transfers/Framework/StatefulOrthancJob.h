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


#pragma once

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <Compatibility.h>  // For std::unique_ptr

#include <memory>


namespace OrthancPlugins
{
  class StatefulOrthancJob : public OrthancJob
  {
  protected:
    class IState;


    class JobInfo : public boost::noncopyable
    {
    private:
      StatefulOrthancJob&  job_;
      bool                 updated_;
      Json::Value          content_;

    public:
      explicit JobInfo(StatefulOrthancJob& job);

      void SetProgress(float progress)
      {
        job_.UpdateProgress(progress);
      }

      void SetContent(const std::string& key,
                      const Json::Value& value);

      void Update();
    };
    

    
    class StateUpdate : public boost::noncopyable
    {
    private:
      OrthancPluginJobStepStatus  status_;
      std::unique_ptr<IState>       state_;

      explicit StateUpdate(OrthancPluginJobStepStatus status) :
        status_(status)
      {
      }

      explicit StateUpdate(IState* state);

    public:
      static StateUpdate* Next(IState* state)  // Takes ownsership
      {
        return new StateUpdate(state);
      }

      static StateUpdate* Continue()
      {
        return new StateUpdate(OrthancPluginJobStepStatus_Continue);
      }

      static StateUpdate* Success()
      {
        return new StateUpdate(OrthancPluginJobStepStatus_Success);
      }

      static StateUpdate* Failure()
      {
        return new StateUpdate(OrthancPluginJobStepStatus_Failure);
      }

      OrthancPluginJobStepStatus GetStatus() const
      {
        return status_;
      }
      
      bool IsOtherState() const
      {
        return state_.get() != NULL;
      }

      IState* ReleaseOtherState();
    };    


    class IState : public boost::noncopyable
    {
    public:
      virtual ~IState()
      {
      }

      virtual StateUpdate* Step() = 0;

      virtual void Stop(OrthancPluginJobStopReason reason) = 0;
    };

    
    virtual StateUpdate* CreateInitialState(JobInfo& info) = 0;
    

  private:
    std::unique_ptr<IState>   state_;
    JobInfo                 info_;


  public:
    StatefulOrthancJob(const std::string& jobType);
    
    virtual OrthancPluginJobStepStatus Step();

    virtual void Stop(OrthancPluginJobStopReason reason);
    
    virtual void Reset();
  };
}
