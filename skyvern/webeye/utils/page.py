from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List

import structlog
from playwright._impl._errors import TimeoutError
from playwright.async_api import ElementHandle, Frame, Page

from skyvern.constants import PAGE_CONTENT_TIMEOUT, SKYVERN_DIR
from skyvern.exceptions import FailedToTakeScreenshot
from skyvern.forge.sdk.settings_manager import SettingsManager

LOG = structlog.get_logger()


def load_js_script() -> str:
    # TODO: Handle file location better. This is a hacky way to find the file location.
    path = f"{SKYVERN_DIR}/webeye/scraper/domUtils.js"
    try:
        # TODO: Implement TS of domUtils.js and use the complied JS file instead of the raw JS file.
        # This will allow our code to be type safe.
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError as e:
        LOG.exception("Failed to load the JS script", path=path)
        raise e


JS_FUNCTION_DEFS = load_js_script()


class SkyvernFrame:
    @staticmethod
    async def take_screenshot(
        page: Page,
        full_page: bool = False,
        file_path: str | None = None,
        timeout: float = SettingsManager.get_settings().BROWSER_LOADING_TIMEOUT_MS,
    ) -> bytes:
        try:
            await page.wait_for_load_state(timeout=SettingsManager.get_settings().BROWSER_LOADING_TIMEOUT_MS)
            LOG.info("Page is fully loaded, agent is about to take screenshots")
            start_time = time.time()
            screenshot: bytes = bytes()
            if file_path:
                screenshot = await page.screenshot(
                    path=file_path,
                    full_page=full_page,
                    timeout=timeout,
                )
            else:
                screenshot = await page.screenshot(
                    full_page=full_page,
                    timeout=timeout,
                    animations="disabled",
                )
            end_time = time.time()
            LOG.info(
                "Screenshot taking time",
                screenshot_time=end_time - start_time,
                full_page=full_page,
                file_path=file_path,
            )
            return screenshot
        except TimeoutError as e:
            LOG.exception(f"Timeout error while taking screenshot: {str(e)}")
            raise FailedToTakeScreenshot(error_message=str(e)) from e
        except Exception as e:
            LOG.exception(f"Unknown error while taking screenshot: {str(e)}")
            raise FailedToTakeScreenshot(error_message=str(e)) from e

    @staticmethod
    async def take_split_screenshots(
        page: Page,
        url: str,
        draw_boxes: bool = False,
        max_number: int = SettingsManager.get_settings().MAX_NUM_SCREENSHOTS,
    ) -> List[bytes]:
        skyvern_page = await SkyvernFrame.create_instance(frame=page)
        assert isinstance(skyvern_page.frame, Page)

        screenshots: List[bytes] = []
        scroll_y_px_old = -30.0
        scroll_y_px = await skyvern_page.scroll_to_top(draw_boxes=draw_boxes)
        # Checking max number of screenshots to prevent infinite loop
        # We are checking the difference between the old and new scroll_y_px to determine if we have reached the end of the
        # page. If the difference is less than 25, we assume we have reached the end of the page.
        while abs(scroll_y_px_old - scroll_y_px) > 25 and len(screenshots) < max_number:
            screenshot = await SkyvernFrame.take_screenshot(page=skyvern_page.frame, full_page=False)
            screenshots.append(screenshot)
            scroll_y_px_old = scroll_y_px
            LOG.info("Scrolling to next page", url=url, num_screenshots=len(screenshots))
            scroll_y_px = await skyvern_page.scroll_to_next_page(draw_boxes=draw_boxes)
            LOG.info(
                "Scrolled to next page",
                scroll_y_px=scroll_y_px,
                scroll_y_px_old=scroll_y_px_old,
            )
        if draw_boxes:
            await skyvern_page.remove_bounding_boxes()
        await skyvern_page.scroll_to_top(draw_boxes=False)
        return screenshots

    @classmethod
    async def create_instance(cls, frame: Page | Frame) -> SkyvernFrame:
        instance = cls(frame=frame)
        await instance.frame.evaluate(JS_FUNCTION_DEFS)
        return instance

    def __init__(self, frame: Page | Frame) -> None:
        self.frame = frame

    def get_frame(self) -> Page | Frame:
        return self.frame

    async def get_content(self, timeout: float = PAGE_CONTENT_TIMEOUT) -> str:
        async with asyncio.timeout(timeout):
            return await self.frame.content()

    async def get_select2_options(self, element: ElementHandle) -> List[Dict[str, Any]]:
        await self.frame.evaluate(JS_FUNCTION_DEFS)
        js_script = "async (element) => await getSelect2Options(element)"
        return await self.frame.evaluate(js_script, element)

    async def get_combobox_options(self, element: ElementHandle) -> List[Dict[str, Any]]:
        await self.frame.evaluate(JS_FUNCTION_DEFS)
        js_script = "async (element) => await getListboxOptions(element)"
        return await self.frame.evaluate(js_script, element)

    async def scroll_to_top(self, draw_boxes: bool) -> float:
        """
        Scroll to the top of the page and take a screenshot.
        :param drow_boxes: If True, draw bounding boxes around the elements.
        :param page: Page instance to take the screenshot from.
        :return: Screenshot of the page.
        """
        js_script = f"async () => await scrollToTop({str(draw_boxes).lower()})"
        scroll_y_px = await self.frame.evaluate(js_script)
        return scroll_y_px

    async def scroll_to_next_page(self, draw_boxes: bool) -> float:
        """
        Scroll to the next page and take a screenshot.
        :param drow_boxes: If True, draw bounding boxes around the elements.
        :param page: Page instance to take the screenshot from.
        :return: Screenshot of the page.
        """
        js_script = f"async () => await scrollToNextPage({str(draw_boxes).lower()})"
        scroll_y_px = await self.frame.evaluate(js_script)
        return scroll_y_px

    async def remove_bounding_boxes(self) -> None:
        """
        Remove the bounding boxes from the page.
        :param page: Page instance to remove the bounding boxes from.
        """
        js_script = "() => removeBoundingBoxes()"
        await self.frame.evaluate(js_script)
