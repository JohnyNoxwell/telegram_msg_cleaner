import asyncio
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.i18n import _, get_lang, set_lang, use_lang


class TestI18N(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        set_lang("ru")

    async def test_use_lang_restores_previous_language(self):
        set_lang("ru")

        with use_lang("en"):
            self.assertEqual(get_lang(), "en")
            self.assertEqual(_("menu_title"), "MAIN MENU")

        self.assertEqual(get_lang(), "ru")
        self.assertEqual(_("menu_title"), "ГЛАВНОЕ МЕНЮ")

    async def test_unknown_language_falls_back_to_default(self):
        set_lang("de")
        self.assertEqual(get_lang(), "ru")

        with use_lang("fr"):
            self.assertEqual(get_lang(), "ru")

    async def test_language_context_is_task_local(self):
        barrier = asyncio.Barrier(2)

        async def worker(lang: str) -> tuple[str, str]:
            with use_lang(lang):
                await barrier.wait()
                await asyncio.sleep(0)
                return get_lang(), _("menu_title")

        en_result, ru_result = await asyncio.gather(worker("en"), worker("ru"))

        self.assertEqual(en_result, ("en", "MAIN MENU"))
        self.assertEqual(ru_result, ("ru", "ГЛАВНОЕ МЕНЮ"))
        self.assertEqual(get_lang(), "ru")


if __name__ == "__main__":
    unittest.main()
