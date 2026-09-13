from collections.abc import Sequence
from dataclasses import dataclass

import glm
import pygame
import pygame._sdl2 as sdl2
import tinyecs as ecs

from aenum import extend_enum
from glm import vec2
from pgcooldown import LerpThing
from tinyecs import EntityID, EntityComponentsBundle
from tinyecs.compsys import Comp
from tinyecs.compsys.dynamics import PRSA


type Vector = pygame.Vector2 | glm.vec2 | Sequence[float]

extend_enum(Comp, 'CONTAINER')
extend_enum(Comp, 'GRAVITY')
extend_enum(Comp, 'LIFETIME')
extend_enum(Comp, 'SPLINE')
extend_enum(Comp, 'SPRITE')
extend_enum(Comp, 'SPRITE_ANIM')
extend_enum(Comp, 'TARGET')
extend_enum(Comp, 'TINT')
extend_enum(Comp, 'TINT_COLOR')
extend_enum(Comp, 'TINT_SPRITE')
extend_enum(Comp, 'WORLD')

use_radians = True


class TSprite:
    def __init__(self,
                 texture: sdl2.Texture,
                 srcrect: pygame.Rect,
                 scale: float = 1.0,
                 angle: float = 0.0,
                 anchor: vec2 | None = None,
                 flip_x: bool = False,
                 flip_y: bool = False,
                 layer: int = 0):
        """A sprite based on an sdl2 Texture.

        :param texture: The actual texture
        :param srcrect: The source coordinates on the texture, assuming it's an atlas
        :param scale: The base scale of the sprite.  This is the basis that
            scaling during renering will be applie to self.texture = texture
        :param angle: The base angle of the sprite, e.g. the direction it's on the sprite sheet.
        :param anchor: The pivot point, defaults to center
        :param flip_x: Sprite must be flipped horizontally
        :param flip_y: Sprite must be flipped vertically
        :param layer: An optional sprite layer

        """
        self.texture = texture
        self.srcrect = srcrect
        self.scale = scale

        if scale != 1:
            self.dstrect = self.srcrect.scale_by(scale).move_to(topleft=(0, 0))
        else:
            self.dstrect = srcrect.move_to(topleft=(0, 0))

        if isinstance(anchor, str):
            self.anchor = vec2(getattr(self.dstrect, anchor))
        else:
            self.anchor = anchor

        self.flip_x = flip_x
        self.flip_y = flip_y
        self.angle = angle

        self.layer = layer

    def __iter__(self):
        yield 'texture', self.texture
        yield 'srcrect', self.srcrect
        yield 'scale', self.scale
        yield 'angle', self.angle
        yield 'anchor', self.anchor
        yield 'flip_x', self.flip_x
        yield 'flip_y', self.flip_y

    def __replace__(self, /, **kwargs):
        """Clone the sprite while also changing parameters.

        .. note:: Except ``texture`` and ``srcrect``, the argument list is the
            same as instantiating a :class:`TSprite`.
        """
        existing = dict(self)
        existing.update(kwargs)
        return TSprite(**existing)

    def __repr__(self):
        return f'TSprite({self.texture}, srcrect={self.srcrect}, dstrect={self.dstrect}, anchor={self.anchor}, layer={self.layer}, flip_x={self.flip_x}, flip_y={self.flip_y})'


@dataclass
class SpriteAnim:
    """A component holding a sprite animation.

    :param anim: A list of TSprite instances
    :param timer: A LerpThing to control the sprite switching

    """
    anim: list[TSprite]
    timer: LerpThing


def sys_bounce(eid: EntityID, prsa: PRSA, sprite: TSprite, momentum: Vector, world: pygame.Rect) -> None:
    """Bounce the sprite within the given container.

    """

    rect = sprite.dstrect.move_to(center=prsa.pos)
    if prsa.scale != 1:
        rect.scale_by_ip(prsa.scale)

    if rect.left < world.left:
        rect.left = world.left - rect.left
        momentum.x = -momentum.x
    elif rect.right > world.right:
        rect.right = 2 * world.right - rect.right
        momentum.x = -momentum.x
    if rect.top < world.top:
        rect.top = world.top - rect.top
        momentum.y = -momentum.y
    elif rect.bottom > world.bottom:
        rect.bottom = 2 * world.bottom - rect.bottom
        momentum.y = -momentum.y


def sys_container(eid: EntityID, prsa: PRSA, container: pygame.Rect) -> None:
    """Kill the entity if it has left the given boundaries.

    :param eid: The entity ID

    """

    if not container.collidepoint(prsa.pos):
        ecs.add_component(eid, Comp.IS_KILLED, True)


def _draw_sprite(sprite: TSprite, prsa: PRSA) -> None:
    """Draw a sprite transformed and positioned by the PRSA.

    :param sprite: The TSprite component holding the texture
    :param prsa: The PRSA transform object of the entity

    The sprite is positioned relative to its center.  The optional ``anchor``
    attribute in the sprite is honored and used as offset to the center.
    """

    texture = sprite.texture

    bkp_alpha = texture.alpha
    texture.alpha = prsa.alpha

    anchor = sprite.anchor or sprite.dstrect.center
    dstrect = sprite.dstrect.move_to(center=glm.round(prsa.pos + sprite.dstrect.center - anchor))

    if prsa.scale != 1:
        dstrect.scale_by_ip(prsa.scale)

    angle = prsa.rotation + sprite.angle
    if use_radians:
        angle = glm.degrees(angle)

    texture.draw(srcrect=sprite.srcrect,
                 dstrect=dstrect,
                 angle=angle,
                 origin=sprite.anchor,
                 flip_x=sprite.flip_x,
                 flip_y=sprite.flip_y)
    print(f'draw {texture} at {dstrect}')

    texture.alpha = bkp_alpha


def sys_bulk_draw_sprites(entities: EntityComponentsBundle, *, layered=False):
    """Bulk-draw sprites transformed and positioned by the PRSA.

    :param eid: A list of ``tinyecs.EntityComponentsBundle`` to loop over
    :param layered: Flag if the ``layer`` attribute in the sprite should be honored

    """

    if layered:
        sprites = sorted(entities, key=lambda e: e[1].layer)
    else:
        sprites = entities

    for eid, sprite, prsa in sprites:
        _draw_sprite(sprite, prsa)


def sys_draw_sprite(eid: EntityID, sprite: TSprite, prsa: PRSA) -> None:
    """Draw a sprite transformed and positioned by the PRSA.

    :param eid: The entity ID
    :param sprite: The TSprite component holding the texture
    :param prsa: The PRSA transform object of the entity

    """

    _draw_sprite(sprite, prsa)


def sys_sprite_anim(eid: EntityID, sprite_anim: SpriteAnim) -> None:
    """Based on the timer in ``anim``, update ``sprite``.

    :param eid: The entity ID
    :param sprite_anim: The sprite animation

    """

    if sprite_anim.timer.finished():
        sprite = sprite_anim.anim[-1]
    else:
        sprite = sprite_anim.anim[int(sprite_anim.timer)]
    ecs.update_component(eid, Comp.SPRITE, sprite)


def sys_mouse(eid: EntityID, prsa: PRSA, *, mouse: Vector) -> None:
    """Apply the mouse position to the PRSA.

    :param eid: The entity ID
    :param prsa: The PRSA transform object of the entity
    :param mouse: The current mouse position

    .. note: The mouse position must be provided as kwarg when running this system.
    """

    prsa.pos = vec2(mouse)
