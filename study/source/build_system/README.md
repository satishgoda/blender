
```
make update
```


```
make BUILD_DIR=/Users/sgoda/dev/b3d/blender_build \
     BUILD_CMAKE_ARGS="-DCMAKE_INSTALL_PREFIX=/Users/sgoda/dev/b3d/blender_build/install" \
     NPROCS=16 \
     ninja release
```

```
PYTHONPATH=./.venv/lib/python3.11/site-packages WORKAREA_PATH=/Users/sgoda/Desktop/workarea51/ /Users/sgoda/dev/b3d/blender_build/install/Blender.app/Contents/MacOS/Blender --python-use-system-env
```