import time

import pyautogui
def main():
    # Convert the user's input to an integer
    while True:
        try:
            num_courses_on_page = 3 # int(input("Please the number of courses you have on this page: "))
            # time.sleep(1)  # this is needed so the enter you press in the terminal doesn't interfere
            break
        except ValueError:
            print("Please enter a valid integer.")


    # alt tab back to chrome
    pyautogui.keyDown('command')
    pyautogui.press('tab')
    pyautogui.keyUp('command')


    for course in range(num_courses_on_page):
        # go into the first apge
        pyautogui.press('tab')
        pyautogui.press('tab')
        pyautogui.press('enter')
        download_assessments_for_course()

def download_assessments_for_course():
    pyautogui.press('tab')




if __name__ == '__main__':
    main()