# Constants for tight type-checking
COMBAT = "Combat"
UTILITY = "Utility"
MASTERWORK = "Masterwork"

WEAPON = "Weapon"
INGESTED = "Ingested"
INHALED = "Inhaled"
CONTACT = "Contact"

def get_venomblade_scaling(level):
    """Returns a structured dictionary of scaling stats based on Rogue level."""
    stats = {
        "prepared": 3, 
        "combat_damage": "1d6", 
        "adv_damage": "0d6"
    }
    
    if level >= 17:
        stats.update({"prepared": 9, "combat_damage": "4d6"})
    elif level >= 13:
        stats.update({"prepared": 7, "combat_damage": "3d6"})
    elif level >= 9:
        stats.update({"prepared": 5, "combat_damage": "2d6"})
        
    if level >= 13:
        stats["adv_damage"] = "2d6"
    elif level >= 9:
        stats["adv_damage"] = "1d6"
        
    return stats

POISON_DB = {
    "Adder's Kiss": {
        "icon": "🐍", "type": COMBAT, "rarity": "Common", "min_level": 3,
        "delivery": WEAPON, "damage": True, "damage_type": "Poison", "save": "CON", "duration": "1 round",
        "effect": "Target is Poisoned.",
        "flavour": "A clear venom that blackens veins within seconds.",
        "upgrades": {
            9: "The poisoned condition lasts for 1 minute (save ends at the end of each turn).",
            13: "The target has disadvantage on its first saving throw against this poison."
        }
    },
    "Crippling Venom": {
        "icon": "🩸", "type": COMBAT, "rarity": "Common", "min_level": 3,
        "delivery": WEAPON, "damage": True, "damage_type": "Poison", "save": "CON", "duration": "1 round",
        "effect": "Target's speed is reduced by 10 ft.",
        "flavour": "A thick, sludgy toxin that rapidly crystallizes in the bloodstream.",
        "upgrades": {
            9: "The effect lasts for 1 minute (save ends at the end of each turn).",
            13: "While its speed is reduced, the creature has disadvantage on Dexterity saving throws."
        }
    },
    "Nerve-Sever Toxin": {
        "icon": "⚡", "type": COMBAT, "rarity": "Uncommon", "min_level": 3,
        "delivery": WEAPON, "damage": True, "damage_type": "Poison", "save": "CON", "duration": "1 round",
        "effect": "Target cannot take reactions.",
        "flavour": "A paralytic agent targeting the motor cortex, causing immediate numbness.",
        "upgrades": {
            9: "The effect lasts until the end of the target's next turn.",
            13: "Opportunity attacks made by the target have disadvantage for 1 minute."
        }
    },
    "Hemotoxic Brew": {
        "icon": "❤️‍🔥", "type": COMBAT, "rarity": "Uncommon", "min_level": 3,
        "delivery": WEAPON, "damage": True, "damage_type": "Poison", "save": "CON", "duration": "1 round",
        "effect": "Target cannot regain hit points.",
        "flavour": "An aggressive anticoagulant that causes wounds to weep profusely.",
        "upgrades": {
            9: "The effect lasts for 1 minute (save ends at the end of each turn).",
            13: "On a failed save, the creature takes your Combat Poison damage again at the start of its next turn."
        }
    },
    "Black Lotus Extract": {
        "icon": "🪷", "type": COMBAT, "rarity": "Rare", "min_level": 9,
        "delivery": WEAPON, "damage": True, "damage_type": "Poison", "save": "CON", "duration": "1 minute",
        "effect": "Target is Poisoned and takes Combat Poison damage at the start of each of its turns.",
        "flavour": "Distilled from the rarest of subterranean blooms, it ravages the body from within.",
        "upgrades": {
            13: "The target has disadvantage on its first saving throw against this poison."
        }
    },
    "Drowsing Draught": {
        "icon": "💤", "type": UTILITY, "rarity": "Common", "min_level": 3,
        "delivery": INGESTED, "damage": False, "damage_type": None, "save": "CON", "duration": "1 minute",
        "effect": "Target falls unconscious.",
        "flavour": "A sweet-tasting syrup that mimics the exhaustion of a hard day's labor.",
        "upgrades": {
            9: "The unconsciousness is considered magical sleep.",
            13: "The creature has disadvantage on the initial saving throw."
        }
    },
    "Truth Sap": {
        "icon": "👁️", "type": UTILITY, "rarity": "Uncommon", "min_level": 3,
        "delivery": INGESTED, "damage": False, "damage_type": None, "save": "CON", "duration": "1 hour",
        "effect": "Target is Poisoned and has disadvantage on Deception.",
        "flavour": "A bitter resin that strips away the ego, leaving only a compulsive need to confess.",
        "upgrades": {
            9: "The creature also has disadvantage on Persuasion and Intimidation.",
            13: "When attempting to tell a lie, it must succeed on a CHA save or be unable to speak falsely."
        }
    },
    "Hallucinogenic Toxin": {
        "icon": "🌀", "type": UTILITY, "rarity": "Rare", "min_level": 3,
        "delivery": INHALED, "damage": False, "damage_type": None, "save": "CON", "duration": "1 hour",
        "effect": "Target is Poisoned, has disadvantage on INT/WIS checks, and speed -10 ft.",
        "flavour": "A fine powder that fragments reality into terrifying, kaleidoscopic shards.",
        "upgrades": {
            9: "The creature also has disadvantage on initiative rolls.",
            13: "On a failed initial save, the creature is incapacitated until the end of its next turn."
        }
    },
    "Silent Night Oil": {
        "icon": "🤫", "type": UTILITY, "rarity": "Uncommon", "min_level": 3,
        "delivery": CONTACT, "damage": False, "damage_type": None, "save": "CON", "duration": "1 hour",
        "effect": "Target is Poisoned and can speak only in a whisper.",
        "flavour": "A frictionless oil that coats the vocal cords, stealing the victim's voice.",
        "upgrades": {
            9: "The creature cannot cast spells with verbal components.",
            13: "The creature is also deafened for the duration."
        }
    },
    "Memorium Miasma": {
        "icon": "🌫️", "type": UTILITY, "rarity": "Rare", "min_level": 3,
        "delivery": INHALED, "damage": False, "damage_type": None, "save": "CON", "duration": "10 minutes",
        "effect": "Target is Poisoned, memory becomes hazy, disadvantage on recall checks. (10-ft cube).",
        "flavour": "A pale fog that washes over the mind like the tide over footprints in the sand.",
        "upgrades": {
            9: "The cube increases to a 15-foot area.",
            13: "Choose up to your INT modifier of creatures to automatically succeed the save."
        }
    },
    "Adhesive Resin": {
        "icon": "🕸️", "type": UTILITY, "rarity": "Common", "min_level": 3,
        "delivery": CONTACT, "damage": False, "damage_type": None, "save": "DEX", "duration": "1 minute",
        "effect": "Target's hands are restrained. (Requires DC 15 STR check to break).",
        "flavour": "An alchemical glue so powerful it can bind plate armor together.",
        "upgrades": {
            9: "The Strength check DC increases to 17.",
            13: "You can hurl this resin as a ranged weapon attack (range 20/60 feet)."
        }
    },
    "Vitriolic Marrow-Bane": {
        "icon": "🧪", "type": MASTERWORK, "rarity": "Legendary", "min_level": 17,
        "delivery": WEAPON, "damage": True, "damage_type": "Acid", "save": "CON", "duration": "1 minute",
        "effect": "Ignores immunity. Target's AC reduced by 3. Takes ongoing damage at start of turns.",
        "flavour": "A hyper-concentrated acid that boils bone to vapor in seconds.",
        "upgrades": {}
    },
    "Arcane-Severing Neurotoxin": {
        "icon": "🧠", "type": MASTERWORK, "rarity": "Legendary", "min_level": 17,
        "delivery": WEAPON, "damage": True, "damage_type": "Psychic", "save": "CON", "duration": "1 minute",
        "effect": "Ignores immunity. Spells require CON save to cast. Disadvantage on spell attacks.",
        "flavour": "A toxin designed to surgically unweave a mage's connection to the Weave.",
        "upgrades": {}
    },
    "Lethe-Water Elixir": {
        "icon": "🌊", "type": MASTERWORK, "rarity": "Legendary", "min_level": 17,
        "delivery": INGESTED, "damage": False, "damage_type": None, "save": "CON", "duration": "1 hour",
        "effect": "Ignores immunity. Target enters trance, answers truthfully. Modify Memory available.",
        "flavour": "The ultimate tool of the shadow apothecary; a drop that washes away a life.",
        "upgrades": {}
    }
}