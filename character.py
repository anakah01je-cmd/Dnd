import json
import os

class Character:
    # Maps skills to their governing ability score
    SKILL_ATTRIBUTES = {
        "Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT", 
        "Athletics": "STR", "Deception": "CHA", "History": "INT", 
        "Insight": "WIS", "Intimidation": "CHA", "Investigation": "INT", 
        "Medicine": "WIS", "Nature": "INT", "Perception": "WIS", 
        "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT", 
        "Sleight of Hand": "DEX", "Stealth": "DEX", "Survival": "WIS"
    }

    def __init__(self):
        # PORTABILITY FIX: Use relative path based on this file's location
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.filepath = os.path.join(self.base_dir, 'Data', 'character.json')
        
        # Automatically create the Data folder if it doesn't exist
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        
        self.load_data()

    def load_data(self):
        # If the file doesn't exist yet (fresh setup), create a blank default
        if not os.path.exists(self.filepath):
            self.data = {
                "name": "Mute",
                "level": 3,
                "species": "Changeling",
                "class_info": "Venomblade Rogue",
                "base_stats": {"STR": 8, "DEX": 16, "CON": 14, "INT": 9, "WIS": 14, "CHA": 15},
                "skills": {},
                "tool_proficiencies": {},
                "inventory": [],
                "notes": "",
                "current_hp": 0, "temp_hp": 0, "hit_dice_spent": 0,
                "bolts": 20, "reagents": 2, "prepared_poisons": {}, "conditions": [],
                "gp": 0, "sp": 0, "cp": 0, "mastered_weapons": [],
                "ac": 12, "speed": 30, "concentrating": False, "healing_potions": {}
            }
            self.stats = self.data["base_stats"]
            self.level = self.data["level"]
            self.save_data()
        else:
            with open(self.filepath, 'r') as f:
                self.data = json.load(f)
            self.stats = self.data.get("base_stats", {})
            self.level = self.data.get("level", 3)
        
        # Initialize persistent trackers if they don't exist in the JSON yet
        if "current_hp" not in self.data: self.data["current_hp"] = self.hp_max
        if "temp_hp" not in self.data: self.data["temp_hp"] = 0
        if "hit_dice_spent" not in self.data: self.data["hit_dice_spent"] = 0
        if "bolts" not in self.data: self.data["bolts"] = 20
        if "reagents" not in self.data: self.data["reagents"] = 2
        if "prepared_poisons" not in self.data: self.data["prepared_poisons"] = {}
        if "conditions" not in self.data: self.data["conditions"] = []
        if "gp" not in self.data: self.data["gp"] = 0
        if "sp" not in self.data: self.data["sp"] = 0
        if "cp" not in self.data: self.data["cp"] = 0
        if "mastered_weapons" not in self.data: self.data["mastered_weapons"] = []
        if "ac" not in self.data: self.data["ac"] = 12 + self.get_mod("DEX")
        if "speed" not in self.data: self.data["speed"] = 30
        if "concentrating" not in self.data: self.data["concentrating"] = False
        if "healing_potions" not in self.data:
            self.data["healing_potions"] = {
                "Healing": 0, "Greater Healing": 0, "Superior Healing": 0, "Supreme Healing": 0
            }

    def save_data(self):
        """Writes all current data states back to the JSON file to prevent data loss."""
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=4)
        if hasattr(os, 'sync'):
            os.sync()

    def get_mod(self, stat_name):
        return (self.stats.get(stat_name, 10) - 10) // 2

    @property
    def proficiency_bonus(self):
        return (self.level - 1) // 4 + 2

    @property
    def hp_max(self):
        con_mod = self.get_mod("CON")
        return 8 + ((self.level - 1) * 5) + (self.level * con_mod)

    @property
    def poison_dc(self):
        return 8 + self.proficiency_bonus + self.get_mod("DEX")

    @property
    def sneak_attack_dice(self):
        return (self.level + 1) // 2

    @property
    def to_hit_mod(self):
        return self.get_mod("DEX") + self.proficiency_bonus

    @property
    def damage_mod(self):
        return self.get_mod("DEX")

    @property
    def max_reagents(self):
        return max(2, self.proficiency_bonus + self.get_mod("INT"))

    def get_tool_mod(self, tool_name, ability="DEX"):
        mod = self.get_mod(ability)
        prof_level = self.data.get("tool_proficiencies", {}).get(tool_name, 0)
        return mod + (self.proficiency_bonus * prof_level)

    def get_save_mod(self, stat_name):
        mod = self.get_mod(stat_name)
        is_proficient = False
        if stat_name in ["DEX", "INT"]:
            is_proficient = True
        if self.level >= 15 and stat_name in ["WIS", "CHA"]:
            is_proficient = True
            
        if is_proficient:
            mod += self.proficiency_bonus
        return mod

    def get_skill_mod(self, skill_name):
        stat = self.SKILL_ATTRIBUTES.get(skill_name, "DEX")
        mod = self.get_mod(stat)
        prof_level = self.data.get("skills", {}).get(skill_name, 0) 
        return mod + (self.proficiency_bonus * prof_level)

    def level_up(self):
        self.level += 1
        self.data["level"] = self.level
        # Level 19 grants Epic Boon, not ASI (Removed 19 from this list)
        if self.level in [4, 8, 10, 12, 16]:
            self.data["asi_points"] = self.data.get("asi_points", 0) + 2
        
        self.data["current_hp"] = self.hp_max
        self.save_data()

    def increase_stat(self, stat_name):
        if self.data.get("asi_points", 0) > 0:
            self.data["base_stats"][stat_name] += 1
            self.data["asi_points"] -= 1
            self.save_data()
            self.load_data()