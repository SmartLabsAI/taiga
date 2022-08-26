# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos Ventures SL

from taiga.base import templating
from taiga.base.i18n import FALLBACK_LOCALE, I18N


def test_i18n_is_created_with_the_falback_lang():
    i18n = I18N()
    assert i18n.translations.info()["language"] == str(FALLBACK_LOCALE)
    assert len(i18n._translations_cache) == 1


def test_i18n_is_initialized_with_the_config_lang(override_settings, initialize_template_env):
    settings_lang = "es_ES"
    with (override_settings({"LANG": settings_lang}), initialize_template_env()):
        i18n = I18N()

        orig_trans = i18n.translations
        assert orig_trans.info()["language"] == str(FALLBACK_LOCALE)
        assert "jinja2.ext.InternationalizationExtension" not in templating.env.extensions
        assert "gettext" not in templating.env.globals
        assert len(i18n._translations_cache) == 1

        i18n.initialize()

        init_trans = i18n.translations
        assert init_trans.info()["language"] == settings_lang
        assert "jinja2.ext.InternationalizationExtension" in templating.env.extensions
        assert templating.env.globals["gettext"] == init_trans.gettext
        assert len(i18n._translations_cache) == 2  # fallback != settings lang


def test_i18n_set_lang(override_settings, initialize_template_env):
    settings_lang = "en_US"
    lang = "es_ES"
    with (override_settings({"LANG": settings_lang}), initialize_template_env()):
        i18n = I18N()
        i18n.initialize()

        init_trans = i18n.translations
        assert init_trans.info()["language"] == settings_lang
        assert "jinja2.ext.InternationalizationExtension" in templating.env.extensions
        assert templating.env.globals["gettext"] == init_trans.gettext
        assert len(i18n._translations_cache) == 1  # fallback == settings lang

        i18n.set_lang(lang)

        new_trans = i18n.translations
        assert new_trans.info()["language"] == lang
        assert "jinja2.ext.InternationalizationExtension" in templating.env.extensions
        assert templating.env.globals["gettext"] == new_trans.gettext
        assert len(i18n._translations_cache) == 2


def test_i18n_reset_lang(override_settings):
    settings_lang = "es_ES"
    lang = "en_US"
    with override_settings({"LANG": settings_lang}):
        i18n = I18N()
        i18n.initialize()
        i18n.set_lang(lang)

        assert i18n.translations.info()["language"] == lang

        i18n.reset_lang()

        assert i18n.translations.info()["language"] == settings_lang


def test_i18n_use_contextmanager(override_settings):
    settings_lang = "es_ES"
    lang = "en_US"
    with override_settings({"LANG": settings_lang}):
        i18n = I18N()
        i18n.initialize()

        assert i18n.translations.info()["language"] == settings_lang

        with i18n.use(lang):
            assert i18n.translations.info()["language"] == lang

        assert i18n.translations.info()["language"] == settings_lang


def test_i18n_if_is_language_available():
    lang = "en_US"
    invalid_lang = "invalid_lang"
    i18n = I18N()

    assert i18n.is_language_available(lang)
    assert not i18n.is_language_available(invalid_lang)
