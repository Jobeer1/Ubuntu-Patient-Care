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

#include "Token.h"

#include <OrthancException.h>

namespace OrthancPlugins
{ 
  Token::Token(TokenType type,
               const std::string& key) :
    type_(type),
    key_(key)
  {
  }

  Token::Token(const Token& other) :
    type_(other.GetType()),
    key_(other.GetKey())
  {
  }

  bool Token::operator< (const Token &right) const
  {
    if (type_ != right.type_)
    {
      return type_ < right.type_;
    }
    else
    {
      return key_ < right.key_ ;
    }
  }
}
