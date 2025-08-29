/**
 * Advanced authorization plugin for Orthanc
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

#include "Enumerations.h"

namespace OrthancPlugins
{ 
  class Token
  {
  private:
    TokenType   type_;
    std::string key_;

  public:
    Token(TokenType type,
          const std::string& key);

    Token(const Token& other);

    TokenType GetType() const
    {
      return type_;
    }

    const std::string& GetKey() const
    {
      return key_;
    }

    // required to use this class in std::set
    bool operator< (const Token &right) const;
  };
}
