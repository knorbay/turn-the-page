"""Chapter tool variety follows actual cleared drawings, without a menu.

The first adaptive gift remains the close/distance complement to the starter.
These two later drawings expose different combat verbs before the last boss.
Ownership lives in the existing Artist gift save data; visiting a checkpoint
cannot refill an owned magazine or draw the same tool twice.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDelivery:
    after_clear: int
    weapon_id: str


CHAPTER_DELIVERIES = {
    0: (ToolDelivery(2, "fold_crossbow"), ToolDelivery(3, "margin_maul")),
    1: (ToolDelivery(2, "marker_shotgun"), ToolDelivery(3, "fold_crossbow")),
    2: (ToolDelivery(2, "eraser_cannon"), ToolDelivery(3, "orbit_saw")),
    3: (ToolDelivery(2, "carbon_lance"), ToolDelivery(3, "fold_crossbow")),
    4: (ToolDelivery(2, "orbit_saw"), ToolDelivery(3, "eraser_cannon")),
}


def next_delivery(page, arenas, player, weapons):
    """Return an earned drawing only after its room and beyond its exit.

    A finished room may include a boss (the Western page has two regular
    fights before its two bosses). The expedition's deliberate giant losses
    never count as a weapon reward. A late checkpoint keeps an earned drawing
    available, so walking past a narrow offer window cannot lose it forever.
    """
    if weapons is None or not weapons.unlocked or weapons.current_id == "unarmed":
        return None
    rooms = sorted((arena for arena in arenas if getattr(arena, "mandatory", False)
                    and arena.arena_id != "baby_face_interlude"),
                   key=lambda arena: arena.start_x)
    for delivery in CHAPTER_DELIVERIES.get(page, ()):
        if delivery.weapon_id in weapons.unlocked or len(rooms) < delivery.after_clear:
            continue
        predecessors = rooms[:delivery.after_clear]
        if (all(arena.completed for arena in predecessors)
                and player.center_x > predecessors[-1].end_x-80):
            return delivery.weapon_id
    return None
