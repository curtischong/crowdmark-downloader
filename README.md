# crowdmark-downloader

This is a script I wrote to download all of my Crowdmark assessments when I graduated.

I searched around for similar tools but wasn't satisfied because other tools simply call the Crowdmark API.
What makes my downloader unique is that it downloads each assessment's page as an HTML file to preserve the TA's
feedback on each image.

### Installation

Install Selenium (the browser automation tool to roboticaly click on links and download images)
`pip3 install -r requirements.txt`

### Usage

1) Run the script using this command `python3 download.py`.
    - This will launch a new Chrome webpage and navigate to Waterloo's Learn page
2) Manually log in
    - This part cannot be automated because everyone has different credentials and 2FA setups.
3) Return to the terminal and type something random and press enter.
    - This tells the script that you have finished logging in
4) Sit back and relax! All of the HTML pages will be saved underneath the `output/` directory (it will be created after
   you run the script)

