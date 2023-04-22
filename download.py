import time

from selenium import webdriver
from selenium.webdriver.common.by import By
import os


def main():
    driver = webdriver.Chrome()
    driver.get("https://app.crowdmark.com/sign-in/waterloo")

    input("Enter any random string to indicate you logged in: ")

    assert "Crowdmark" in driver.title
    working_directory = os.getcwd()

    output_directory = os.path.join(working_directory, "output")
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    download_assessments_for_ith_page(driver, output_directory, 1)


def download_assessments_for_ith_page(driver, output_directory, starting_page):
    start_time = time.time()
    page_num = starting_page
    # for each page in crowdmark, install each assessment
    while True:
        driver.get(f"https://app.crowdmark.com/student/courses?page={page_num}")
        time.sleep(3)  # wait for page to load. For some reason driver.get doesn't wait for the entire page to load

        course_list = driver.find_element(By.CLASS_NAME, "student-dashboard__course-list")

        a_tags = course_list.find_elements(By.TAG_NAME, "a")

        if len(a_tags) == 0:
            # there are no more links on this page, so we have scrapped all the assessments
            end_time = time.time()
            elapsed_time = end_time - start_time
            print("finished downloading in: ", elapsed_time, " seconds!")
            driver.close()
            exit(0)

        urls = [a_tag.get_attribute("href") for a_tag in a_tags]
        for url in urls:
            download_assessments_for_course(driver, output_directory, url)

        page_num += 1


def download_assessments_for_course(driver, output_directory, url):
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
        download_assessment(driver, course_output_directory, assessment_url)


def download_assessment(driver, course_output_directory, url):
    driver.get(url)
    time.sleep(5)  # wait for page to load. For some reason driver.get doesn't wait for the entire page to load
    assessment_name = page_name(url)
    html = driver.page_source
    with open(f"{course_output_directory}/{assessment_name}.html", "w", encoding="utf-8") as file:
        file.write(html)


def page_name(url):
    return url.rsplit('/', 1)[-1]


if __name__ == '__main__':
    main()
