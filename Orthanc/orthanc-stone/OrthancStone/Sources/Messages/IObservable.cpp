/**
 * Stone of Orthanc
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this program. If not, see
 * <http://www.gnu.org/licenses/>.
 **/


#include "IObservable.h"

#include "../StoneException.h"

#include <Logging.h>

#include <cassert>
#include <stdexcept>

namespace OrthancStone 
{
  IObservable::~IObservable()
  {
    // delete all callables (this will also unregister them from the broker)
    for (Callables::const_iterator it = callables_.begin();
         it != callables_.end(); ++it)
    {
      for (std::set<ICallable*>::const_iterator
             it2 = it->second.begin(); it2 != it->second.end(); ++it2)
      {
        delete *it2;
      }
    }
  }
  

  void IObservable::RegisterCallable(ICallable* callable)
  {
    if (callable == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
    
    const MessageIdentifier& id = callable->GetMessageIdentifier();
    callables_[id].insert(callable);
  }

  void IObservable::EmitMessageInternal(const IObserver* receiver,
                                        const IMessage& message)
  {
    //LOG(TRACE) << "IObservable::EmitMessageInternal receiver = " << std::hex << receiver << std::dec;
    Callables::const_iterator found = callables_.find(message.GetIdentifier());

    if (found != callables_.end())
    {
      for (std::set<ICallable*>::const_iterator
             it = found->second.begin(); it != found->second.end(); ++it)
      {
        assert(*it != NULL);

        boost::shared_ptr<IObserver> observer((*it)->GetObserver().lock());

        if (observer)
        {
          if (receiver == NULL ||    // Are we broadcasting?
              observer.get() == receiver)  // Not broadcasting, but this is the receiver
          {
            try
            {
              // LOG(INFO) << "IN Handling message : " << message.GetIdentifier().AsString();
              (*it)->Apply(message);
              // LOG(INFO) << "OUT Handling message : " << message.GetIdentifier().AsString();
            }
            catch (Orthanc::OrthancException& e)
            {
              LOG(ERROR) << "OrthancException on callable: " << e.What() << " " << message.GetIdentifier().AsString();
            }
            catch (StoneException& e)
            {
              LOG(ERROR) << "StoneException on callable: " << e.What();
            }
            catch (std::exception& e)
            {
              LOG(ERROR) << "C++ exception on callable: " << e.what();
            }
            catch (...)
            {
              LOG(ERROR) << "Native exception on callable";
            }
          }
        }
        else
        {
          // TODO => Remove "it" from the list of callables => This
          // allows to suppress the need for "Unregister()"
        }
      }
    }
  }


  void IObservable::BroadcastMessage(const IMessage& message)
  {
    EmitMessageInternal(NULL, message);
  }

  
  void IObservable::EmitMessage(boost::weak_ptr<IObserver> observer,
                                const IMessage& message)
  {
    //LOG(TRACE) << "IObservable::EmitMessage observer = " << std::hex << observer.get() << std::dec;

    boost::shared_ptr<IObserver> lock(observer.lock());
    if (lock)
    {
      EmitMessageInternal(lock.get(), message);
    }
  }
}
