#!/usr/bin/env python3
"""Parse natural language like 'set alarm for seven thirty am' → HOUR|MINUTE|LABEL"""
import sys
import re

WORD_NUMS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
    'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
    'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
    'oh': 0, 'o': 0,
}

def words_to_nums(text):
    tokens = text.split()
    out = []
    i = 0
    while i < len(tokens):
        w = tokens[i]
        if w in WORD_NUMS:
            val = WORD_NUMS[w]
            if val in (20, 30, 40, 50) and i + 1 < len(tokens):
                nxt = tokens[i + 1]
                if nxt in WORD_NUMS and WORD_NUMS[nxt] < 10:
                    val += WORD_NUMS[nxt]
                    i += 1
            out.append(str(val))
        else:
            out.append(w)
        i += 1
    return " ".join(out)

def parse(text):
    t = text.lower().strip()
    # Split glued forms like "7am" → "7 am", "10pm" → "10 pm"
    t = re.sub(r'(\d)(am|pm|a\.m\.|p\.m\.)', r'\1 \2', t)
    t = words_to_nums(t)

    hour = None
    minute = 0

    # "7:30", "7.30", "7 30"
    m = re.search(r'\b(\d{1,2})[:\.\s](\d{1,2})\b', t)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if h <= 23 and mn <= 59:
            hour, minute = h, mn

    # Bare hour fallback
    if hour is None:
        m = re.search(r'\b(\d{1,2})\b', t)
        if m:
            hour = int(m.group(1))

    if hour is None:
        return None

    # AM/PM handling
    if 'pm' in t or 'p.m' in t or 'evening' in t or 'afternoon' in t or 'night' in t:
        if hour < 12:
            hour += 12
    elif 'am' in t or 'a.m' in t or 'morning' in t:
        if hour == 12:
            hour = 0

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    label = "Alarm"
    for keyword in ['medication', 'gym', 'work', 'meeting', 'wake', 'meds']:
        if keyword in t:
            label = keyword.capitalize()
            break

    return f"{hour}|{minute}|{label}"

if __name__ == "__main__":
    text = " ".join(sys.argv[1:])
    result = parse(text)
    if result:
        print(result)
