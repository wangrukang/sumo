#!/usr/bin/env python
# Eclipse SUMO, Simulation of Urban MObility; see https://eclipse.org/sumo
# Copyright (C) 2011-2018 German Aerospace Center (DLR) and others.
# This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v2.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v20.html
# SPDX-License-Identifier: EPL-2.0

# @file    timing.py
# @author  Michael Behrisch
# @date    2018-11-30
# @version $Id: history.py f2df2bd45d evamarie.wiessner@dlr.de 2018-06-29 14:14:14 +0200 $

"""
This script uses either a directory with historic sumo versions
or git bisect to compare performance of differnt sumo versions.
"""
from __future__ import absolute_import
from __future__ import print_function

import subprocess
import argparse
import os
import sys
import collections
import numpy


def build():
    sumoSubdir = False
    if os.path.exists(os.path.join("sumo", "src", "sumo_main.cpp")):
        os.chdir("sumo")
        sumoSubdir = True
    subprocess.check_call(["make", "-j"])
    if sumoSubdir:
        os.chdir("..")
        return "sumo"
    return ""

def runHistory(args, versions, extraInfo=""):
    results = collections.defaultdict(list)
    for d in versions:
        try:
            for _ in xrange(args.runs):
                for l in subprocess.check_output(['/usr/bin/time', '-v', os.path.join(d, 'bin', 'sumo'), "-v", "-c", args.cfg], stderr=subprocess.STDOUT).splitlines():
                    if "User time" in l:
                        t = float(l.split(": ")[-1])
                    elif "wall clock" in l:
                        w = float(l.split(":")[-1])
                    elif "UPS: " in l:
                        u = 1e6 / max(1., float(l.split(": ")[-1]))
                    elif "Maximum resident" in l:
                        m = float(l.split(": ")[-1])
                results[d].append((u, t))
        except subprocess.CalledProcessError as e:
            if len(versions) == 1:
                raise
            else:
                print(e, file=sys.stderr)
                continue
    with open(args.stats, "a") as out:
        for d, r in sorted(results.items()):
            r = sorted(r)[:args.runs - args.skip]
            print(d, extraInfo, " ".join(map(str, numpy.mean(r, 0))), file=out)
    return numpy.mean(r, 0)[0]


argparser = argparse.ArgumentParser()
argparser.add_argument("cfg", help="sumo config to run")
argparser.add_argument("--versions", nargs="*", help="sumo versions to run")
argparser.add_argument("--stats", help="stats file to write")
argparser.add_argument("--basedir", default="buildHistory", help="where to find the version subdirs")
argparser.add_argument("--bisect", type=float, help="run git bisect with the given threshold value")
argparser.add_argument("--runs", type=int, default=5, help="number of runs for each version")
argparser.add_argument("--skip", type=int, default=2, help="number of worst runs to skip for each version")
args = argparser.parse_args()
if args.stats is None:
    args.stats = os.path.dirname(args.cfg) + ".stats"
if args.skip >= args.runs:
    args.skip = args.runs // 2
    print("Skipping too many runs, reducing skip to %s." % args.skip, file=sys.stderr)
if args.versions:
    versions = args.versions
else:
    versions = [os.path.join(args.basedir, v) for v in os.listdir(args.basedir)]
if args.bisect:
    versions = [build()]

if args.bisect:
    try:
        time = runHistory(args, versions, subprocess.check_output(["git", "describe", "--always"]).strip())
    except subprocess.CalledProcessError as e:
        print(e, file=sys.stderr)
        sys.exit(125)   # an exit code of 125 asks "git bisect" to "skip" the current commit
#    subprocess.call(["git", "reset", "--hard"])  # to allow bisect to continue even when there are local modifications
    sys.exit(0 if time < args.bisect else 1)
else:
    runHistory(args, versions)
