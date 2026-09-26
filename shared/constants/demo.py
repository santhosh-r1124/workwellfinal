"""What marks a row as a fixture rather than a person.

Three scripts and one route need to agree on this, and they used to each
carry their own copy. A seeder and a purger that disagree by one character
is the failure where invented telemetry survives the purge and quietly
shares a database with real measurements - at which point no dashboard can
tell its reader which numbers were made up.
"""

# Fixtures live on a domain nobody can receive mail at, so membership of
# the demo set is a property of the row rather than a flag someone has to
# remember to set.
DEMO_EMAIL_DOMAIN = "@demo.workwell.ai"

# Published in the README and printed by the seeder. It is a fixture
# credential, not a secret; what keeps it safe is that the accounts it
# opens exist only where someone deliberately seeded them.
DEMO_PASSWORD = "workwell-demo"


def is_demo_email(email: str) -> bool:
    return email.lower().endswith(DEMO_EMAIL_DOMAIN)
