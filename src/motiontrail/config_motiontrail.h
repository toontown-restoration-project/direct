// Filename: config_motiontrail.h
// Created by:  drose (27Aug02)
//
////////////////////////////////////////////////////////////////////
//
// PANDA 3D SOFTWARE
// Copyright (c) Carnegie Mellon University.  All rights reserved.
//
// All use of this software is subject to the terms of the revised BSD
// license.  You should have received a copy of this license along
// with this source code in a file named "LICENSE."
//
////////////////////////////////////////////////////////////////////

#ifndef CONFIG_MOTIONTRAIL_H
#define CONFIG_MOTIONTRAIL_H

#include "directbase.h"
#include "notifyCategoryProxy.h"
#include "dconfig.h"

#include "cMotionTrail.h"

NotifyCategoryDecl(motiontrail, EXPCL_DIRECT, EXPTP_DIRECT);

extern EXPCL_DIRECT void init_libmotiontrail();

#endif
