import time
import base64

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
import os
from glob import glob
import shutil

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

def main():
    driver = webdriver.Chrome()
    driver.get("https://app.crowdmark.com/sign-in")

    input("Press Enter after logging in: ")

    assert "Crowdmark" in driver.title
    working_directory = os.getcwd()

    output_directory = os.path.join(working_directory, "output")
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # It's important that we retry failed requests because the network can be unreliable.
    retry = Retry(
        total=10,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount('https://', adapter)

    start_time = time.time()
    download_assessments_for_ith_page(driver, output_directory, 1, session)
    end_time = time.time()

    elapsed_time = end_time - start_time
    print("Finished downloading in: ", elapsed_time, " seconds!")
    driver.close()

    post_process(working_directory, output_directory)

    exit(0)


def download_assessments_for_ith_page(driver, output_directory, starting_page, session):
    page_num = starting_page
    # for each page in crowdmark, install each assessment
    while True:
        driver.get(f"https://app.crowdmark.com/student/courses?page={page_num}")
        time.sleep(3)  # wait for page to load. For some reason driver.get doesn't wait for the entire page to load

        course_list = driver.find_element(By.CLASS_NAME, "courses__course-list")

        a_tags = course_list.find_elements(By.TAG_NAME, "a")

        if len(a_tags) == 0:
            # there are no more links on this page, so we have scraped all the assessments
            return

        urls = [a_tag.get_attribute("href") for a_tag in a_tags]
        for url in urls:
            download_assessments_for_course(driver, output_directory, url, session)

        page_num += 1


def download_assessments_for_course(driver, output_directory, url, session):
    course_name = page_name(url)
    driver.get(url)
    time.sleep(3)  # wait for page to load. For some reason driver.get doesn't wait for the entire page to load

    course_output_directory = os.path.join(output_directory, course_name)
    if not os.path.exists(course_output_directory):
        os.makedirs(course_output_directory)

    a_tags = driver.find_elements(By.TAG_NAME, "a")
    urls = [a_tag.get_attribute("href") for a_tag in a_tags]
    for assessment_url in urls:
        if (not assessment_url) or ("assessments" not in assessment_url):
            # this link doesn't take you to an assessment
            continue
        download_assessment(driver, course_output_directory, assessment_url, session)


def download_assessment(driver, course_output_directory, url, session):
    driver.get(url)
    time.sleep(5)  # wait for page to load. For some reason driver.get doesn't wait for the entire page to load
    assessment_name = page_name(url)

    # Show class score distribution (if it is available).
    buttons_to_show_scores = driver.find_elements(By.CSS_SELECTOR, "button.score-summary__score-toggle")
    assert len(buttons_to_show_scores) in [0, 1]
    if len(buttons_to_show_scores) == 1:
        buttons_to_show_scores[0].click()

    # Remove extraneous elements. These are elements which will never be useful in an offline archive of the assessment page.
    for selector in ["script", "link", ".main-sidebar", ".main-topbar", ".mobile-topbar", ".score-view__actions", ".score-summary__graph-wrap"]:
        remove_elements_by_css_selector(driver, selector, url)

    # Remove the iframe. We could have done this above, but removing all iframe elements is a little bit dangerous if the site design changes.
    # So we do it here instead with a few assertions to fail fast in case of unexpected behaviour.
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if len(iframes) > 0:
        assert iframes[0].get_attribute("src").startswith("https://js.stripe.com")
        driver.execute_script('arguments[0].outerHTML="";', iframes[0])
        assert len(driver.find_elements(By.TAG_NAME, "iframe")) == 0

    # Replace canvas element by equivalent image.
    # This canvas element only exists on assessments where the 'Class scores distribution' is shown.
    canvas_elements = driver.find_elements(By.CSS_SELECTOR, "canvas")
    assert len(canvas_elements) in [0, 1]
    if len(canvas_elements) == 1:
        # Implementation copied from https://stackoverflow.com/a/38318578/14464173 .
        canvas_base64 = driver.execute_script("return arguments[0].toDataURL('image/png');", canvas_elements[0])
        assert canvas_base64.count("data:image/png;base64,") == 1
        canvas_base64 = canvas_base64.replace("data:image/png;base64,", "")
        canvas_png = base64.b64decode(canvas_base64)
        with open(f"{course_output_directory}/{assessment_name}_distribution.png", 'xb') as f:
            f.write(canvas_png)
        driver.execute_script(f'arguments[0].outerHTML = "<img src=\'{assessment_name}_distribution.png\' alt=\'Scores distribution chart\'>";', canvas_elements[0])

    # Grab a list of all the images for later downloading.
    images = []
    for img in driver.find_elements(By.TAG_NAME, "img"):
        imageURL = img.get_attribute("src")
        # We are certainly interested in downloading these images.
        if imageURL.startswith("https://usercontent.crowdmark.com") or imageURL.startswith("https://assets.crowdmark.com"):
            filename = imageURL.split("/")[-1].split("?")[0] + ".jpg"
            assert len(filename) >= 20
            images.append((imageURL, filename))
        # We are certainly NOT interested in these.
        elif (not imageURL.startswith("https://gravatar.com")) and (not imageURL.endswith("_distribution.png")):
            # If some image URL does not fit one of the above two criteria, we should log a warning in case it turns out to be worth saving.
            print(f"WARN: not downloading {imageURL}")

    # Grab a list of all the linked attachments for later downloading.
    attachments = []
    for a in driver.find_elements(By.TAG_NAME, "a"):
        href = a.get_attribute("href")
        if bool(href) and href.startswith("https://app.crowdmark.com/text-attachments/"):
            attachments.append(href)

    # Grab the page source as a string.
    # From now on we will only manipulate this string.
    html = driver.page_source

    # Fetch each image.
    for imageURL in images:
        resp = session.get(imageURL[0], timeout=180)
        assert resp.status_code == 200

        # An image may appear more than once in the page. In other words, the images list may have duplicates.
        # Therefore we perform this replacement one at a time.
        assert html.count(imageURL[0].replace("&", "&amp;")) >= 1
        html = html.replace(imageURL[0].replace("&", "&amp;"), imageURL[1], 1)

        # Write this image to a file.
        with open(f"{course_output_directory}/{imageURL[1]}", 'wb') as f:
            f.write(resp.content)

    # Insert a reference to the local stylesheet.
    assert html.count("<head>") == 1
    html = html.replace("<head>", '<head><link integrity="" rel="stylesheet" data-key="cm-main" href="../stylesheet.css">')

    # Save the HTML file itself.
    with open(f"{course_output_directory}/{assessment_name}.html", "w", encoding="utf-8") as file:
        file.write(html)

    # As a last step, download all attachments.
    for url in attachments:
        download_attachment(driver, course_output_directory, url, session)

def download_attachment(driver, course_output_directory, url, session):
    driver.get(url)
    time.sleep(5) # wait to download attachment

    download_links = [e for e in driver.find_elements(By.TAG_NAME, "a") if e.get_attribute("href") is not None and "usercontent.crowdmark.com" in e.get_attribute("href") and driver.execute_script("return arguments[0].innerHTML", e) != "Download"]
    assert len(download_links) == 1

    download_url = download_links[0].get_attribute("href")
    filename = driver.execute_script("return arguments[0].innerHTML", download_links[0])

    resp = session.get(download_url, timeout=180)
    assert resp.status_code == 200

    with open(f"{course_output_directory}/{filename}", 'xb') as f:
        f.write(resp.content)


def remove_elements_by_css_selector(driver, selector, url):
    while True:
        try:
            # For each element found by the selector, execute some JavaScript to remove it from the page.
            for element in driver.find_elements(By.CSS_SELECTOR, selector):
                driver.execute_script('arguments[0].outerHTML="";', element)
            # At this point we have not encountered any exceptions and we are done.
            return
        except StaleElementReferenceException:
            # This is an indication of a stale DOM, so just log a warning and restart from the beginning.
            print(f"WARN: StaleElementReferenceException while scrubbing {selector} from {url}, restarting.")
            pass


def page_name(url):
    return url.rsplit('/', 1)[-1]

def post_process(working_directory, output_directory):
    srcPath = os.path.join(working_directory, "crowdmark-08e51e713bd0dd31059ff3d65c1b91b4.css")
    destPath = os.path.join(output_directory, "stylesheet.css")
    shutil.copy(srcPath, destPath)

    # Copy fonts to output directory.
    for fontSrcPath in glob(os.path.join(working_directory, "fonts", "*")):
        shutil.copy(fontSrcPath, output_directory)

    # Perform some text replacements on every html file in the output directory.
    for savedHtmlFilePath in glob(os.path.join(output_directory, "**", "*.html"), recursive=True):
        with open(savedHtmlFilePath, "r") as file:
            htmlContent = file.read()

        replacementPairs = [
            # Replacements required to load local fonts instead of remote ones.
            ['?V=2.7.5', ''],
            ['https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/fonts/HTML-CSS/TeX/woff', '..'],
            ['https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/fonts/HTML-CSS/TeX/otf', '..'],
            # For some reason this attribute sometimes appears, but typically only when the assessment is an exam, not a homework.
            ['<img crossorigin="anonymous"', '<img'],
        ]

        for pair in replacementPairs:
            htmlContent = htmlContent.replace(pair[0], pair[1])

        with open(savedHtmlFilePath, "w") as file:
            file.write(htmlContent)


if __name__ == '__main__':
    main()
