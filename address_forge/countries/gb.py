"""
UK (GB) address parsing rules for address-forge.

United Kingdom address conventions differ from continental Europe in several
key respects that affect ISO 20022 PostalAddress24 field mapping.
"""

RULES = """
UK Address Parsing Rules:
- UK postcodes follow the format: AN NAA, ANN NAA, AAN NAA, AANN NAA, ANA NAA, AANA NAA
  (e.g. SW1A 2AA, EC1A 1BB, W1A 0AX, NW1 6XE, M1 1AE)
- Always separate the building number from the street name.
  Example: "221B Baker Street" → building_number="221B", street_name="Baker Street"
- UK does NOT have a 'state' or 'province' — country_sub_division is rarely used.
  For London, use town_location_name for the borough if given (e.g. "Westminster").
- The town_name is the post town (e.g. "London", "Manchester", "Edinburgh"), NOT a district.
- Scottish addresses: town_name is the Scottish city/town. country="GB".
- Northern Ireland addresses: country="GB" (not IE).
- For "London" addresses, the post town is "London" even if the borough is given.
- PO Box addresses: use post_box field, set address_type="PBOX".
- "Flat" or "Apartment" numbers: put in building_number (e.g. "Flat 3B").
- Building names (e.g. "Canary Wharf", "The Shard") go in building_name.
- county_sub_division: use for English counties only if explicitly stated (e.g. "Surrey", "Kent").
- Do NOT invent postal codes — if not present in the input, omit post_code.
"""
