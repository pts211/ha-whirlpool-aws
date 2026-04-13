"""Constants for the Whirlpool AWS integration."""

from whirlpool.backendselector import Brand, Region

DOMAIN = "whirlpool_aws"
CONF_BRAND = "brand"

REGIONS_CONF_MAP = {
    "EU": Region.EU,
    "US": Region.US,
}

BRANDS_CONF_MAP = {
    "Whirlpool": Brand.Whirlpool,
    "Maytag": Brand.Maytag,
    "KitchenAid": Brand.KitchenAid,
    "Consul": Brand.Consul,
}
