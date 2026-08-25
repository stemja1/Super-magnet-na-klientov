"""Prompt templates (parameterized slots) for the LLM Orchestrator (spec §8).

Every template has named slots filled at call time. Slovak-language by default
to match the Slovak B2B context.
"""

# Lead scoring — exact spec text (§8).
LEAD_SCORING_TEMPLATE = """Vstupné dáta: {company_profile}, {contact_profile}, {recent_activity}.
Úloha: ohodnoť lead od 0 do 100 podľa pravdepodobnosti konverzie v slovenskom B2B prostredí. Zohľadni: veľkosť firmy, odvetvie, finančné ukazovatele (FinStat), aktivitu na webe, job change signály. Vysvetli skóre v 3 bodoch."""

PRE_MEETING_INSIGHTS_TEMPLATE = """Na základe profilu firmy {company_profile} a nedávnej aktivity {recent_activity}
priprav 5 stručných postrehov pred obchodným hovorom v slovenskom B2B kontexte. Zameraj sa na:
- Pain points odvetvia
- Vhodnú konverzačnú skratku
- 2 relevantné otázky
- Rižiká a ako im predísť"""

EMAIL_GENERATION_TEMPLATE = """Napíš profesionálny, stručný B2B email v slovenčine.
Príjemca: {contact_profile}
Cieľ: {email_goal}
Tón: {tone}
Požiadavka: vygeneruj predmet (Subject) a telo emailu (max 120 slov)."""

CALL_SUMMARIZATION_TEMPLATE = """Zhrň nasledujúci prepis obchodného hovoru na slovenčine do štruktúry:
- Hlavný záujem zákazníka
- Nasledujúci krok (action item)
- Odhad pravdepodobnosti konverzie (0-100)
Prepis: {transcript}"""
