# crowdmark-downloader

This is a script I wrote to download all of my Crowdmark assessments when I graduated.

I searched for similar tools but wasn't satisfied because other tools simply called Crowdmark's API.
My downloader is unique because it downloads each assessment's page as an HTML file to preserve the TA's
feedback on each image.

### Installation

Install Selenium (the browser automation tool to click on links and download images robotically)
`pip3 install -r requirements.txt`

### Usage

1) Run the script using this command `python3 download.py`.
    - This will launch a new Chrome webpage and navigate to Waterloo's Learn page
2) Manually log in
    - I cannot automate this part because everyone has different credentials and 2FA schemes.
3) Return to the terminal and type something random and press enter.
    - This tells the script that you have finished logging in
4) Sit back and relax! All of the HTML pages will be saved underneath the `output/` directory (it will be created after
   you run the script)

### Important Usage Notes

This program assumes that you have a stable internet connection and that you are downloading all of the files in one
sitting.
If your computer goes to sleep, the script will be interrupted.

### Maintenance

I will not be maintaining this repo because I just wanted to write this simple script in an afternoon to help with a
small task. Hopefully you will also find this code useful!

Oh, and also...........

# Congrats on Graduating!
