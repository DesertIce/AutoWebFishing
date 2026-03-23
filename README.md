# AutoWebFishing
To automate catching fish and buying bait in WEBFISHING

IMPORTANT:
Make sure you have python installed and run "pip install pyautogui opencv-python pillow" in your terminal.
Keep the reference images in the `Screenshots` folder next to `AutoWebFishing.py` (the script now resolves those paths automatically).
Make sure you have the game's built-in autoclicker ON.
Make sure your rod is bound to 1 and the portable bait station phone to 5 for continuing to fish after you run out of bait.
If you are encountering bugs, try running the game in full screen windowed mode since that seems to be very consistent for me.

How it works:
Start the script, then cast your line. The python script will take it from there!
After casting your line with some bait, the script will wait until you hook a fish. After that, it will start reeling the fish in. The catch message will be clicked through, and then your line will be cast again without your input. If you run out of bait, the script will look through your inventory for different bait if available, or it will go ahead and call a portable bait station to sell your fish and buy new bait before continuing the fishing cycle.

If you want to prioritize catching higher quality fish, you can avoid switching to lesser baits by just removing the lines of code related to the baits you don't want under bait_images. For example:
    bait_images = [
            (nautilus0_image, nautilusx_image),  # Only use Nautilus bait, no other bait
    ]

This script should work with any bait licenses you might have, if you do not have all the bait licenses. It works with any lure, including the Patient Lure. I have not included any code to click popups for the Challenge Lure.

When you cast your line, you can reel back in to do something else without needing to start the script over. Just cast your line again!

Disclaimer: This is the first thing I ever really wrote code for, aside from python practice problems, so it can definitely be optimized. But it works!

Happy Fishing!
