
```
make update
```


```
make BUILD_DIR=/Users/sgoda/dev/b3d/blender_build \
     BUILD_CMAKE_ARGS="-DCMAKE_INSTALL_PREFIX=/Users/sgoda/dev/b3d/blender_build/install" \
     NPROCS=16 \
     ninja release
```