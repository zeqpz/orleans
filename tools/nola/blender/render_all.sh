#!/bin/sh
# Build + render every fall symbol in background Blenders, 5 at a time. usage: sh tools/nola/blender/render_all.sh [IDs..]
B="/c/Users/CooperHinkel/Blender/blender-5.2.3-windows-x64/blender.exe"
cd "$(dirname "$0")/../../.."
IDS=${*:-"H1 H2 H3 H4 H5 H6 H7 L1 L2 L3 L4 L5 L6 L7 L8 L9 L10 M BS ES"}
echo $IDS | tr ' ' '\n' | xargs -P 5 -I{} sh -c "\"$B\" -b --factory-startup --python tools/nola/blender/symanim.py -- {} > art/blender/renders/{}.log 2>&1; grep -h -E 'DONE|Error' art/blender/renders/{}.log | head -2"
