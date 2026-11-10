from collections.abc import MutableSequence, Sequence
from dataclasses import dataclass

import glm
import pygame
import pygame._sdl2 as sdl2
import tinyecs as ecs

from aenum import extend_enum
from glm import vec2
from pgcooldown import LerpThing
from tinyecs import EntityID
from tinyecs.compsys import Comp
from tinyecs.compsys.dynamics import PRSA


type Vector = pygame.Vector2 | glm.vec2 | Sequence[float]
type MVector = pygame.Vector2 | glm.vec2 | MutableSequence[float]

extend_enum(Comp, 'CONTAINER')
extend_enum(Comp, 'GRAVITY')
extend_enum(Comp, 'SPLINE')
extend_enum(Comp, 'SPRITE')
extend_enum(Comp, 'SPRITE_ANIM')
extend_enum(Comp, 'TARGET')
extend_enum(Comp, 'TINT')
extend_enum(Comp, 'TINT_COLOR')
extend_enum(Comp, 'TINT_SPRITE')
extend_enum(Comp, 'WANTS_MOUSE')
extend_enum(Comp, 'WORLD')

use_radians = False


class TSprite:
    def __init__(self,
                 texture: sdl2.Texture,
                 srcrect: pygame.Rect,
                 scale: float = 1.0,
                 angle: float = 0.0,
                 anchor: vec2 | str | None = 'center',
                 flip_x: bool = False,
                 flip_y: bool = False,
                 layer: int = 0):
        """A sprite based on an sdl2 Texture.

        :param texture: The actual texture
        :param srcrect: The source coordinates on the texture, assuming it's an atlas
        :param scale: The base scale of the sprite.  This is the base scale that
            scaling during rendering will be applied to
        :param angle: The base angle of the sprite, e.g. the direction it's on the sprite sheet.
        :param anchor: The pivot point, defaults to 'center'.  See
            ``pygame.rect.Rect`` point attributes for possible values.
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
        yield 'layer', self.layer

    def __replace__(self, /, **kwargs):
        """Clone the sprite while also changing parameters.

        .. note:: The argument list is the same as instantiating a :class:`TSprite`.
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


def sys_bounce(eid: EntityID, prsa: PRSA, sprite: TSprite, momentum: MVector, world: pygame.Rect) -> None:
    """Bounce the sprite within the given world container.

    :param eid: The entity ID
    :param prsa: The PRSA transform object of the entity
    :param sprite: A TSprite component containing the texture and relating parameters
    :param momentum: The momentum of the entity
    :param world: A Rect describing the boundaries to bounce in

    """

    w_offset = -vec2(world.topleft)
    w_normalized = world.move_to(topleft=(0, 0))

    rect = sprite.dstrect.move_to(center=prsa.pos + w_offset)

    if prsa.scale != 1:
        rect.scale_by_ip(prsa.scale)

    initial_pos = vec2(rect.center)

    if rect.left < w_normalized.left:
        rect.left = w_normalized.left - rect.left
        momentum[0] = -momentum[0]
    elif rect.right > w_normalized.right:
        rect.right = 2 * w_normalized.right - rect.right
        momentum[0] = -momentum[0]
    if rect.top < w_normalized.top:
        rect.top = w_normalized.top - rect.top
        momentum[1] = -momentum[1]
    elif rect.bottom > w_normalized.bottom:
        rect.bottom = 2 * w_normalized.bottom - rect.bottom
        momentum[1] = -momentum[1]

    prsa.pos += vec2(rect.center) - initial_pos


def sys_container(eid: EntityID, prsa: PRSA, container: pygame.Rect) -> None:
    """Mark the entity as killed if its prsa.pos has left the given boundaries.

    :param eid: The entity ID
    :param prsa: The PRSA transform object of the entity
    :param container: If the entity leaves the container, it's marked as killed

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

    texture.alpha = bkp_alpha


def sys_bulk_draw_sprites(entities: list[tuple[EntityID, TSprite, PRSA]], *, layered=False):
    """Bulk-draw sprites transformed and positioned by the PRSA.

    :param entities: A list of ``(eid, sprite, prsa)`` tuples  to loop over
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
    """Based on the timer in ``sprite_anim``, update the ``sprite`` component.

    If the timer in ``sprite_anim`` is non-repeating, the last frame will be
    selected if the timer runs out.

    :param eid: The entity ID
    :param sprite_anim: The sprite animation component

    """

    if sprite_anim.timer.finished():
        sprite = sprite_anim.anim[-1]
    else:
        sprite = sprite_anim.anim[int(sprite_anim.timer)]
    ecs.update_component(eid, Comp.SPRITE, sprite)


def sys_mouse(eid: EntityID, prsa: PRSA, wants_mouse: bool, *, mouse: Vector) -> None:
    """Apply the mouse position to the PRSA.

    :param eid: The entity ID
    :param prsa: The PRSA transform object of the entity
    :param wants_mouse: The marker component that indicates that this entity
        receives the mouse position. The existence of this component alone is
        sufficient, its value is ignored
    :param mouse: The current mouse position

    .. note:: The mouse position must be provided as kwarg when running this system.
    """

    prsa.pos = vec2(mouse)
