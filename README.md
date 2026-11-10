# tinyecs-compsys-sdl2

`tinyecs.compsys.sdl2` provides systems and components dealing with the
`pygame-ce` SDL2 rendering backend. It covers topics around textures,
sprites, \...

## Synopsis

This package relies on registered component IDs from
`tinyecs-compsys-base`. It should not be used standalone, but instead be
automatically detected and registered with the top level
`tinyecs.compsys` package.

``` python
import tinyecs.compsys as cs

cs.register()
```

## Installation

It\'s up to you, if you install the currently provided `compsys`
packages from `tinyecs` by using

``` console
pip install tinyecs[base,sdl2]
```

or include them by adding specific dependencies:

``` console
pip install tinyecs
pip install tinyecs-compsys
pip install tinyecs-compsys-base
pip install tinyecs-compsys-sdl2
```

## Support / Contributing

Issues can be opened on [github
issues](https://github.com/dickerdackel/tinyecs-compsys-sdl2/issues)

## License

This software is provided under the MIT license.

See LICENSE file for details.
