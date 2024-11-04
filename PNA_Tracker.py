import cv2
import time
import pytesseract
import os
import mss
import numpy as np
import re
from threading import Thread, Lock
from customtkinter import CTk, CTkImage, CTkFrame, CTkLabel, FontManager
import customtkinter as ctk
from PIL import Image
import signal

# Directory Configuration
dir_path = os.path.dirname(os.path.realpath(__file__))
images_dir = os.path.join(dir_path, 'Images')
tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Global variables
thread_lock = Lock()

# Functions for reading and saving variables
def read_variable(key):
    if os.path.exists('variables.txt'):
        with open('variables.txt', "r") as file:
            for line in file:
                if ": " in line:
                    file_key, value = line.strip().split(": ", 1)
                    if file_key == key:
                        return value.strip()
    return ""

def read_tracker_variable(key):
    if os.path.exists('tracker_vars.txt'):
        with open('tracker_vars.txt', "r") as file:
            for line in file:
                if ": " in line:
                    file_key, value = line.strip().split(": ", 1)
                    if file_key == key:
                        return value.strip()
    return ""

def save_tracker_variable(key, value):
    if os.path.exists('tracker_vars.txt'):
        with open('tracker_vars.txt', "r") as file:
            lines = file.readlines()
    
        with open('tracker_vars.txt', "w") as file:
            for line in lines:
                if line.startswith(f"{key}:"):
                    file.write(f"{key}: {value}\n")
                else:
                    file.write(line)

def pixel_x_variable():
    return read_variable("Pixel_X")

def pixel_y_variable():
    return read_variable("Pixel_Y")

pixel_x = int(pixel_x_variable())
pixel_y = int(pixel_y_variable())

def encounters_variable():
    return read_tracker_variable("Encounters")

def save_encounters(encounters):
    save_tracker_variable("Encounters", str(encounters))

def profit_variable():
    return read_tracker_variable("Profit")

def save_profit(profit):
    save_tracker_variable("Profit", str(profit))

def screenshot():
    with mss.mss() as sct:
        monitor = {"top": 8, "left": 8, "width": 1904, "height": 1064}
        screenshot = sct.grab(monitor)
        scr_np = np.array(screenshot)
        scr_gray = cv2.cvtColor(scr_np, cv2.COLOR_BGRA2GRAY)
        return scr_gray

def screenshot_coord(coordinates):
    with mss.mss() as sct:
        box = {
            "top": coordinates[1],
            "left": coordinates[0],
            "width": coordinates[2] - coordinates[0],
            "height": coordinates[3] - coordinates[1]
        }
        screenshot = sct.grab(box)
        scr_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)
        return scr_bgr

# Checks if "vs" image is detected on screen
def vs_detected():
    screen = screenshot()
    vs_img_path = os.path.join(images_dir, 'vs.png')
    
    if screen is None:
        print("Screen capture failed.")
        return False
    
    if not os.path.exists(vs_img_path):
        print(f"vs.png not found in {images_dir}")
        return False
    
    vs_img = cv2.imread(vs_img_path, cv2.IMREAD_GRAYSCALE)
    result = cv2.matchTemplate(screen, vs_img, cv2.TM_CCOEFF_NORMED)
    threshold = 0.75
    return np.any(result >= threshold)

# Tracks profit using OCR
def profit_tracker():
    coordinates = (1511 + pixel_x, 952 + pixel_y, 1690 + pixel_x, 970 + pixel_y)
    img = screenshot_coord(coordinates)
    
    if img is None:
        print("Failed to capture the specified screen region.")
        return False
    
    cv2.imwrite("pokemon.png", img)
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    config = r'--oem 3 --psm 6'

    try:
        result = pytesseract.image_to_string(gray_img, config=config)
        match = re.search(r"You gained \$(\d+)", result)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f"Error in OCR processing: {e}")
    return False

text_label_encounters = None
text_label_profit = None
text_frame = None

# Updates the displayed encounter and profit values
def update_display():
    global text_label_encounters, text_label_profit, text_frame
    while True:
        try:
            with thread_lock:
                encounters_value = int(encounters_variable() or 0)
                encounters_text = f"{encounters_value:,}"
                profit_value = int(profit_variable() or 0)
                profit_text = f"${profit_value:,}"

            if text_label_encounters:
                text_label_encounters.configure(text=encounters_text)
            if text_label_profit:
                text_label_profit.configure(text=profit_text)

            time.sleep(0.5)
        except Exception as e:
            print(f"Error updating display: {e}")
            os.kill(os.getpid(), signal.SIGTERM)

# Sets up the main UI
def create_display():
    global text_label_encounters, text_label_profit, text_frame

    app = CTk()
    app.title("PNA Tracker")
    app.geometry("530x200")
    app.resizable(False, False)
    app.attributes("-topmost", True)
    app.overrideredirect(True)
    app.iconbitmap(os.path.join(images_dir, 'PPlanetEncountersRounded.ico'))
    ctk.set_appearance_mode("Dark")
    app.wm_attributes("-transparentcolor", app["bg"])

    screen_width = app.winfo_screenwidth()
    x_position = screen_width - 530 - 40
    y_position = 40
    app.geometry(f"530x200+{x_position}+{y_position}")

    main_frame = CTkFrame(app, fg_color="transparent")
    main_frame.pack(fill=ctk.BOTH, expand=True)

    try:
        icon_img_path = os.path.join(images_dir, 'back_rounded.png')
        discord_icon = CTkImage(Image.open(icon_img_path), size=(530, 100))
        icon_label = CTkLabel(main_frame, image=discord_icon, text="")
        icon_label.pack(side=ctk.LEFT)
    except Exception as e:
        print(f"Failed to load Discord icon: {e}")

    FontManager.load_font("PKMN RBYGSC.ttf")

    # Create buttons frame
    buttons_frame = CTkFrame(main_frame, fg_color="#f5f5f5", bg_color="#f5f5f5")
    buttons_frame.place(relx=0.43, rely=0.5, anchor="center")

    # Displays encounter and profit values
    def show_value(encounters_text=None, profit_text=None):
        global text_label_encounters, text_label_profit, text_frame

        buttons_frame.destroy()
        new_text_frame = CTkFrame(main_frame, fg_color="#f5f5f5", bg_color="#f5f5f5")

        if encounters_text is not None:
            text_label_encounters = CTkLabel(
                new_text_frame,
                text=encounters_text,
                font=("PKMN RBYGSC Regular", 60),
                fg_color="transparent",
                text_color='#2b2b2e',
                anchor="w"
            )
            text_label_encounters.pack(pady=(0, 5), padx=0)

        if profit_text is not None:
            text_label_profit = CTkLabel(
                new_text_frame,
                text=profit_text,
                font=("PKMN RBYGSC Regular", 60),
                fg_color="transparent",
                text_color='#2b2b2e',
                anchor="w"
            )
            text_label_profit.pack(pady=(0, 5), padx=0)

        text_frame = new_text_frame
        text_frame.place(relx=0.43, rely=0.5, anchor="center")

    def keep_encounters():
        encounters_value = int(encounters_variable() or 0)
        show_value(encounters_text=f"{encounters_value:,}")
        Thread(target=update_display, daemon=True).start()

    def keep_profit():
        profit_value = int(profit_variable() or 0)
        show_value(profit_text=f"${profit_value:,}")
        Thread(target=update_display, daemon=True).start()

    def new_encounters():
        save_encounters(0)
        show_value(encounters_text="0")
        Thread(target=update_display, daemon=True).start()

    def new_profit():
        save_profit(0)
        show_value(profit_text="$0")
        Thread(target=update_display, daemon=True).start()

    button_font = ("PKMN RBYGSC Regular", 18)
    keep_enc_button = ctk.CTkButton(buttons_frame, text="Keep Enc", command=keep_encounters, fg_color="#f5f5f5", hover_color="#d0d0d0", font=button_font, text_color="#2b2b2e")
    keep_profit_button = ctk.CTkButton(buttons_frame, text="Keep Profit", command=keep_profit, fg_color="#f5f5f5", hover_color="#d0d0d0", font=button_font, text_color="#2b2b2e")
    new_enc_button = ctk.CTkButton(buttons_frame, text="New Enc", command=new_encounters, fg_color="#f5f5f5", hover_color="#d0d0d0", font=button_font, text_color="#2b2b2e")
    new_profit_button = ctk.CTkButton(buttons_frame, text="New Profit", command=new_profit, fg_color="#f5f5f5", hover_color="#d0d0d0", font=button_font, text_color="#2b2b2e")

    keep_enc_button.grid(row=0, column=0, padx=10, pady=3)
    keep_profit_button.grid(row=0, column=1, padx=10, pady=3)
    new_enc_button.grid(row=1, column=0, padx=10, pady=3)
    new_profit_button.grid(row=1, column=1, padx=10, pady=3)

    # Window dragging functions
    def on_press(event):
        app.x = event.x
        app.y = event.y

    def on_drag(event):
        x = app.winfo_x() - app.x + event.x
        y = app.winfo_y() - app.y + event.y
        app.geometry(f"+{x}+{y}")

    app.bind("<Button-1>", on_press)
    app.bind("<B1-Motion>", on_drag)
    app.mainloop()

# Main Function
def main():
    total_profit = int(profit_variable() or 0)
    total_encounters = int(encounters_variable() or 0)
    plus_profit = 0
    Thread(target=create_display, daemon=True).start()

    while True:
        time.sleep(0.2)
        if vs_detected():
            while vs_detected():
                time.sleep(0.2)
            total_encounters += 1
            plus_profit = profit_tracker()
            if plus_profit is not False:
                with thread_lock:
                    total_profit += plus_profit
            save_encounters(total_encounters)
            save_profit(total_profit)
            print(f"Encounters: {total_encounters}")
            print(f"Profit: {plus_profit}")
            print(f"Total profit: {total_profit}")

if __name__ == "__main__":
    main()
