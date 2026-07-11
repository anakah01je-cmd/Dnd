import random

def roll(notation="1d20"):
    """Rolls dice based on 'XdY+Z' notation."""
    if 'd' not in notation:
        return int(notation)
    
    parts = notation.split('d')
    num_dice = int(parts[0])
    
    # Handle the modifier part
    if '+' in parts[1]:
        sides, mod = map(int, parts[1].split('+'))
    elif '-' in parts[1]:
        sides, mod = int(parts[1].split('-')[0]), -int(parts[1].split('-')[1])
    else:
        sides, mod = int(parts[1]), 0
        
    rolls = [random.randint(1, sides) for _ in range(num_dice)]
    return sum(rolls) + mod