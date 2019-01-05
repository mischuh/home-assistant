"""Collection of useful functions for the HomeKit component."""
import logging

import voluptuous as vol

from homeassistant.components import media_player
from homeassistant.core import split_entity_id
from homeassistant.const import (
    ATTR_CODE, ATTR_SUPPORTED_FEATURES, CONF_NAME, CONF_TYPE, TEMP_CELSIUS)
import homeassistant.helpers.config_validation as cv
import homeassistant.util.temperature as temp_util
from .const import (
    CONF_FEATURE, CONF_FEATURE_LIST, HOMEKIT_NOTIFY_ID, FEATURE_ON_OFF,
    FEATURE_PLAY_PAUSE, FEATURE_PLAY_STOP, FEATURE_TOGGLE_MUTE, TYPE_FAUCET,
    TYPE_OUTLET, TYPE_SHOWER, TYPE_SPRINKLER, TYPE_SWITCH, TYPE_VALVE)

_LOGGER = logging.getLogger(__name__)


BASIC_INFO_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
})

FEATURE_SCHEMA = BASIC_INFO_SCHEMA.extend({
    vol.Optional(CONF_FEATURE_LIST, default=None): cv.ensure_list,
})


CODE_SCHEMA = BASIC_INFO_SCHEMA.extend({
    vol.Optional(ATTR_CODE, default=None): vol.Any(None, cv.string),
})

MEDIA_PLAYER_SCHEMA = vol.Schema({
    vol.Required(CONF_FEATURE): vol.All(
        cv.string, vol.In((FEATURE_ON_OFF, FEATURE_PLAY_PAUSE,
                           FEATURE_PLAY_STOP, FEATURE_TOGGLE_MUTE))),
})

SWITCH_TYPE_SCHEMA = BASIC_INFO_SCHEMA.extend({
    vol.Optional(CONF_TYPE, default=TYPE_SWITCH): vol.All(
        cv.string, vol.In((
            TYPE_FAUCET, TYPE_OUTLET, TYPE_SHOWER, TYPE_SPRINKLER,
            TYPE_SWITCH, TYPE_VALVE))),
})


def validate_entity_config(values):
    """Validate config entry for CONF_ENTITY."""
    if not isinstance(values, dict):
        raise vol.Invalid('expected a dictionary')

    entities = {}
    for entity_id, config in values.items():
        entity = cv.entity_id(entity_id)
        domain, _ = split_entity_id(entity)

        if not isinstance(config, dict):
            raise vol.Invalid('The configuration for {} must be '
                              ' a dictionary.'.format(entity))

        if domain in ('alarm_control_panel', 'lock'):
            config = CODE_SCHEMA(config)

        elif domain == media_player.DOMAIN:
            config = FEATURE_SCHEMA(config)
            feature_list = {}
            for feature in config[CONF_FEATURE_LIST]:
                params = MEDIA_PLAYER_SCHEMA(feature)
                key = params.pop(CONF_FEATURE)
                if key in feature_list:
                    raise vol.Invalid('A feature can be added only once for {}'
                                      .format(entity))
                feature_list[key] = params
            config[CONF_FEATURE_LIST] = feature_list

        elif domain == 'switch':
            config = SWITCH_TYPE_SCHEMA(config)

        else:
            config = BASIC_INFO_SCHEMA(config)

        entities[entity] = config
    return entities


def validate_media_player_features(state, feature_list):
    """Validate features for media players."""
    features = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

    supported_modes = []
    if features & (media_player.SUPPORT_TURN_ON |
                   media_player.SUPPORT_TURN_OFF):
        supported_modes.append(FEATURE_ON_OFF)
    if features & (media_player.SUPPORT_PLAY | media_player.SUPPORT_PAUSE):
        supported_modes.append(FEATURE_PLAY_PAUSE)
    if features & (media_player.SUPPORT_PLAY | media_player.SUPPORT_STOP):
        supported_modes.append(FEATURE_PLAY_STOP)
    if features & media_player.SUPPORT_VOLUME_MUTE:
        supported_modes.append(FEATURE_TOGGLE_MUTE)

    error_list = []
    for feature in feature_list:
        if feature not in supported_modes:
            error_list.append(feature)

    if error_list:
        _LOGGER.error('%s does not support features: %s',
                      state.entity_id, error_list)
        return False
    return True


def show_setup_message(hass, pincode):
    """Display persistent notification with setup information."""
    pin = pincode.decode()
    _LOGGER.info('Pincode: %s', pin)
    message = 'To set up Home Assistant in the Home App, enter the ' \
              'following code:\n### {}'.format(pin)
    hass.components.persistent_notification.create(
        message, 'HomeKit Setup', HOMEKIT_NOTIFY_ID)


def dismiss_setup_message(hass):
    """Dismiss persistent notification and remove QR code."""
    hass.components.persistent_notification.dismiss(HOMEKIT_NOTIFY_ID)


def convert_to_float(state):
    """Return float of state, catch errors."""
    try:
        return float(state)
    except (ValueError, TypeError):
        return None


def temperature_to_homekit(temperature, unit):
    """Convert temperature to Celsius for HomeKit."""
    return round(temp_util.convert(temperature, unit, TEMP_CELSIUS) * 2) / 2


def temperature_to_states(temperature, unit):
    """Convert temperature back from Celsius to Home Assistant unit."""
    return round(temp_util.convert(temperature, TEMP_CELSIUS, unit) * 2) / 2


def density_to_air_quality(density):
    """Map PM2.5 density to HomeKit AirQuality level."""
    if density <= 35:
        return 1
    if density <= 75:
        return 2
    if density <= 115:
        return 3
    if density <= 150:
        return 4
    return 5
