@echo off
wsl bash -c "cd $(pwd) && find . -type f -iname '*.png' -exec pngcrush -ow -rem allb -reduce {} \;"
pause