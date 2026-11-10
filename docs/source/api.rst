tinyecs-compsys-sdl2 API
========================

.. contents::
   :class: this-will-duplicate-information-and-it-is-still-useful-here

Components
----------

Registers the following CIDs to ``tinyecs.compsys.Comp``:

* CONTAINER
* GRAVITY
* SPLINE
* SPRITE
* SPRITE_ANIM
* TARGET
* TINT
* TINT_COLOR
* TINT_SPRITE
* WANTS_MOUSE
* WORLD

.. autoclass:: tinyecs.compsys.sdl2.TSprite
   :class-doc-from: both
   :members:
   :special-members: __replace__


.. autoclass:: tinyecs.compsys.sdl2.SpriteAnim
   :members:


Systems
-------

.. autofunction:: tinyecs.compsys.sdl2.sys_bounce
.. autofunction:: tinyecs.compsys.sdl2.sys_container
.. autofunction:: tinyecs.compsys.sdl2.sys_bulk_draw_sprites
.. autofunction:: tinyecs.compsys.sdl2.sys_draw_sprite
.. autofunction:: tinyecs.compsys.sdl2.sys_sprite_anim
.. autofunction:: tinyecs.compsys.sdl2.sys_mouse
