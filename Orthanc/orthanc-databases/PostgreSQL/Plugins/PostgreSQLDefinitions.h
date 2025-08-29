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

#include <stdint.h>


/**
 * This advisory lock is used if the "Lock" option is set to "true",
 * in order to prevent the execution of two PostgreSQL index plugins
 * on the same database.
 **/
static const int32_t POSTGRESQL_LOCK_INDEX = 42;


/**
 * This advisory lock is used if the "Lock" option is set to "true",
 * in order to prevent the execution of two PostgreSQL storage area
 * plugins on the same database.
 **/
static const int32_t POSTGRESQL_LOCK_STORAGE = 43;


/**
 * Transient advisory lock to protect the setup of the database,
 * because concurrent statements like "CREATE TABLE" are not protected
 * by transactions.
 * https://groups.google.com/d/msg/orthanc-users/yV3LSTh_TjI/h3PRApJFBAAJ
 **/
static const int32_t POSTGRESQL_LOCK_DATABASE_SETUP = 44;

/**
 * Transient advisory lock to protect the instance creation,
 * because it is not 100% resilient to concurrency in, e.g, READ COMIITED 
 * transaction isolation level.
 **/
static const int32_t POSTGRESQL_LOCK_CREATE_INSTANCE = 45;
