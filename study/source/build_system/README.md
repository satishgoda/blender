
```
 git checkout main
 git pull upstream main
 make update
 git checkout study
 git remote -v
 git rebase main
 git checkout main
 git push public
 git checkout study
 git rebase main
 git push --force
```

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