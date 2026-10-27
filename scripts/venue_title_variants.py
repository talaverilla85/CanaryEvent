"""Proof-conservative alias titles for cross-source venue corroboration.

Only a few observed title wrapper differences. Exact event-day/municipality
matching, independent source requirement, and the conflict gate still apply.
"""
import re
import unicodedata

def variants(title):
    raw=str(title or "")
    raw=unicodedata.normalize("NFKD",raw).casefold()
    raw="".join(c for c in raw if not unicodedata.combining(c))
    raw=re.sub(r"[^a-z0-9]+"," ",raw).strip()
    forms={raw}
    if raw.startswith("concierto "):
        forms.add(raw[len("concierto "):].strip())
    if raw.startswith("exposicion "):
        forms.add(raw[len("exposicion "):].strip())
    # A title having an extra municipality/festival suffix still represents
    # an identical named performance, never an arbitrary substring match.
    for ending in (" telde"," san rafael"," teatro juan ramon jimenez"):
        if raw.endswith(ending):
            forms.add(raw[:-len(ending)].strip())
    if " otro show de impro mas" in raw:
        forms.add("otro show de impro mas")
    return {re.sub(r"[^a-z0-9]+","",s) for s in forms if len(s)>=7}
