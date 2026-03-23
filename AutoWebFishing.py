import pyautogui
import time
import cv2
import numpy as np
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "Screenshots"


def screenshot_path(filename):
    return str(SCREENSHOTS_DIR / filename)

# Path to reference images
# stuff related to fishing
start_image = screenshot_path("start.jpg")
catch_image = screenshot_path("catch.jpg")
stop_image = screenshot_path("stop.jpg")
reel1_image = screenshot_path("reel1.jpg")
reel2_image = screenshot_path("reel2.jpg")

# stuff related to inventory
wormx_image = screenshot_path("Wormsx.jpg")
worm0_image = screenshot_path("Worms0.jpg")
cricketx_image = screenshot_path("Cricketsx.jpg")
cricket0_image = screenshot_path("Crickets0.jpg")
leechx_image = screenshot_path("Leechesx.jpg")
leech0_image = screenshot_path("Leeches0.jpg")
minnowx_image = screenshot_path("Minnowsx.jpg")
minnow0_image = screenshot_path("Minnows0.jpg")
squidx_image = screenshot_path("Squidsx.jpg")
squid0_image = screenshot_path("Squids0.jpg")
nautilusx_image = screenshot_path("Nautilusesx.jpg")
nautilus0_image = screenshot_path("Nautiluses0.jpg")

# stuff for shopping
shopWorm_image = screenshot_path("shopWorm.jpg")
shopCricket_image = screenshot_path("shopCricket.jpg")
shopLeech_image = screenshot_path("shopLeech.jpg")
shopMinnow_image = screenshot_path("shopMinnow.jpg")
shopSquid_image = screenshot_path("shopSquid.jpg")
shopNautilus_image = screenshot_path("shopNautilus.jpg")
sell_image = screenshot_path("sellall.jpg")


# Function to perform image matching
def find_image_on_screen(image_path, threshold=0.8):
    screenshot = pyautogui.screenshot()
    screenshot = np.array(screenshot)
    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)

    reference_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if reference_image is None:
        print(f"Error: Could not load image at {image_path}")
        return None  # Return None if the image couldn't be loaded

    screenshot_height, screenshot_width = screenshot.shape
    ref_height, ref_width = reference_image.shape
    if ref_height > screenshot_height or ref_width > screenshot_width:
        print(
            f"Error: Reference image at {image_path} is larger than the current screenshot."
        )
        return None

    result = cv2.matchTemplate(screenshot, reference_image, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)  # Get best match

    if max_val >= threshold:
        # Calculate center of the matched image
        center_x = max_loc[0] + ref_width // 2
        center_y = max_loc[1] + ref_height // 2
        return center_x, center_y  # Return the center coordinates
    return None  # No match found

# Function to handle bait inventory
def baitInventory():
    pyautogui.keyDown('b')
    print("Pressing b.")
    pyautogui.keyUp('b')
    time.sleep(1)
    # List of bait absence and presence images (in order of priority)
    bait_images = [
        (nautilus0_image, nautilusx_image),  # Nautiluses
        (squid0_image, squidx_image),       # Squids
        (minnow0_image, minnowx_image),     # Minnows
        (leech0_image, leechx_image),       # Leeches
        (cricket0_image, cricketx_image),   # Crickets
        (worm0_image, wormx_image)          # Worms
    ]
    for absence_image, presence_image in bait_images:
        if find_image_on_screen(absence_image, threshold=1.0):
            print(f"Bait '{absence_image}' is absent. Moving to next type.")
            continue
        bait_location = find_image_on_screen(presence_image, threshold=0.99)
        if bait_location:
            center_x, center_y = bait_location
            print(f"Clicking on bait at ({center_x}, {center_y}).")
            pyautogui.mouseDown(center_x, center_y)
            pyautogui.mouseUp()
            pyautogui.keyDown('b')
            print("Pressing b.")
            pyautogui.keyUp('b')
            return center_x, center_y

    # If no bait is found, perform the fallback action
    print("No bait available. Executing fallback actions...")
    pyautogui.keyDown('b')
    pyautogui.keyUp('b')    # Press 'b'
    print("Pressed 'b'.")
    pyautogui.keyDown('s')  # Hold 's'
    print("Holding 's'...")
    time.sleep(0.6)  # Hold for 0.6 seconds
    pyautogui.keyUp('s')  # Release 's'
    print("Released 's'.")
    pyautogui.keyDown('5')
    pyautogui.keyUp('5')
    print("Pressed 5")
    time.sleep(1)

    #summon shop
    screen_width, screen_height = pyautogui.size()  # Get screen width and height
    center_x = screen_width // 2  # Calculate center x-coordinate
    center_y = screen_height // 2  # Calculate center y-coordinate

    print(f"Clicking: ({center_x}, {center_y})")
    pyautogui.mouseDown(center_x, center_y)  # Start holding the left mouse button
    pyautogui.mouseUp()

    #enter shop
    pyautogui.keyDown('e')
    pyautogui.keyUp('e')

    #shop
    shop_images = [
        (sell_image), #sell everything button
        (shopNautilus_image),  # Nautiluses
        (shopSquid_image),  # Squids
        (shopMinnow_image),  # Minnows
        (shopLeech_image),  # Leeches
        (shopCricket_image),  # Crickets
        (shopWorm_image)  # Worms
    ]

    for image_path in shop_images:
        shop_location = find_image_on_screen(image_path, threshold=0.8)  # Adjust threshold as needed
        if shop_location:
            center_x, center_y = shop_location
            print(f"Clicking on shop item at ({center_x}, {center_y}) for image: {image_path}.")
            pyautogui.mouseDown(center_x, center_y)
            pyautogui.mouseUp()
            time.sleep(0.1)
        else:
            print(f"Image not found on screen: {image_path}.")

    #Return to fishing position
    pyautogui.keyDown('e')
    pyautogui.keyUp('e')
    print("Pressing e")
    time.sleep(1)
    pyautogui.keyDown('1')
    pyautogui.keyUp('1')
    print("Took out fishing rod")
    pyautogui.keyDown('w')
    time.sleep(0.6)
    pyautogui.keyUp('w')
    print("walked back")
    


# Main function
if __name__ == "__main__":
    while True:  # Infinite loop to keep checking continuously
        # Check for `start`
        if find_image_on_screen(reel1_image) or find_image_on_screen(reel2_image) or find_image_on_screen(start_image):  # If start image or hold image is found
            # Get screen resolution to calculate center
            screen_width, screen_height = pyautogui.size()  # Get screen width and height
            center_x = screen_width // 2  # Calculate center x-coordinate
            center_y = screen_height // 2  # Calculate center y-coordinate

            # Hold left click at the center of the screen
            print(f"Holding left click at center: ({center_x}, {center_y})")
            pyautogui.mouseDown(center_x, center_y)  # Start holding the left mouse button

            # Wait for the 'catch' image to appear
            while not find_image_on_screen(catch_image):  
                print("Waiting for catch image to appear...")
                time.sleep(1)  # Check every 1 second

            # `catch_image` is detected
            print("Catch image detected. Clicking E at center.")
            while find_image_on_screen(catch_image):
                pyautogui.keyDown('e')
                print("Pressing E.")
                pyautogui.keyUp('e')
                time.sleep(0.5)

                # Additional check: if `catch_image` is still detected for 2 seconds
                start_time = time.time()  # Start the timer
                while find_image_on_screen(catch_image):
                    # Check if catch_image has been there for 2 seconds
                    if time.time() - start_time >= 2:
                        print("Catch image still detected for 2 seconds. Pausing for 2 seconds.")
                        time.sleep(2)  # Pause for 2 seconds
                        break  # Exit inner loop and wait before clicking 'E' again
                    time.sleep(0.1)  # Check every 0.1 seconds to avoid excessive CPU usage

                # Double-check if catch_image has disappeared
                if not find_image_on_screen(catch_image):
                    print("Catch image no longer detected.")
                    break  # Exit the loop if `catch_image` is no longer visible

            # When `catch_image` is no longer detected, double-check
            print("Catch image no longer detected. Double-checking...")
            time.sleep(0.5)  # Wait briefly for a second check
            if not find_image_on_screen(catch_image) and find_image_on_screen(stop_image):
                print("Stop image detected.")


                # Switch bait
                baitInventory()
                print("selecting new bait")
                

                time.sleep(1)
                pyautogui.mouseDown(center_x, center_y)  # Hold left click for 3 seconds
                print(f"Holding left click for 3 seconds at center: ({center_x}, {center_y})")
                time.sleep(1.5)
                pyautogui.mouseUp()  # Release the left mouse button
                print("Released left click after 1.5 seconds.")

            elif not find_image_on_screen(stop_image):  # Double-check
                print("Confirmed: Catch image no longer detected.")
                time.sleep(1)  # Wait 1 second
                pyautogui.mouseDown(center_x, center_y)  # Hold left click for 3 seconds
                print(f"Holding left click for 3 seconds at center: ({center_x}, {center_y})")
                time.sleep(1.5)
                pyautogui.mouseUp()  # Release the left mouse button
                print("Released left click after 1.5 seconds.")

        time.sleep(1)  # Optional delay between checks
