# How to Design Unit

## Design Properties

- Add the name and properties of you unit to `Unit.PROPERTIES` in `units.py`.

## Design Image

- Draw a PNG image for your unit with size `TILE_SIZE x TILE_SIZE` (default: 32 x 32) and color Red.
- Name the image as `assets/unit/{UNIT}_0.png`.
- Run `generate_blue_from_red.py` to generate image `{UNIT}_1.png`.
- (Optional) To avoid libpng warning, run this on Bash:
    ```
    sudo apt-get install pngcrush
    cd $(pwd) && find . -type f -iname '*.png' -exec pngcrush -ow -rem allb -reduce {} \;
    ```