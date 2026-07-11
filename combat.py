from dice import roll

class CombatEngine:
    @staticmethod
    def resolve_attack(to_hit_mod, has_advantage=False):
        """Rolls an attack, handling advantage logic, and returns the result and log."""
        r1, r2 = roll("1d20"), roll("1d20")
        
        if has_advantage:
            final_r = max(r1, r2)
            log = f"(Advantage: Rolled {r1} & {r2}, kept {final_r})"
            return final_r + to_hit_mod, log
        else:
            return r1 + to_hit_mod, f"(Rolled {r1})"

    @staticmethod
    def resolve_weapon_damage(base_dice, damage_mod):
        """Standard weapon damage."""
        return roll(f"{base_dice}+{damage_mod}")

    @staticmethod
    def resolve_poison_damage(dice_str):
        """Rolls pure poison/toxin dice."""
        return roll(dice_str)

    @staticmethod
    def resolve_sneak_attack(total_dice, cunning_cost, is_poisoned, avt_dice_str):
        """Calculates final Sneak Attack output after Cunning Strike deductions."""
        net_dice = total_dice - cunning_cost
        log = ""
        
        if net_dice <= 0:
            log += "**Sneak Attack:** +0 Damage (Dice consumed by Cunning Strikes)"
        else:
            sa_dmg = roll(f"{net_dice}d6")
            log += f"**Sneak Attack:** +{sa_dmg} Damage"
            
        if is_poisoned and avt_dice_str != "0d6":
            avt_dmg = roll(avt_dice_str)
            log += f" | 🐍 **Adv. Venom Techniques:** +{avt_dmg} Poison Damage"
            
        return log