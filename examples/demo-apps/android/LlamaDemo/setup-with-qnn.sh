#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

set -eu

if [ -z "$QNN_SDK_ROOT" ]; then
  echo "You must specify QNN_SDK_ROOT"
  exit 1
fi

BASEDIR=$(dirname "$0")
source "$BASEDIR"/../../../../build/build_android_library.sh

BUILD_AAR_DIR="$(mktemp -d)"
export BUILD_AAR_DIR

build_jar
build_android_native_library "arm64-v8a"
build_aar
mkdir -p "$BASEDIR"/app/libs
cp "$BUILD_AAR_DIR/executorch.aar" "$BASEDIR"/app/libs/executorch.aar
