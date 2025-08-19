"""
Project-wide constants for the cocktails app.
Keep shared enums, default URLs, etc. here.
"""

# Default "no image" placeholder used in admin previews
NO_IMAGE_URL = "https://res.cloudinary.com/dau9qbp3l/image/upload/v1755145790/no-photo-master.png"

# Canonical list of glass types used across admin/forms (and elsewhere)
GLASS_TYPE_CHOICES = [
    ("Highball", "Highball"),
    ("Rocks", "Rocks / Old Fashioned"),
    ("Shot", "Shot"),
    ("Martini", "Martini / Cocktail"),
    ("Hurricane", "Hurricane"),
    ("Margarita", "Margarita"),
    ("Coupe", "Coupe / Champagne Saucer"),
    ("Collins", "Collins"),
    ("Flute", "Flute"),
    ("Irish Coffee", "Irish Coffee"),
    ("Red Wine", "Red Wine / Wine"),
    ("White Wine", "White Wine / Bowl / Orb"),
    ("Nick & Nora", "Nick & Nora"),
    ("Snifter", "Cognac / Snifter / Brandy"),
    ("Tiki", "Tiki"),
    ("Sling", "Sling"),
    ("Pitcher", "Pitcher"),
    ("Goblet", "Goblet"),
    ("Jar", "Jar"),
    ("Copper Mug", "Copper Mug"),
    ("French Press", "French Press"),
    ("Milkshake", "Milkshake"),
    ("Punch Bowl", "Punch Bowl"),
    ("Tea Cup", "Tea Cup"),
]

DEFAULT_GLASS_TYPE = "Highball"

__all__ = ["NO_IMAGE_URL", "GLASS_TYPE_CHOICES", "DEFAULT_GLASS_TYPE"]
