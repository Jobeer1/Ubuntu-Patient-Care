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


#include "MySQLParameters.h"

#include "MySQLDatabase.h"

#include <Logging.h>
#include <OrthancException.h>

namespace OrthancDatabases
{
  void MySQLParameters::Reset()
  {
    host_ = "localhost";
    username_.clear();
    password_.clear();
    database_.clear();
    port_ = 3306;

#if defined(_WIN32)
    unixSocket_.clear();
#else
    unixSocket_ = "/var/run/mysqld/mysqld.sock";
#endif
    
    lock_ = true;
  }

  
  MySQLParameters::MySQLParameters() :
    ssl_(false),
    verifySslServerCertificates_(true),
    maxConnectionRetries_(10),
    connectionRetryInterval_(5)
  {
    Reset();
  }


  MySQLParameters::MySQLParameters(const OrthancPlugins::OrthancConfiguration& pluginConfiguration,
                                   const OrthancPlugins::OrthancConfiguration& orthancConfiguration)
  {
    Reset();

    std::string s;
    if (pluginConfiguration.LookupStringValue(s, "Host"))
    {
      SetHost(s);
    }

    if (pluginConfiguration.LookupStringValue(s, "Username"))
    {
      SetUsername(s);
    }

    if (pluginConfiguration.LookupStringValue(s, "Password"))
    {
      SetPassword(s);
    }

    if (pluginConfiguration.LookupStringValue(s, "Database"))
    {
      SetDatabase(s);
    }

    unsigned int port;
    if (pluginConfiguration.LookupUnsignedIntegerValue(port, "Port"))
    {
      SetPort(port);
    }

    if (pluginConfiguration.LookupStringValue(s, "UnixSocket"))
    {
      SetUnixSocket(s);
    }

    lock_ = pluginConfiguration.GetBooleanValue("Lock", true);  // Use locking by default

    ssl_ = pluginConfiguration.GetBooleanValue("EnableSsl", false);
    verifySslServerCertificates_ = pluginConfiguration.GetBooleanValue("SslVerifyServerCertificates", true);

    const std::string defaultCaCertificates = orthancConfiguration.GetStringValue("HttpsCACertificates", "");
    sslCaCertificates_ = pluginConfiguration.GetStringValue("SslCACertificates", defaultCaCertificates);

    if (ssl_ && verifySslServerCertificates_ && sslCaCertificates_.empty())
    {
      LOG(ERROR) << "MySQL: No SslCACertificates defined, unable to check SSL Server certificates";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    maxConnectionRetries_ = pluginConfiguration.GetUnsignedIntegerValue("MaximumConnectionRetries", 10);
    connectionRetryInterval_ = pluginConfiguration.GetUnsignedIntegerValue("ConnectionRetryInterval", 5);
  }


  void MySQLParameters::SetHost(const std::string& host)
  {
    host_ = host;
  }

  
  void MySQLParameters::SetUsername(const std::string& username)
  {
    username_ = username;
  }

  
  void MySQLParameters::SetPassword(const std::string& password)
  {
    password_ = password;
  }

  
  void MySQLParameters::SetDatabase(const std::string& database)
  {
    if (database.empty())
    {
      LOG(ERROR) << "MySQL: Empty database name";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    
    if (!MySQLDatabase::IsValidDatabaseIdentifier(database))
    {
      LOG(ERROR) << "MySQL: Only alphanumeric characters are allowed in a "
                 << "database name: \"" << database << "\"";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);          
    }
    
    database_ = database;
  }

  
  void MySQLParameters::SetPort(unsigned int port)
  {
    if (port >= 65535)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      port_ = port;
    }
  }

  
  void MySQLParameters::SetUnixSocket(const std::string& socket)
  {
#if defined(_WIN32)
    if (!socket.empty())
    {
      LOG(WARNING) << "MySQL: Setting an UNIX socket on Windows has no effect";
    }
#endif
    
    unixSocket_ = socket;
  }

  
  void MySQLParameters::Format(Json::Value& target) const
  {
    target = Json::objectValue;
    target["Host"] = host_;
    target["Username"] = username_;
    target["Password"] = password_;
    target["Database"] = database_;
    target["Port"] = port_;
    target["UnixSocket"] = unixSocket_;
    target["Lock"] = lock_;
  }
}
