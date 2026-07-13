import streamlit as st
from character import Character
from dice import roll
from combat import CombatEngine
from Poisons import POISON_DB, get_venomblade_scaling, MASTERWORK
import json
import os

st.set_page_config(layout="wide", page_title="Mute Companion")

if 'mute' not in st.session_state:
    st.session_state.mute = Character()

mute = st.session_state.mute
if "current_hp" not in mute.data:
    mute.load_data()
    
# Clean structured dictionary call
venom_stats = get_venomblade_scaling(mute.level)

# Initialize Session States
if 'my_init' not in st.session_state: st.session_state.my_init = 0
if 'last_roll' not in st.session_state: st.session_state.last_roll = "None"
if 'roll_history' not in st.session_state: st.session_state.roll_history = []
if 'stroke_used' not in st.session_state: st.session_state.stroke_used = False
if 'coated_poison' not in st.session_state: st.session_state.coated_poison = None

def update_hp(amount):
    if amount < 0:
        damage = abs(amount)
        if mute.data["temp_hp"] > 0:
            if damage <= mute.data["temp_hp"]: 
                mute.data["temp_hp"] -= damage
                damage = 0
            else: 
                damage -= mute.data["temp_hp"]
                mute.data["temp_hp"] = 0
        mute.data["current_hp"] = max(0, mute.data["current_hp"] - damage)
    else:
        mute.data["current_hp"] = min(mute.hp_max, mute.data["current_hp"] + amount)

def add_roll_to_history(roll_text):
    st.session_state.last_roll = roll_text
    st.session_state.roll_history.append(roll_text)
    if len(st.session_state.roll_history) > 20:
        st.session_state.roll_history.pop(0)

with st.sidebar:
    st.header("⚙️ Character Engine")
    
    if st.button("💾 SAVE CHARACTER STATE", use_container_width=True, type="primary"):
        mute.save_data()
        st.success("State saved to disk!")
        
    st.metric("Character Level", mute.level)
    
    if st.button("🔼 Level Up Mute", use_container_width=True):
        mute.level_up() 
        st.session_state.mute = Character() 
        st.rerun() 
        
    asi_points = mute.data.get("asi_points", 0)
    if asi_points > 0:
        st.warning(f"🌟 You have {asi_points} Ability Score points to spend!")
        for stat, score in mute.stats.items():
            if st.button(f"+1 {stat} (Current: {score})", key=f"asi_{stat}", use_container_width=True):
                mute.increase_stat(stat)
                st.session_state.mute = Character()
                st.rerun()

    with st.expander("📊 Core Stats", expanded=True):
        name = st.text_input("Name", value=mute.data.get("name", "Mute"))
        species = st.text_input("Species", value=mute.data.get("species", "Changeling"))
        class_info = st.text_input("Class", value=mute.data.get("class_info", "Venomblade Rogue"))
        if name != mute.data.get("name") or species != mute.data.get("species") or class_info != mute.data.get("class_info"):
            mute.data["name"] = name
            mute.data["species"] = species
            mute.data["class_info"] = class_info
            mute.save_data()

        stats_str = " | ".join([f"{k}: {v} ({mute.get_mod(k):+})" for k, v in mute.stats.items()])
        st.markdown(f"**Stats:** {stats_str}")
        st.metric("Proficiency Bonus", f"+{mute.proficiency_bonus}")
        
        ac_val = st.number_input("Armor Class (AC)", value=mute.data.get("ac", 12 + mute.get_mod("DEX")), min_value=0)
        mute.data["ac"] = ac_val
        speed_val = st.number_input("Speed (ft)", value=mute.data.get("speed", 30), step=5)
        mute.data["speed"] = speed_val
        
        st.markdown("**Tool Proficiencies:**")
        tools = mute.data.get("tool_proficiencies", {})
        st.write(", ".join([f"{t} (Expert)" if lvl==2 else t for t, lvl in tools.items()]) if tools else "None")

        mastery_options = ["Dagger", "Shortsword", "Scimitar", "Rapier", "Shortbow", "Hand Crossbow", "Sickle"]
        current_mastery = mute.data.get("mastered_weapons", [])
        if mute.level >= 1:
            new_mastery = st.multiselect("Weapon Mastery (Pick 2)", mastery_options, default=current_mastery)
            if new_mastery != current_mastery:
                mute.data["mastered_weapons"] = new_mastery
                mute.save_data()

        st.divider()
        st.markdown("💰 **Coins**")
        col_g, col_s, col_c = st.columns(3)
        gp = col_g.number_input("GP", value=mute.data.get("gp", 0), step=1)
        sp = col_s.number_input("SP", value=mute.data.get("sp", 0), step=1)
        cp = col_c.number_input("CP", value=mute.data.get("cp", 0), step=1)
        if gp != mute.data.get("gp", 0) or sp != mute.data.get("sp", 0) or cp != mute.data.get("cp", 0):
            mute.data["gp"], mute.data["sp"], mute.data["cp"] = gp, sp, cp
            mute.save_data()

    st.divider()

    st.markdown("### ⚡ Initiative")
    col_init_roll, col_init_score = st.columns([2, 1])
    init_mod = mute.get_mod('DEX') + 2 
    if col_init_roll.button(f"🎲 Roll Init (+{init_mod})", use_container_width=True):
        res = roll(f"1d20+{init_mod}")
        st.session_state.my_init = res
        add_roll_to_history(f"**Initiative:** Rolled {res}")
    col_init_score.metric("Score", st.session_state.my_init)

    with st.expander("🔄 Alert Swap"):
        ally_init = st.number_input("Ally's Initiative", value=0, step=1)
        if st.button("Swap Initiative", use_container_width=True):
            st.session_state.my_init = ally_init
            st.success(f"Swapped! New Init: {ally_init}")
            st.rerun()

    st.divider()
    st.markdown("### 🩸 Health & Conditions")
    
    hp_percent = mute.data["current_hp"] / mute.hp_max
    st.progress(hp_percent, text=f"HP: {mute.data['current_hp']} / {mute.hp_max}")
    st.metric("Temp HP", mute.data["temp_hp"])
    
    h1, h2 = st.columns(2)
    if h1.button("➖ Dmg", use_container_width=True): update_hp(-1); st.rerun()
    if h2.button("➕ Heal", use_container_width=True): update_hp(1); st.rerun()
    
    new_thp = st.number_input("Set Temp HP", min_value=0, step=1, value=mute.data.get("temp_hp", 0))
    if new_thp != mute.data.get("temp_hp", 0):
        mute.data["temp_hp"] = new_thp
        st.rerun()

    all_conditions = ["Blinded", "Charmed", "Deafened", "Frightened", "Grappled", "Incapacitated", "Invisible", "Paralyzed", "Petrified", "Poisoned", "Prone", "Restrained", "Stunned", "Unconscious"]
    mute.data["conditions"] = st.multiselect("Active Conditions", all_conditions, default=mute.data.get("conditions", []))
    mute.data["concentrating"] = st.checkbox("🧠 Concentrating?", value=mute.data.get("concentrating", False))
    if st.button("Update Condition State"): mute.save_data(); st.rerun()

    st.divider()
    
    st.markdown("### ⛺ Rest Center")
    available_hit_dice = mute.level - mute.data["hit_dice_spent"]
    c1, c2 = st.columns(2)
    if c1.button(f"🩹 Spend 1 Hit Die ({available_hit_dice} left)", use_container_width=True) and available_hit_dice > 0:
        mute.data["hit_dice_spent"] += 1
        recovered = roll(f"1d8+{mute.get_mod('CON')}")
        update_hp(recovered)
        add_roll_to_history(f"Hit Die Spent: Recovered {recovered} HP")
        st.rerun()
    if c2.button("🛌 Spend ALL Hit Dice", use_container_width=True, disabled=(available_hit_dice == 0)):
        total_recovered = 0
        for _ in range(available_hit_dice):
            recovered = roll(f"1d8+{mute.get_mod('CON')}")
            update_hp(recovered)
            total_recovered += recovered
            mute.data["hit_dice_spent"] += 1
        add_roll_to_history(f"Short Rest: Spent all dice, recovered {total_recovered} total HP")
        st.rerun()
        
    if st.button("🌅 Take Long Rest", use_container_width=True):
        mute.data["current_hp"] = mute.hp_max
        mute.data["hit_dice_spent"] = 0
        mute.data["temp_hp"] = 0
        st.session_state.stroke_used = False
        st.session_state.coated_poison = None
        mute.save_data()
        st.rerun()

    st.divider()
    st.markdown("### 👁️ Passive Senses")
    col_perc, col_ins, col_inv = st.columns(3)
    col_perc.metric("Perception", 10 + mute.get_skill_mod("Perception"))
    col_ins.metric("Insight", 10 + mute.get_skill_mod("Insight"))
    col_inv.metric("Investigation", 10 + mute.get_skill_mod("Investigation"))

    st.divider()
    st.download_button(
        label="📥 Download Character JSON",
        data=json.dumps(mute.data, indent=4),
        file_name="character.json",
        mime="application/json",
        use_container_width=True
    )
    
    uploaded_file = st.file_uploader("📂 Upload Character JSON", type="json")
    if uploaded_file is not None:
        try:
            uploaded_content = json.load(uploaded_file)
            mute.data = uploaded_content
            mute.stats = uploaded_content.get("base_stats", {})
            mute.level = uploaded_content.get("level", 3)
            mute.save_data()
            st.success("Character loaded from upload! Refreshing...")
            st.rerun()
        except Exception as e:
            st.error(f"Error loading file: {e}")

    with st.expander("🎚️ Checks & Saves"):
        for stat in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            mod = mute.get_mod(stat)
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"**{stat}** ({mod:+})")
            if col2.button("🎲", key=f"check_{stat}"):
                res = roll("1d20")
                add_roll_to_history(f"**{stat} Check:** Rolled {res} ({mod:+}) = **{res+mod}**")
                st.rerun()
        st.divider()
        for stat in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            mod = mute.get_save_mod(stat)
            mark = "✦ " if stat in ["DEX", "INT"] or (mute.level >= 15 and stat in ["WIS", "CHA"]) else ""
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"**{mark}{stat} Save** ({mod:+})")
            if col2.button("🎲", key=f"save_{stat}"):
                res = roll("1d20")
                add_roll_to_history(f"**{stat} Save:** Rolled {res} ({mod:+}) = **{res+mod}**")
                st.rerun()

    with st.expander("🤹 Skills"):
        if mute.level >= 9:
            st.markdown("**Subtle Application** (Adv. Venom Techniques)")
            if st.button("🎲 Poison Object/Food (Sleight of Hand)", use_container_width=True):
                r1, r2 = roll("1d20"), roll("1d20")
                final_r = max(r1, r2)
                mod = mute.get_skill_mod("Sleight of Hand")
                add_roll_to_history(f"**Subtle Application:** Rolled {r1} & {r2}, kept {final_r} ({mod:+}) = **{final_r+mod}**")
                st.rerun()
            st.divider()
            
        for skill, stat in mute.SKILL_ATTRIBUTES.items():
            mod = mute.get_skill_mod(skill)
            prof_level = mute.data.get("skills", {}).get(skill, 0)
            mark = "✦✦ " if prof_level == 2 else ("✦ " if prof_level == 1 else "")
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"{mark}{skill} ({mod:+})")
            if col2.button("🎲", key=f"skill_{skill}"):
                res = roll("1d20")
                if mute.level >= 7 and prof_level > 0 and res < 10:
                    add_roll_to_history(f"**{skill}:** Rolled {res} ➔ *Reliable Talent (10)* ({mod:+}) = **{10+mod}**")
                else:
                    add_roll_to_history(f"**{skill}:** Rolled {res} ({mod:+}) = **{res+mod}**")
                st.rerun()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "⚔️ Combat", "🧪 Alchemy", "📖 Journal", "📜 Features", "📜 Roll History", "🗺️ Cartography & Influence"
])

with tab1:
    st.header("Combat Dashboard")
    
    action_col, react_col = st.columns(2)
    with action_col:
        st.markdown("**Bonus Actions**")
        if mute.level >= 2: st.checkbox("Cunning Action (Dash/Disengage/Hide)")
        steady_aim = False
        if mute.level >= 3: steady_aim = st.toggle("🎯 Steady Aim (Advantage, Speed 0)")
    with react_col:
        st.markdown("**Reactions & Epics**")
        if mute.level >= 5 and st.button("🛡️ Uncanny Dodge (Halve Damage)"):
            st.toast("Used Reaction to halve incoming damage!")
        if mute.level >= 20 and not st.session_state.stroke_used:
            if st.button("🍀 Stroke of Luck (Turn Miss into 20)"):
                st.session_state.stroke_used = True
                st.toast("Rolled a 20! Feature consumed until Rest.")
                st.rerun()

    st.divider()

    st.markdown("### 🎯 Attack Rolls")
    has_advantage = st.toggle("🟢 Roll with Advantage (Hidden, Flanking, etc.)")
    is_adv = steady_aim or has_advantage

    hit_melee_col, hit_cross_col = st.columns(2)
    with hit_melee_col:
        if st.button(f"🎯 Melee To Hit (+{mute.to_hit_mod})", use_container_width=True):
            atk, log = CombatEngine.resolve_attack(mute.to_hit_mod, is_adv)
            add_roll_to_history(f"Melee Attack: AC **{atk}** hit! {log}")
            st.rerun()
            
    with hit_cross_col:
        if st.button(f"🎯 Crossbow To Hit (+{mute.to_hit_mod})", use_container_width=True):
            if mute.data["bolts"] > 0:
                mute.data["bolts"] -= 1
                mute.save_data()
                atk, log = CombatEngine.resolve_attack(mute.to_hit_mod, is_adv)
                add_roll_to_history(f"Crossbow Attack: AC **{atk}** hit! {log} | Ammo expended.")
            else:
                add_roll_to_history("Out of ammunition!")
            st.rerun()

    if st.session_state.last_roll != "None":
        st.info(f"🔔 {st.session_state.last_roll}")

    st.divider()

    st.markdown("### 🧪 Healing (Bonus Action)")
    
    available_potions = {k: v for k, v in mute.data["healing_potions"].items() if v > 0}
    
    if available_potions:
        potion_choice = st.selectbox("Select Potion to Drink:", list(available_potions.keys()))
        heal_dice = {
            "Healing": "2d4+2", "Greater Healing": "4d4+4",
            "Superior Healing": "8d4+8", "Supreme Healing": "10d4+20"
        }
        if st.button(f"🧪 Drink {potion_choice} ({heal_dice[potion_choice]})", use_container_width=True):
            healed = roll(heal_dice[potion_choice])
            update_hp(healed)
            mute.data["healing_potions"][potion_choice] -= 1
            mute.save_data()
            add_roll_to_history(f"🩸 Drank {potion_choice}, recovered **{healed}** HP.")
            st.rerun()
    else:
        st.caption("No healing potions in satchel. Manage them in the **Journal** tab.")

    st.divider()

    st.markdown("### 🧪 Weapon Coating (Bonus Action)")
    
    if st.session_state.coated_poison:
        p_data = POISON_DB[st.session_state.coated_poison]
        st.success(f"{p_data['icon']} Your weapon is coated with: **{st.session_state.coated_poison}**")
        if st.button("Wipe Weapon Clean (Discard Poison)"):
            st.session_state.coated_poison = None
            st.rerun()
    else:
        combat_poisons = {p: c for p, c in mute.data.get("prepared_poisons", {}).items() if c > 0 and p in POISON_DB and POISON_DB[p]["delivery"] == "Weapon"}
        if combat_poisons:
            poison_options = [f"{p} ({c} doses)" for p, c in combat_poisons.items()]
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                chosen_coating_str = st.selectbox("Select a combat poison from satchel:", poison_options, label_visibility="collapsed")
            with col_btn:
                if st.button("Apply to Weapon", use_container_width=True):
                    p_name = chosen_coating_str.rsplit(" (", 1)[0]
                    st.session_state.coated_poison = p_name
                    mute.data["prepared_poisons"][p_name] -= 1
                    mute.save_data()
                    st.rerun()
        else:
            st.caption("No combat poisons currently prepared. Brew some in the Alchemy tab!")

    st.divider()

    cunning_costs = 0
    if mute.level >= 5:
        st.markdown("### 🐍 Cunning Strikes")
        available_strikes = {"Poison": 1, "Trip": 1, "Withdraw": 1}
        if mute.level >= 14:
            available_strikes.update({"Daze": 2, "Obscure": 3, "Knock Out": 6})
        
        chosen_strikes = st.multiselect(f"Select Cunning Strikes (DC {mute.poison_dc})", list(available_strikes.keys()))
        cunning_costs = sum([available_strikes[s] for s in chosen_strikes])
        
        if mute.level < 11 and len(chosen_strikes) > 1:
            st.error("You can only apply 1 Cunning Strike effect until Level 11.")
            cunning_costs = 99
        elif mute.level >= 11 and len(chosen_strikes) > 2:
            st.error("Improved Cunning Strike allows a maximum of 2 effects.")
            cunning_costs = 99
        elif cunning_costs > mute.sneak_attack_dice:
            st.error(f"Cannot afford effects: Cost is {cunning_costs}d6, you only have {mute.sneak_attack_dice}d6 Sneak Attack.")

    is_target_poisoned = False
    if mute.level >= 9:
        is_target_poisoned = st.checkbox("Target is currently Poisoned (Advanced Venom Techniques)")

    combat_col1, combat_col2 = st.columns(2)
    
    with combat_col1:
        st.markdown("### ⚔️ Melee Damage")
        if st.button(f"🗡️ Dagger Damage (1d4+{mute.damage_mod})", use_container_width=True):
            dmg = CombatEngine.resolve_weapon_damage("1d4", mute.damage_mod)
            log = f"🩸 **Dagger Damage:** {dmg} Piercing"
            
            if st.session_state.coated_poison:
                p_data = POISON_DB[st.session_state.coated_poison]
                tox_dice = "4d6" if p_data["type"] == MASTERWORK else venom_stats["combat_damage"]
                tox_dmg = CombatEngine.resolve_poison_damage(tox_dice)
                
                log += f" | {p_data['icon']} **{st.session_state.coated_poison}:** {tox_dmg} {p_data['damage_type']} Dmg (DC {mute.poison_dc} {p_data['save']})"
                st.session_state.coated_poison = None 
                
            add_roll_to_history(log)
            st.rerun()
            
        if st.button("👊 Unarmed Strike Damage", use_container_width=True):
            add_roll_to_history(f"🩸 **Damage:** {mute.get_mod('STR')} Bludgeoning")
            st.rerun()

    with combat_col2:
        st.markdown("### 🏹 Ranged & Modifiers")
        xb_tracker_col, xb_add_col, xb_sub_col = st.columns([2, 0.5, 0.5])
        with xb_tracker_col:
            st.markdown(f"**🔩 Ammunition:** `{mute.data['bolts']}` Bolts")
        with xb_add_col:
            if st.button("➕", key="add_b"): 
                mute.data["bolts"] += 1
                st.rerun()
        with xb_sub_col:
            if st.button("➖", key="sub_b"): 
                mute.data["bolts"] = max(0, mute.data["bolts"] - 1)
                st.rerun()

        if st.button(f"🏹 Crossbow Damage (1d8+{mute.damage_mod})", use_container_width=True):
            dmg = CombatEngine.resolve_weapon_damage("1d8", mute.damage_mod)
            log = f"🩸 **Crossbow Damage:** {dmg} Piercing"
            
            if st.session_state.coated_poison:
                p_data = POISON_DB[st.session_state.coated_poison]
                tox_dice = "4d6" if p_data["type"] == MASTERWORK else venom_stats["combat_damage"]
                tox_dmg = CombatEngine.resolve_poison_damage(tox_dice)
                
                log += f" | {p_data['icon']} **{st.session_state.coated_poison}:** {tox_dmg} {p_data['damage_type']} Dmg (DC {mute.poison_dc} {p_data['save']})"
                st.session_state.coated_poison = None 
                
            add_roll_to_history(log)
            st.rerun()
            
        net_sneak_dice = mute.sneak_attack_dice - (cunning_costs if cunning_costs != 99 else 0)
        sa_label = f"🩸 Roll Sneak Attack ({net_sneak_dice}d6)" if net_sneak_dice > 0 else "🩸 Sneak Attack (Dice Consumed by Strikes)"
        
        if st.button(sa_label, use_container_width=True, disabled=(cunning_costs == 99)):
            log = CombatEngine.resolve_sneak_attack(
                total_dice=mute.sneak_attack_dice, 
                cunning_cost=cunning_costs, 
                is_poisoned=is_target_poisoned, 
                avt_dice_str=venom_stats["adv_damage"]
            )
            add_roll_to_history(log)
            st.rerun()

with tab2:
    st.header("Venomcraft & Alchemy")
    
    max_reagents_cap = max(2, mute.proficiency_bonus + mute.get_mod("INT"))
    
    st.markdown(f"### 🧪 Toxic Harvest (Max Cap: {max_reagents_cap})")
    harv_col1, harv_col2, harv_col3 = st.columns([2, 1, 1])
    with harv_col1:
        nature_mod = mute.get_skill_mod("Nature")
        pk_prof = mute.data.get("tool_proficiencies", {}).get("Poisoner's Kit", 0)
        pk_mod = mute.get_mod("DEX") + (mute.proficiency_bonus * pk_prof) 
        harvest_mod = max(nature_mod, pk_mod)
        
        if st.button(f"🎲 Forage for Reagents (+{harvest_mod})", use_container_width=True):
            base_r = roll("1d20")
            total = base_r + harvest_mod
            gained = 2 if total >= 17 else (1 if total >= 12 else 0)
            
            old_reag = mute.data.get("reagents", 0)
            mute.data["reagents"] = min(max_reagents_cap, mute.data.get("reagents", 0) + gained)
            mute.save_data()
            add_roll_to_history(f"Harvest Roll: {total} ({base_r} + {harvest_mod}). Recovered {mute.data['reagents'] - old_reag} reagents!")
            st.rerun()
    
    with harv_col2:
        if st.button("➖ Spend Reagent") and mute.data.get("reagents", 0) > 0:
            mute.data["reagents"] -= 1
            st.rerun()
    with harv_col3:
        if st.button("➕ Buy Reagent (10gp)") and mute.data.get("reagents", 0) < max_reagents_cap:
            mute.data["reagents"] += 1
            st.rerun()
            
    st.metric("Current Toxic Reagents", f'{mute.data.get("reagents", 0)} / {max_reagents_cap}')
    st.divider()
            
    st.subheader("Brew Formulas")
    valid_poisons = {k: v for k, v in POISON_DB.items() if mute.level >= v["min_level"]}
    selected_formula = st.selectbox("Select Formula:", list(valid_poisons.keys()))
    
    p_data = valid_poisons[selected_formula]
    reagent_cost = 2 if p_data["type"] == MASTERWORK else 1
    
    with st.container(border=True):
        st.markdown(f"#### {p_data['icon']} {selected_formula}")
        st.caption(f"*{p_data['flavour']}*")
        st.markdown(f"**Tier:** {p_data['rarity']} | **Delivery:** {p_data['delivery']} | **Save:** {p_data['save']} | **Duration:** {p_data['duration']}")
        st.markdown(f"**Effect:** {p_data['effect']}")
        
        for upgrade_level, upgrade_text in p_data.get("upgrades", {}).items():
            if mute.level >= upgrade_level:
                st.markdown(f"**Level {upgrade_level} Upgrade:** {upgrade_text}")
    
    if st.button(f"🔥 Brew Formula (Cost: {reagent_cost})"):
        if mute.data.get("reagents", 0) < reagent_cost:
            st.error(f"Requires {reagent_cost} Toxic Reagents!")
        else:
            current_poisons = mute.data.get("prepared_poisons", {})
            
            if p_data["type"] == MASTERWORK:
                for existing_p, existing_c in list(current_poisons.items()):
                    if existing_p in POISON_DB and POISON_DB[existing_p]["type"] == MASTERWORK:
                        del current_poisons[existing_p]
                        st.warning(f"Removed old Masterwork ({existing_p}) to make room for the new one.")
            else:
                if sum(current_poisons.values()) >= venom_stats["prepared"]:
                    st.error(f"Satchel full (Max {venom_stats['prepared']} doses).")
                    st.stop()

            mute.data["reagents"] -= reagent_cost
            current_poisons[selected_formula] = current_poisons.get(selected_formula, 0) + 1
            mute.data["prepared_poisons"] = current_poisons
            mute.save_data()
            st.rerun()
            
    st.divider()
    st.subheader(f"Prepared Satchel (Max: {venom_stats['prepared']})")
    for p_name, count in list(mute.data.get("prepared_poisons", {}).items()):
        if count > 0 and p_name in POISON_DB:
            p_cache = POISON_DB[p_name]
            is_masterwork = " 💎" if p_cache["type"] == MASTERWORK else ""
            col_p1, col_p2 = st.columns([3, 1])
            col_p1.write(f"{p_cache['icon']} **{p_name}**{is_masterwork} (`{count}` doses)")
            if col_p2.button("Discard Dose", key=f"discard_{p_name}"):
                mute.data["prepared_poisons"][p_name] -= 1
                mute.save_data()
                st.rerun()

with tab3:
    st.header("📝 Notes & Inventory")
    chalk = st.text_input("Chalkboard:")
    if chalk: st.markdown(f"### 🗣️ *{chalk}*")

    st.subheader("🧪 Potion Satchel")
    potion_tiers = {
        "Healing": "2d4 + 2", "Greater Healing": "4d4 + 4",
        "Superior Healing": "8d4 + 8", "Supreme Healing": "10d4 + 20"
    }
    
    col_pot_add, col_pot_del = st.columns(2)
    potion_to_manage = col_pot_add.selectbox("Manage Potion Tier:", list(potion_tiers.keys()))
    if col_pot_add.button("➕ Add Potion"):
        mute.data["healing_potions"][potion_to_manage] = mute.data["healing_potions"].get(potion_to_manage, 0) + 1
        mute.save_data()
        st.rerun()
    if col_pot_del.button("➖ Remove Potion") and mute.data["healing_potions"].get(potion_to_manage, 0) > 0:
        mute.data["healing_potions"][potion_to_manage] -= 1
        mute.save_data()
        st.rerun()
        
    st.caption("Current Stock:")
    for p, qty in mute.data["healing_potions"].items():
        if qty > 0:
            st.write(f"- **{p}** ({qty} doses, heals {potion_tiers[p]})")
    st.divider()

    i_col, n_col = st.columns(2)
    current_inv = "\n".join([f"• {item}" if not item.startswith("•") else item for item in mute.data.get("inventory", [])])
    updated_inv = i_col.text_area("Inventory", current_inv, height=400)
    updated_notes = n_col.text_area("Notes", mute.data.get("notes", ""), height=400)

    if st.button("💾 Save Journal & Inventory", use_container_width=True):
        clean_inv = [line.strip().lstrip("• ") for line in updated_inv.split("\n") if line.strip()]
        mute.data["inventory"] = clean_inv
        mute.data["notes"] = updated_notes
        mute.save_data()
        st.success("Changes saved permanently to character.json!")

with tab4:
    st.header("📜 Active Class Features")
    st.caption(f"Displaying features unlocked up to Rogue Level {mute.level}.")
    
    feature_progression = {
        1: ["**Expertise:** Double proficiency bonus on two chosen skills.", f"**Sneak Attack ({mute.sneak_attack_dice}d6):** Extra damage once per turn with Advantage or an adjacent ally.", "**Weapon Mastery:** Utilize mastery properties of two weapon types.", "**Thieves' Cant:** You know Thieves' Cant and one other language of your choice."],
        2: ["**Cunning Action:** Dash, Disengage, or Hide as a Bonus Action."],
        3: ["**Steady Aim:** Bonus Action to gain Advantage on next attack (Speed becomes 0).", "🧪 **Refined Chemistry (Venomblade):** Venomblade poisons ignore poison resistance.", "🧪 **Toxic Harvest (Venomblade):** Harvest reagents from toxic enemies/environments.", f"🧪 **Venomcraft (Venomblade):** Brew and apply combat/utility poisons (DC {mute.poison_dc})."],
        5: [f"**Cunning Strike (DC {mute.poison_dc}):** Forgo Sneak Attack dice to Poison, Trip, or Withdraw.", "**Uncanny Dodge:** Use your Reaction to halve an attacker's damage against you."],
        6: ["**Expertise:** Double proficiency bonus on two additional skills."],
        7: ["**Evasion:** Take no damage on successful Dex saves (half on failure).", "**Reliable Talent:** Treat any d20 roll of 9 or lower as a 10 for proficient skills."],
        9: [f"🧪 **Advanced Venom Techniques (Venomblade):** +{venom_stats['adv_damage']} extra damage to poisoned targets. Advantage to sleight-of-hand poisons."],
        11: ["**Improved Cunning Strike:** You can use up to two Cunning Strike effects at once."],
        13: ["🧪 **Master of Venoms (Venomblade):** Ignore poison immunity (treat as resistance). Gain resistance to poison damage and advantage on poison saves."],
        14: ["**Devious Strikes:** Cunning strike options expand to Daze, Knock Out, and Obscure."],
        15: ["**Slippery Mind:** Gain proficiency in Wisdom and Charisma saving throws."],
        17: ["🧪 **Magnum Opus (Venomblade):** Brew legendary Masterwork Toxins (Vitriolic Marrow-Bane, Arcane-Severing Neurotoxin, Lethe-Water Elixir)."],
        18: ["**Elusive:** No attack roll can have Advantage against you unless you are Incapacitated."],
        19: ["**Epic Boon:** You gain an Epic Boon feat or another feat of your choice for which you qualify."],
        20: ["**Stroke of Luck:** Turn any failed d20 test into a 20 (Once per Short/Long Rest)."]
    }
    
    for lvl in range(1, mute.level + 1):
        if lvl in feature_progression:
            with st.expander(f"Level {lvl} Features", expanded=(lvl == mute.level)):
                for feature in feature_progression[lvl]:
                    st.markdown(f"- {feature}")

with tab5:
    st.header("📜 Roll History")
    st.caption("Last 20 rolls (chronological).")
    for i, log in enumerate(reversed(st.session_state.roll_history)):
        st.text(f"{len(st.session_state.roll_history) - i}. {log}")

with tab6:
    st.markdown(
        """
        <div style="background-color:#1e1e2e; padding:15px; border-radius:10px; border-left: 5px solid #ff5555; margin-bottom:20px;">
            <h2 style="color:#ffffff; margin:0;">🗺️ City-State Influence & Cartography Ledger</h2>
            <p style="color:#a6adc8; margin:5px 0 0 0; font-size:14px;">Track Mute's political sway, faction dynamic standings, and safe house sectors across the ruins.</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    col_fac, col_loc = st.columns([1, 1], gap="large")
    
    # ==========================================
    # LEFT COLUMN: FACTION STANDING THEATRE
    # ==========================================
    with col_fac:
        st.markdown("### 🏛️ Faction Network & Allegiances")
        
        factions = mute.data.get("factions", {})
        
        for f_name, f_info in factions.items():
            standing = f_info.get("standing", 0)
            norm_val = float((standing + 20) / 40)
            color = f_info.get("color", "#ff5555")
            
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 18px; font-weight: bold; color: {color};">⚔️ {f_name}</span>
                        <span style="background-color: {color}22; color: {color}; padding: 3px 10px; border-radius: 12px; font-size: 12px; border: 1px solid {color}55; font-weight: bold;">
                            {f_info.get('tier', 'Neutral').upper()}
                        </span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                st.progress(norm_val, text=f"Dynamic Standing: {standing:+}")
                
                with st.expander("📝 Intelligence Notes & Adjustment", expanded=False):
                    b_sub, b_add = st.columns(2)
                    if b_sub.button(f"📉 Decrease {f_name} (-1)", use_container_width=True):
                        f_info["standing"] = max(-20, standing - 1)
                        if f_info["standing"] <= -10: f_info["tier"] = "Hostile"
                        elif f_info["standing"] <= -4: f_info["tier"] = "Wary"
                        elif f_info["standing"] <= 4: f_info["tier"] = "Neutral"
                        elif f_info["standing"] <= 10: f_info["tier"] = "Trusted"
                        else: f_info["tier"] = "Allied"
                        mute.save_data()
                        st.rerun()
                        
                    if b_add.button(f"📈 Increase {f_name} (+1)", use_container_width=True):
                        f_info["standing"] = min(20, standing + 1)
                        if f_info["standing"] <= -10: f_info["tier"] = "Hostile"
                        elif f_info["standing"] <= -4: f_info["tier"] = "Wary"
                        elif f_info["standing"] <= 4: f_info["tier"] = "Neutral"
                        elif f_info["standing"] <= 10: f_info["tier"] = "Trusted"
                        else: f_info["tier"] = "Allied"
                        mute.save_data()
                        st.rerun()
                    
                    updated_f_notes = st.text_area("Field Intelligence:", value=f_info.get("notes", ""), key=f"notes_{f_name}")
                    if updated_f_notes != f_info.get("notes", ""):
                        f_info["notes"] = updated_f_notes
                        mute.save_data()
    
    # ==========================================
    # RIGHT COLUMN: LOCATION CARDS & COMPASS
    # ==========================================
    with col_loc:
        st.markdown("### 📍 Location Registry & Safehouses")
        
        loc_list = mute.data.get("locations", [])
        total_discovered = len(loc_list)
        visited_count = sum(1 for l in loc_list if l.get("Visited", False))
        
        stat_c1, stat_c2 = st.columns(2)
        stat_c1.metric("Discovered Zones", total_discovered)
        stat_c2.metric("Sectors Inspected", f"{visited_count} / {total_discovered}")
        st.divider()
        
        search_query = st.text_input("🔍 Filter Sector Database...", "").lower()
        
        for idx, loc in enumerate(loc_list):
            if search_query and search_query not in loc.get("Name", "").lower() and search_query not in loc.get("Controller", "").lower():
                continue
                
            danger = loc.get("Danger", "Low")
            danger_colors = {"Low": "#2E7D32", "Medium": "#F57C00", "High": "#D32F2F", "Extreme": "#7B1FA2"}
            d_color = danger_colors.get(danger, "#7f8c8d")
            
            with st.container(border=True):
                v_status = "🟢 Visited" if loc.get("Visited", False) else "⚪ Unexplored"
                current_controller = loc.get('Controller', 'Unknown')
                
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <strong style="font-size: 16px; color:#ffffff;">📍 {loc.get('Name', 'Unknown')}</strong>
                        <span style="font-size: 12px; color: {d_color}; font-weight: bold; background-color: {d_color}22; padding: 2px 8px; border-radius: 4px; border: 1px solid {d_color}44;">
                            {danger} Danger
                        </span>
                    </div>
                    <div style="font-size: 13px; margin-bottom: 8px;">
                        <span style="color:#a6adc8;">Controlled by:</span> <span style="color:#f5c2e7; font-weight:600;">{current_controller}</span>
                        <span style="margin-left: 15px; color:#a6adc8;">Status:</span> <span style="color:#f9e2af;">{v_status}</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                with st.expander("🛠️ Re-route Info / Inspect Notes", expanded=False):
                    is_visited = st.checkbox("Sector Marked Visited", value=loc.get("Visited", False), key=f"vis_check_{idx}")
                    
                    c1, c2 = st.columns(2)
                    new_danger = c1.selectbox("Update Threat Matrix:", ["Low", "Medium", "High", "Extreme"], index=["Low", "Medium", "High", "Extreme"].index(danger), key=f"dang_sel_{idx}")
                    
                    # --- DYNAMIC CONTROLLER DROPDOWN ---
                    known_controllers = set(mute.data.get("factions", {}).keys())
                    for l in loc_list: 
                        known_controllers.add(l.get("Controller", "Unknown"))
                    known_controllers.update(["Unknown", "Unaligned", "Monsters", "Faithful"])
                    ctrl_options = sorted(list(known_controllers)) + ["➕ Add New..."]
                    
                    new_ctrl_selection = c2.selectbox(
                        "Faction in Control:", 
                        ctrl_options, 
                        index=ctrl_options.index(current_controller) if current_controller in ctrl_options else 0, 
                        key=f"ctrl_sel_{idx}"
                    )
                    
                    final_ctrl = new_ctrl_selection
                    if new_ctrl_selection == "➕ Add New...":
                        final_ctrl = st.text_input("Enter New Faction/Controller:", key=f"new_ctrl_txt_{idx}")
                        if not final_ctrl: 
                            final_ctrl = current_controller

                    updated_l_notes = st.text_area("Logbook Entries:", value=loc.get("Notes", ""), key=f"loc_notes_{idx}")
                    
                    # If anything changes, save and rerun to update the UI badge immediately
                    if (is_visited != loc.get("Visited", False) or 
                        new_danger != danger or 
                        updated_l_notes != loc.get("Notes", "") or 
                        (final_ctrl != current_controller and final_ctrl != "➕ Add New...")):
                        
                        loc["Visited"] = is_visited
                        loc["Danger"] = new_danger
                        loc["Notes"] = updated_l_notes
                        loc["Controller"] = final_ctrl
                        mute.save_data()
                        st.rerun()
                        
        st.markdown("---")
        with st.expander("➕ Chart Unmapped Sector Location"):
            with st.form("add_location_form", clear_on_submit=True):
                nl_name = st.text_input("Zone Name:")
                nl_danger = st.selectbox("Danger Severity Matrix:", ["Low", "Medium", "High", "Extreme"])
                
                form_controllers = set(mute.data.get("factions", {}).keys())
                for l in loc_list: form_controllers.add(l.get("Controller", "Unknown"))
                form_controllers.update(["Unknown", "Unaligned", "Monsters", "Faithful"])
                form_options = sorted(list(form_controllers)) + ["➕ Add New..."]
                
                nl_control_sel = st.selectbox("Faction in Control:", form_options, index=form_options.index("Unaligned") if "Unaligned" in form_options else 0)
                nl_control_custom = st.text_input("If 'Add New...', specify here:")
                
                nl_notes = st.text_area("Initial Survey Reports / Recon:")
                
                if st.form_submit_button("💾 Commit Blueprint to Archive"):
                    if nl_name:
                        final_nl_control = nl_control_custom if nl_control_sel == "➕ Add New..." and nl_control_custom else (nl_control_sel if nl_control_sel != "➕ Add New..." else "Unknown")
                        new_entry = {
                            "Name": nl_name,
                            "Danger": nl_danger,
                            "Controller": final_nl_control,
                            "Visited": True,
                            "Notes": nl_notes
                        }
                        mute.data.setdefault("locations", []).append(new_entry)
                        mute.save_data()
                        st.toast(f"Sector mapped successfully: {nl_name}")
                        st.rerun()