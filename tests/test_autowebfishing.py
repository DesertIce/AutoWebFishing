from pathlib import Path
from unittest.mock import patch

import numpy as np

import AutoWebFishing as awf


def test_all_configured_images_exist():
    image_paths = [
        awf.start_image,
        awf.catch_image,
        awf.stop_image,
        awf.reel1_image,
        awf.reel2_image,
        awf.wormx_image,
        awf.worm0_image,
        awf.cricketx_image,
        awf.cricket0_image,
        awf.leechx_image,
        awf.leech0_image,
        awf.minnowx_image,
        awf.minnow0_image,
        awf.squidx_image,
        awf.squid0_image,
        awf.nautilusx_image,
        awf.nautilus0_image,
        awf.shopWorm_image,
        awf.shopCricket_image,
        awf.shopLeech_image,
        awf.shopMinnow_image,
        awf.shopSquid_image,
        awf.shopNautilus_image,
        awf.sell_image,
    ]

    missing = [path for path in image_paths if not Path(path).is_file()]

    assert missing == []


def test_find_image_on_screen_returns_none_for_oversized_template():
    screenshot = np.zeros((10, 10, 3), dtype=np.uint8)
    reference = np.zeros((20, 20), dtype=np.uint8)

    with patch.object(awf.pyautogui, "screenshot", return_value=screenshot), patch.object(
        awf.cv2, "imread", return_value=reference
    ):
        assert awf.find_image_on_screen("ignored.jpg") is None
