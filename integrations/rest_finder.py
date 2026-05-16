"""Rest stop / safe pull-over location finder using Nominatim (OpenStreetMap).

Queries Nominatim for nearby rest areas, petrol stations, and parking lots given the
driver's approximate location. Nominatim is free, requires no API key, and retains no
personal data — consistent with SafeShift's privacy-first design.
Returns a list of suggested stop names and distances for the companion/rest_break handler
to present to the driver.
"""
