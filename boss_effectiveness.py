"""Small, positive boss/tool relationships shared by every damage path.

Bosses still own *when* a hit can land.  This table only changes the size of an
accepted mark, so a poor tool can always finish a fight through learned openings.
The stable saved weapon IDs also identify shots after their owner switches tools.
"""
from __future__ import annotations

from dataclasses import dataclass


WEAPON_FAMILIES = {
    "pencil_blade": "cut",
    "ink_pistol": "precision",
    "marker_shotgun": "spread",
    "eraser_cannon": "erase",
    "rubber_band": "ricochet",
    "excalibur": "heroic",
    "margin_maul": "heavy",
    "carbon_lance": "precision",
    "folded_shuriken": "returning",
    "chalk_bomb": "blast",
}

# All values are intentionally modest: reading the boss and reaching its
# opening matters more than selecting a tool. Unknown tools remain normal.
BOSS_WEAPON_EFFECTIVENESS = {
    "moon_compass": {"returning": 1.40, "heavy": 1.30, "precision": .70, "erase": .85},
    "wanted_sketch": {"precision": 1.35, "returning": 1.20, "spread": .65, "heavy": .80},
    "railroad_stapler": {"heavy": 1.40, "erase": 1.25, "blast": 1.20, "precision": .75, "cut": .80},
    "orbital_mistake": {"erase": 1.40, "ricochet": 1.25, "cut": .70, "spread": .80},
    "scissor_director": {"precision": 1.35, "returning": 1.20, "heavy": .75, "spread": .80},
    "final_editor": {"heavy": 1.35, "returning": 1.25, "ricochet": .75, "spread": .85},
    "boss": {"erase": 1.35, "heavy": 1.20, "precision": .75},
    "compass": {"heavy": 1.30, "returning": 1.25, "precision": .75},
    "stapler": {"erase": 1.30, "blast": 1.25, "spread": .75},
    "failed_sketch": {"erase": 1.30, "returning": 1.20, "precision": .75},
    "artist_mistake": {"erase": 1.35, "heroic": 1.20, "cut": .75},
}

_DAMAGE_FAMILIES = {
    "ink": "precision", "marker": "spread", "eraser": "erase",
    "rubber_band": "ricochet", "chalk_bomb": "blast", "excalibur": "heroic",
    "maul_finisher": "heavy", "ion_wave": "cut",
}


@dataclass(frozen=True)
class Effectiveness:
    multiplier: float = 1.0
    label: str = "normal"
    family: str = "unknown"


def weapon_family(weapon_id=None, damage_kind=None, tags=None):
    if weapon_id in WEAPON_FAMILIES:
        return WEAPON_FAMILIES[weapon_id]
    tags = set(tags or ())
    for tag in tags:
        if tag.startswith("weapon:"):
            family = WEAPON_FAMILIES.get(tag.partition(":")[2])
            if family:
                return family
    kinds = [damage_kind] if damage_kind else []
    kinds.extend(sorted(tags))
    for kind in kinds:
        if kind in _DAMAGE_FAMILIES:
            return _DAMAGE_FAMILIES[kind]
        if kind.startswith(("pencil", "katana_", "bowie_", "field_", "ion_edge", "redraw")):
            return "cut"
    return "unknown"


def effectiveness_for(enemy, weapon_id=None, damage_kind=None, tags=None):
    family = weapon_family(weapon_id, damage_kind, tags)
    kind = getattr(enemy, "kind", str(enemy) if isinstance(enemy, str) else "")
    is_boss = isinstance(enemy, str) or getattr(enemy, "is_boss", False) or kind == "boss"
    multiplier = BOSS_WEAPON_EFFECTIVENESS.get(kind, {}).get(family, 1.0) if is_boss else 1.0
    # A malformed future entry must never turn a weapon into an immunity.
    multiplier = max(.25, min(1.75, float(multiplier)))
    label = "strong" if multiplier > 1.05 else "weak" if multiplier < .95 else "normal"
    return Effectiveness(multiplier, label, family)


def boss_damage(amount, enemy, tags=None):
    """Scale an accepted hit once, after the boss has tested its opening."""
    tags = set(tags or ())
    # Direct enemy APIs also serve arena scripts and legacy practice tools.
    # Only a real, identified combat tool invokes the material relationship.
    multiplier = (effectiveness_for(enemy, tags=tags).multiplier
                  if any(tag.startswith("weapon:") for tag in tags) else 1.0)
    return max(0.0, float(amount)) * multiplier
