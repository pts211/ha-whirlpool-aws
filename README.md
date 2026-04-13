# Whirlpool Appliances (AWS IoT) — HACS Custom Integration

Test integration for the [whirlpool-sixth-sense](https://github.com/abmantis/whirlpool-sixth-sense) AWS IoT branch. Clones the official [Whirlpool integration](https://www.home-assistant.io/integrations/whirlpool/) and adds microwave support via the AWS IoT MQTT transport.

## Installation

1. Add this repository as a custom repository in HACS (Integration type)
2. Install "Whirlpool Appliances (AWS IoT)"
3. Restart Home Assistant
4. Add the integration via Settings > Integrations > Add Integration > "Whirlpool Appliances (AWS IoT)"

## Supported Appliances

All appliances supported by the official integration (aircon, washer, dryer, oven, refrigerator) plus:

- **Microwave** (via AWS IoT): cavity state, cook timer, hood fan, hood light, cavity light, control lock, quiet mode, sabbath mode, start/cancel cook
