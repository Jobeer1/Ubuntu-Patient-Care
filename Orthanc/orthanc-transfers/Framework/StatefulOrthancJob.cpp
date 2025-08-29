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


#include "StatefulOrthancJob.h"

#include <Compatibility.h>  // For std::unique_ptr

namespace OrthancPlugins
{
  StatefulOrthancJob::JobInfo::JobInfo(StatefulOrthancJob& job) :
    job_(job),
    updated_(true),
    content_(Json::objectValue)
  {
  }


  void StatefulOrthancJob::JobInfo::SetContent(const std::string& key,
                                               const Json::Value& value)
  {
    content_[key] = value;
    updated_ = true;
  }

  
  void StatefulOrthancJob::JobInfo::Update()
  {
    if (updated_)
    {
      job_.UpdateContent(content_);
      updated_ = false;
    }
  }
    

  StatefulOrthancJob::StateUpdate::StateUpdate(IState* state) :
    status_(OrthancPluginJobStepStatus_Continue),
    state_(state)
  {
    if (state == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
  }


  StatefulOrthancJob::IState* StatefulOrthancJob::StateUpdate::ReleaseOtherState()
  {
    if (state_.get() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      return state_.release();
    }
  }


  StatefulOrthancJob::StatefulOrthancJob(const std::string& jobType) :
    OrthancJob(jobType),
    info_(*this)
  {
  }

  
  OrthancPluginJobStepStatus StatefulOrthancJob::Step()
  {
    std::unique_ptr<StateUpdate> update;

    if (state_.get() == NULL)
    {        
      update.reset(CreateInitialState(info_));
    }
    else
    {
      update.reset(state_->Step());
    }

    info_.Update();

    if (update.get() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }

    if (update->IsOtherState())
    {
      state_.reset(update->ReleaseOtherState());
      assert(state_.get() != NULL);

      return OrthancPluginJobStepStatus_Continue;
    }
    else
    {
      OrthancPluginJobStepStatus status = update->GetStatus();

      if (status == OrthancPluginJobStepStatus_Success)
      {
        info_.SetProgress(1);
      }

      if (status == OrthancPluginJobStepStatus_Success ||
          status == OrthancPluginJobStepStatus_Failure)
      {
        state_.reset();
      }

      return status;
    }
  }

  
  void StatefulOrthancJob::Stop(OrthancPluginJobStopReason reason)
  {
    if (state_.get() != NULL)
    {
      state_->Stop(reason);

      if (reason != OrthancPluginJobStopReason_Paused)
      {
        // Drop the current state, so as to force going back to the
        // initial state on resubmit
        state_.reset();
      }
    }
  }

  
  void StatefulOrthancJob::Reset()
  {
    if (state_.get() != NULL)
    {
      // Error in the Orthanc core: Reset() should only be called
      // from the "Failure" state, where no "IState*" is available
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }
}
