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
    
venom_stats = get_venomblade_scaling(mute.level)

# Initialize Session States
if 'my_init' not in st.session_state: st.session_state.my_init = 0
if 'last_roll' not in st.session_state: st.session_state.last_roll = "None"
if 'roll_history' not in st.session_state: st.session_state.roll_history = []
if 'stroke_used' not in st.session_state: st.session_state.stroke_used = False
if 'coated_poison' not in st.session_state: st.session_state.coated_poison = None
# Initiative tracker states
if 'combatants' not in st.session_state:
    st.session_state.combatants = []
if 'current_turn' not in st.session_state:
    st.session_state.current_turn = 0
if 'round_counter' not in st.session_state:
    st.session_state.round_counter = 1
if 'combat_pending_action' not in st.session_state:
    st.session_state.combat_pending_action = None
if 'combat_pending_target' not in st.session_state:
    st.session_state.combat_pending_target = None

# Process any pending Bonus/Reaction resets BEFORE the checkboxes below are
# instantiated this run. Streamlit forbids writing to st.session_state[key]
# for a widget that's already been created earlier in the *same* run, so
# this has to happen up-front rather than inside the button handlers.
if st.session_state.combat_pending_action == "next_turn":
    idx = st.session_state.combat_pending_target
    if idx is not None and 0 <= idx < len(st.session_state.combatants):
        st.session_state.combatants[idx]["bonus_used"] = False
        st.session_state.combatants[idx]["reaction_used"] = False
        st.session_state[f"bonus_{idx}"] = False
        st.session_state[f"reaction_{idx}"] = False
    st.session_state.combat_pending_action = None
    st.session_state.combat_pending_target = None
elif st.session_state.combat_pending_action in ("reset_round", "next_round"):
    for i in range(len(st.session_state.combatants)):
        st.session_state.combatants[i]["bonus_used"] = False
        st.session_state.combatants[i]["reaction_used"] = False
        st.session_state[f"bonus_{i}"] = False
        st.session_state[f"reaction_{i}"] = False
    st.session_state.combat_pending_action = None

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
    if mute.data["current_hp"] > 0:
        mute.data["death_saves"] = {"successes": 0, "failures": 0}

def add_roll_to_history(roll_text):
    st.session_state.last_roll = roll_text
    st.session_state.roll_history.append(roll_text)
    if len(st.session_state.roll_history) > 20:
        st.session_state.roll_history.pop(0)

with st.sidebar:
    # (unchanged – keep your existing sidebar code exactly as before)
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
        if ac_val != mute.data.get("ac"):
            mute.data["ac"] = ac_val
            mute.save_data()
        speed_val = st.number_input("Speed (ft)", value=mute.data.get("speed", 30), step=5)
        if speed_val != mute.data.get("speed"):
            mute.data["speed"] = speed_val
            mute.save_data()
        st.markdown("**Tool Proficiencies:**")
        tools = mute.data.get("tool_proficiencies", {})
        st.write(", ".join([f"{t} (Expert)" if lvl==2 else t for t, lvl in tools.items()]) if tools else "None")
        mastery_options = ["Dagger", "Shortsword", "Scimitar", "Rapier", "Shortbow", "Hand Crossbow", "Sickle"]
        current_mastery = mute.data.get("mastered_weapons", [])
        if mute.level >= 1:
            new_mastery = st.multiselect("Weapon Mastery (Pick 2)", mastery_options, default=current_mastery, max_selections=2)
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
    init_mod = mute.initiative_mod
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
    st.markdown("### 😮‍💨 Exhaustion")
    exh_level = st.number_input("Exhaustion Level (0-6)", min_value=0, max_value=6, step=1, value=mute.data.get("exhaustion", 0))
    if exh_level != mute.data.get("exhaustion", 0):
        mute.data["exhaustion"] = exh_level
        mute.save_data()
        st.rerun()
    if exh_level > 0:
        st.caption(f"⚠️ -{exh_level*2} penalty applied automatically to attack rolls, saves, skill checks, and initiative. Speed is reduced by {exh_level*5} ft (adjust manually).")
    if exh_level >= 6:
        st.error("💀 Level 6 Exhaustion: Death.")
    st.divider()
    st.markdown("### 🩸 Health & Conditions")
    st.caption("Full editing now lives on the ⚔️ Combat tab — this is just a glance from anywhere else in the app.")
    hp_percent = mute.data["current_hp"] / mute.hp_max
    st.progress(hp_percent, text=f"HP: {mute.data['current_hp']} / {mute.hp_max}")
    st.metric("Temp HP", mute.data["temp_hp"])
    if mute.data.get("conditions"):
        st.warning("⚠️ " + ", ".join(mute.data["conditions"]))
    if mute.data.get("concentrating"):
        st.info("🧠 Concentrating")
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
        mute.data["exhaustion"] = max(0, mute.data.get("exhaustion", 0) - 1)
        mute.data["death_saves"] = {"successes": 0, "failures": 0}
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

# TABS
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "⚔️ Combat", "🧪 Alchemy", "📖 Journal", "📜 Features", "📜 Roll History", "🗺️ Cartography & Influence", "🧑‍🤝‍🧑 Allies"
])

with tab1:
    st.header("Combat Dashboard")

    # ---------- STATUS AT-A-GLANCE (HP, damage, conditions, death saves) ----------
    with st.container(border=True):
        status_hp_col, status_dmg_col, status_cond_col = st.columns([1.3, 1.5, 1.2])

        with status_hp_col:
            hp_percent = mute.data["current_hp"] / mute.hp_max
            bar_label = f"❤️ HP: {mute.data['current_hp']} / {mute.hp_max}"
            if mute.data["current_hp"] == 0:
                bar_label = f"💀 DOWN — 0 / {mute.hp_max}"
            st.progress(hp_percent, text=bar_label)
            thp_col, ac_col, spd_col = st.columns(3)
            thp_col.metric("Temp HP", mute.data["temp_hp"])
            ac_col.metric("AC", mute.data.get("ac", 10))
            spd_col.metric("Speed", f"{mute.data.get('speed', 30)} ft")

        with status_dmg_col:
            st.caption("Apply Damage / Healing")
            amt_col, halve_col = st.columns([1.3, 1.7])
            dmg_amount = amt_col.number_input("Amount", min_value=0, step=1, value=0, key="combat_amount", label_visibility="collapsed")
            halve = halve_col.checkbox("🛡️ Halve (Uncanny Dodge)", key="combat_halve_toggle")
            b1, b2 = st.columns(2)
            if b1.button("🩸 Apply Damage", use_container_width=True, key="combat_apply_dmg") and dmg_amount > 0:
                final_dmg = dmg_amount // 2 if halve else dmg_amount
                was_concentrating = mute.data.get("concentrating", False)
                update_hp(-final_dmg)
                mute.save_data()
                note = " (halved via Uncanny Dodge)" if halve else ""
                add_roll_to_history(f"Took {final_dmg} damage{note}.")
                if was_concentrating and mute.data["current_hp"] > 0:
                    st.session_state.pending_concentration_dc = max(10, final_dmg // 2)
                st.rerun()
            if b2.button("💚 Apply Healing", use_container_width=True, key="combat_apply_heal") and dmg_amount > 0:
                update_hp(dmg_amount)
                mute.save_data()
                add_roll_to_history(f"Healed {dmg_amount} HP.")
                st.rerun()

        with status_cond_col:
            st.caption("Conditions")
            all_conditions = ["Blinded", "Charmed", "Deafened", "Frightened", "Grappled", "Incapacitated", "Invisible", "Paralyzed", "Petrified", "Poisoned", "Prone", "Restrained", "Stunned", "Unconscious"]
            new_conditions = st.multiselect("Active Conditions", all_conditions, default=mute.data.get("conditions", []), key="combat_conditions", label_visibility="collapsed")
            if new_conditions != mute.data.get("conditions", []):
                mute.data["conditions"] = new_conditions
                mute.save_data()
                st.rerun()
            new_concentrating = st.checkbox("🧠 Concentrating?", value=mute.data.get("concentrating", False), key="combat_concentrating")
            if new_concentrating != mute.data.get("concentrating", False):
                mute.data["concentrating"] = new_concentrating
                mute.save_data()
                st.rerun()

        # Concentration save prompt — fires automatically after damage is applied while concentrating
        if st.session_state.get("pending_concentration_dc"):
            dc = st.session_state.pending_concentration_dc
            st.warning(f"🧠 Took damage while concentrating — make a CON save (DC {dc}) or lose concentration!")
            csv1, csv2 = st.columns([1, 3])
            with csv1:
                if st.button(f"🎲 Roll CON Save ({mute.get_save_mod('CON'):+})", key="concentration_save_roll"):
                    res = roll("1d20")
                    mod = mute.get_save_mod("CON")
                    total = res + mod
                    if total >= dc:
                        add_roll_to_history(f"🧠 Concentration Save: Rolled {res} ({mod:+}) = {total} vs DC {dc}. **Success!**")
                    else:
                        add_roll_to_history(f"🧠 Concentration Save: Rolled {res} ({mod:+}) = {total} vs DC {dc}. **Failed — concentration broken!**")
                        mute.data["concentrating"] = False
                        mute.save_data()
                    st.session_state.pending_concentration_dc = None
                    st.rerun()
            with csv2:
                if st.button("Dismiss", key="concentration_save_dismiss"):
                    st.session_state.pending_concentration_dc = None
                    st.rerun()

        # Death Saving Throws — appears automatically at 0 HP
        if mute.data["current_hp"] == 0:
            st.divider()
            ds = mute.data.setdefault("death_saves", {"successes": 0, "failures": 0})
            st.markdown("### 💀 Death Saving Throws")
            dcol1, dcol2, dcol3 = st.columns([1, 1, 1.5])
            dcol1.metric("Successes", f"{ds['successes']} / 3")
            dcol2.metric("Failures", f"{ds['failures']} / 3")
            with dcol3:
                st.write("")
                if st.button("🎲 Roll Death Save", use_container_width=True, key="death_save_roll"):
                    r = roll("1d20")
                    if r == 20:
                        mute.data["current_hp"] = 1
                        ds = {"successes": 0, "failures": 0}
                        add_roll_to_history("💀 Death Save: **Natural 20!** Regained 1 HP, conscious again.")
                    elif r == 1:
                        ds["failures"] = min(3, ds["failures"] + 2)
                        add_roll_to_history(f"💀 Death Save: **Natural 1!** Counts as 2 failures ({ds['failures']}/3).")
                    elif r >= 10:
                        ds["successes"] += 1
                        add_roll_to_history(f"💀 Death Save: Rolled {r}. Success ({ds['successes']}/3).")
                    else:
                        ds["failures"] += 1
                        add_roll_to_history(f"💀 Death Save: Rolled {r}. Failure ({ds['failures']}/3).")
                    if ds["successes"] >= 3:
                        st.toast("Stabilized!")
                        ds = {"successes": 0, "failures": 0}
                    if ds["failures"] >= 3:
                        add_roll_to_history("💀 **Three failures — Mute has died.**")
                    mute.data["death_saves"] = ds
                    mute.save_data()
                    st.rerun()
            if ds["failures"] >= 3:
                st.error("💀 Three failed death saves. Mute has died.")

        # Quick rest access, so a lull in combat doesn't require the sidebar either
        with st.expander("⛺ Quick Rest"):
            available_hit_dice = mute.level - mute.data["hit_dice_spent"]
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button(f"🩹 Spend 1 Hit Die ({available_hit_dice} left)", use_container_width=True, key="combat_hitdice", disabled=(available_hit_dice == 0)):
                    mute.data["hit_dice_spent"] += 1
                    recovered = roll(f"1d8+{mute.get_mod('CON')}")
                    update_hp(recovered)
                    mute.save_data()
                    add_roll_to_history(f"Hit Die Spent: Recovered {recovered} HP")
                    st.rerun()
            with rc2:
                if st.button("🌅 Take Long Rest", use_container_width=True, key="combat_longrest"):
                    mute.data["current_hp"] = mute.hp_max
                    mute.data["hit_dice_spent"] = 0
                    mute.data["temp_hp"] = 0
                    mute.data["exhaustion"] = max(0, mute.data.get("exhaustion", 0) - 1)
                    mute.data["death_saves"] = {"successes": 0, "failures": 0}
                    st.session_state.stroke_used = False
                    st.session_state.coated_poison = None
                    mute.save_data()
                    st.rerun()

    st.divider()
    
    # ---------- IMPROVED INITIATIVE TRACKER ----------
    with st.expander("⏳ Initiative Tracker", expanded=True):
        # Display round counter at the top
        st.metric("**Round**", st.session_state.round_counter)
        
        st.markdown("Add combatants, sort by initiative, and track actions per turn.")
        add_type = st.selectbox("Combatant Type", ["Myself (Mute)", "Ally", "Enemy"], key="add_combatant_type")

        if add_type == "Myself (Mute)":
            c1, c2 = st.columns([3, 1])
            with c1:
                mute_init = st.number_input("Initiative", step=1, value=st.session_state.my_init, key="add_init_mute")
            with c2:
                st.write("")
                if st.button("➕ Add Mute", use_container_width=True):
                    st.session_state.combatants.append({
                        "name": "Mute", "initiative": mute_init, "type": "Player",
                        "bonus_used": False, "reaction_used": False
                    })
                    st.rerun()

        elif add_type == "Ally":
            allies = mute.data.get("allies", [])
            if not allies:
                st.info("No allies saved yet. Add some in the 🧑‍🤝‍🧑 Allies tab first.")
            else:
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    chosen_ally = st.selectbox("Select Ally", [a["name"] for a in allies], key="add_ally_sel")
                with c2:
                    ally_init = st.number_input("Initiative", step=1, value=0, key="add_init_ally")
                with c3:
                    st.write("")
                    if st.button("➕ Add Ally", use_container_width=True):
                        st.session_state.combatants.append({
                            "name": chosen_ally, "initiative": ally_init, "type": "Ally",
                            "bonus_used": False, "reaction_used": False
                        })
                        st.rerun()

        else:  # Enemy
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                enemy_name = st.text_input("Enemy Name", key="add_enemy_name")
            with c2:
                enemy_init = st.number_input("Initiative", step=1, value=0, key="add_init_enemy")
            with c3:
                st.write("")
                if st.button("➕ Add Enemy", use_container_width=True):
                    if enemy_name:
                        st.session_state.combatants.append({
                            "name": enemy_name, "initiative": enemy_init, "type": "Enemy",
                            "bonus_used": False, "reaction_used": False
                        })
                        st.rerun()

        if st.button("Sort by Initiative (descending)"):
            st.session_state.combatants.sort(key=lambda x: x["initiative"], reverse=True)
            st.session_state.current_turn = 0
            st.rerun()
        
        if st.session_state.combatants:
            st.divider()
            # Header
            cols = st.columns([3, 1, 1, 1, 0.5])
            cols[0].write("**Name**")
            cols[1].write("**Init**")
            cols[2].write("**Bonus**")
            cols[3].write("**Reaction**")
            cols[4].write("")
            
            type_icons = {"Player": "👤", "Ally": "🤝", "Enemy": "☠️"}
            for idx, combatant in enumerate(st.session_state.combatants):
                is_current = (idx == st.session_state.current_turn)
                if is_current:
                    st.markdown(f'<div style="background-color: #2a2a3a; padding: 5px; border-radius: 5px; margin-bottom: 2px;">', unsafe_allow_html=True)
                
                cols = st.columns([3, 1, 1, 1, 0.5])
                icon = type_icons.get(combatant.get("type", "Enemy"), "")
                cols[0].write(f"{combatant['name']} {icon}")
                cols[1].write(str(combatant["initiative"]))
                
                # Bonus Action checkbox
                bonus = cols[2].checkbox("Bonus Action used", value=combatant.get("bonus_used", False), key=f"bonus_{idx}", label_visibility="collapsed")
                # Reaction checkbox
                reaction = cols[3].checkbox("Reaction used", value=combatant.get("reaction_used", False), key=f"reaction_{idx}", label_visibility="collapsed")
                
                # Update states if changed
                if bonus != combatant.get("bonus_used", False):
                    st.session_state.combatants[idx]["bonus_used"] = bonus
                    st.rerun()
                if reaction != combatant.get("reaction_used", False):
                    st.session_state.combatants[idx]["reaction_used"] = reaction
                    st.rerun()
                
                if cols[4].button("❌", key=f"remove_{idx}"):
                    del st.session_state.combatants[idx]
                    if st.session_state.current_turn >= len(st.session_state.combatants):
                        st.session_state.current_turn = max(0, len(st.session_state.combatants)-1)
                    st.rerun()
                
                if is_current:
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # Navigation buttons
            col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1,1,1,1,1])
            with col_nav1:
                if st.button("◀ Prev Turn"):
                    # Just move back; don't reset flags (useful for undoing)
                    st.session_state.current_turn = (st.session_state.current_turn - 1) % len(st.session_state.combatants)
                    st.rerun()
            with col_nav2:
                if st.button("Next Turn ▶"):
                    current = st.session_state.current_turn
                    # Queue the reset for next run instead of doing it now —
                    # these checkboxes have already been instantiated this run.
                    st.session_state.combat_pending_action = "next_turn"
                    st.session_state.combat_pending_target = current
                    # Advance to next
                    next_turn = (current + 1) % len(st.session_state.combatants)
                    # If we wrapped, increment round
                    if next_turn == 0:
                        st.session_state.round_counter += 1
                    st.session_state.current_turn = next_turn
                    st.rerun()
            with col_nav3:
                if st.button("Reset Round"):
                    st.session_state.combat_pending_action = "reset_round"
                    st.session_state.current_turn = 0
                    st.session_state.round_counter = 1
                    st.rerun()
            with col_nav4:
                if st.button("Next Round"):
                    st.session_state.combat_pending_action = "next_round"
                    st.session_state.current_turn = 0
                    st.session_state.round_counter += 1
                    st.rerun()
            with col_nav5:
                if st.button("Clear All Combatants"):
                    st.session_state.combatants = []
                    st.session_state.current_turn = 0
                    st.session_state.round_counter = 1
                    st.rerun()
        else:
            st.info("No combatants. Add some to start tracking initiative.")
    st.divider()
    
    # ---------- REST OF COMBAT TAB (UNCHANGED) ----------
    # Cunning Action & Steady Aim live here only, since they're Mute-specific
    # Rogue features, not generic actions every combatant has.
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
                mute.save_data()
                st.rerun()
        with xb_sub_col:
            if st.button("➖", key="sub_b"): 
                mute.data["bolts"] = max(0, mute.data["bolts"] - 1)
                mute.save_data()
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
            mute.save_data()
            st.rerun()
    with harv_col3:
        if st.button("➕ Buy Reagent (10gp)") and mute.data.get("reagents", 0) < max_reagents_cap:
            mute.data["reagents"] += 1
            mute.save_data()
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

with tab7:
    st.header("🧑‍🤝‍🧑 Allies & Party Members")
    st.caption("Track your party's details here, then pull them straight into the Initiative Tracker on the Combat tab.")

    allies = mute.data.get("allies", [])

    if not allies:
        st.info("No allies added yet. Use the form below to add your first party member.")

    for idx, ally in enumerate(allies):
        with st.container(border=True):
            st.markdown(f"#### 🤝 {ally.get('name', 'Unnamed')}")
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Name", value=ally.get("name", ""), key=f"ally_name_{idx}")
                new_class = st.text_input("Class / Role", value=ally.get("class_info", ""), key=f"ally_class_{idx}")
            with col2:
                new_ac = st.number_input("AC", value=ally.get("ac", 10), min_value=0, key=f"ally_ac_{idx}")
                new_hp_max = st.number_input("Max HP", value=ally.get("hp_max", 10), min_value=0, key=f"ally_hpmax_{idx}")

            new_hp_current = st.number_input(
                "Current HP", value=ally.get("hp_current", ally.get("hp_max", 10)),
                min_value=0, max_value=max(new_hp_max, 0), key=f"ally_hpcur_{idx}"
            )
            new_notes = st.text_area("Notes", value=ally.get("notes", ""), key=f"ally_notes_{idx}", height=80)

            if (new_name != ally.get("name") or new_class != ally.get("class_info") or
                new_ac != ally.get("ac") or new_hp_max != ally.get("hp_max") or
                new_hp_current != ally.get("hp_current") or new_notes != ally.get("notes")):
                allies[idx] = {
                    "name": new_name, "class_info": new_class, "ac": new_ac,
                    "hp_max": new_hp_max, "hp_current": new_hp_current, "notes": new_notes
                }
                mute.data["allies"] = allies
                mute.save_data()
                st.rerun()

            if st.button("🗑️ Remove Ally", key=f"ally_remove_{idx}"):
                allies.pop(idx)
                mute.data["allies"] = allies
                mute.save_data()
                st.rerun()

    st.divider()
    with st.expander("➕ Add New Ally", expanded=len(allies) == 0):
        with st.form("add_ally_form", clear_on_submit=True):
            a_name = st.text_input("Name")
            a_class = st.text_input("Class / Role")
            c1, c2 = st.columns(2)
            a_ac = c1.number_input("AC", value=10, min_value=0)
            a_hp = c2.number_input("Max HP", value=10, min_value=0)
            a_notes = st.text_area("Notes")
            if st.form_submit_button("💾 Add Ally"):
                if a_name:
                    mute.data.setdefault("allies", []).append({
                        "name": a_name, "class_info": a_class, "ac": a_ac,
                        "hp_max": a_hp, "hp_current": a_hp, "notes": a_notes
                    })
                    mute.save_data()
                    st.toast(f"Added {a_name} to the party!")
                    st.rerun()