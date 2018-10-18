import os
from getpass import getpass
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor

import requests
from tqdm import tqdm
from pyquery import PyQuery
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


login_url = 'https://ninghao.net/user/login'

package_url = 'https://ninghao.net/package/website'

session = requests.session()


def login():
    # 配置chrome启动参数
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-logging')
    # 启动selenium获取cookies
    driver = webdriver.Chrome('chromedriver.exe', chrome_options=chrome_options)
    print('* 启动浏览器成功')
    driver.get(login_url)
    username = input('* 请输入帐号: ')
    password = getpass('* 请输入密码: ')
    driver.find_element_by_id('edit-name').send_keys(username)
    driver.find_element_by_id('edit-pass').send_keys(password)
    driver.find_element_by_id('edit-submit').submit()
    print('* 帐号验证通过,正在提取cookies')
    # 处理cookies
    cookies = '; '.join([item['name'] + '=' + item['value'] for item in driver.get_cookies()])
    driver.quit()
    with open('cookies.txt', 'w') as file:
        file.write(cookies)
    return cookies


def get_download_link(cookies):
    # 装载cookies
    req_headers = {
        'Cookie': cookies,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/69.0.3497.100 Safari/537.36'
    }
    session.headers.update(req_headers)

    video_result = []

    # 获取package信息
    package_html = session.get(package_url).text
    package_doc = PyQuery(package_html)
    package_name = package_doc('h1')[0].text
    print('* 正在处理课程包 - {}...'.format(package_name))
    try:
        os.mkdir(package_name)
    except FileExistsError:
        pass

    # 获取course信息
    course_id_list = [i.text for i in package_doc('.item .value')]
    course_name_list = [i.text.strip() for i in package_doc('.item .header h3')]
    course_href_list = [i.get('href') for i in package_doc('.item .header a')]
    course_info = list(zip(course_id_list, course_name_list, course_href_list))

    for course_id, course_name, course_href in course_info:
        print('* 正在处理课程{}: {}...'.format(course_id, course_name))
        video_download_dir = '{}{}{}.{}{}'.format(package_name, os.path.sep, course_id, course_name, os.path.sep)
        try:
            os.mkdir(video_download_dir)
        except FileExistsError:
            pass
        course_url = 'https://ninghao.net' + course_href
        course_html = session.get(course_url).text
        course_doc = PyQuery(course_html)

        # 获取video信息
        video_list = course_doc('.item.viewed .content a,.item.untouched .content a')
        video_id_list = [i for i in range(1, len(video_list) + 1)]
        video_name_list = [i.text.strip() for i in video_list]
        video_href_list = [i.get('href') for i in video_list]
        video_info = list(zip(video_id_list, video_name_list, video_href_list))
        index = 1
        for video_id, video_name, video_href in video_info:
            print('* 正在处理视频{}: {}...'.format(video_id, video_name))
            video_url = 'https://ninghao.net' + video_href
            video_html = session.get(video_url).text
            video_doc = PyQuery(video_html)
            video_download_link = video_doc('source')[0].get('src')
            # video_file_name = video_download_link.split('/')[-1]
            # video_file_path = video_download_dir + video_file_name
            video_name = video_name.replace(':', '：').replace('/', '#')
            video_file_path = video_download_dir + str(index) + '.' + video_name + '.mp4 '
            video_result.append([video_download_link, video_file_path])
            index += 1
    return video_result


def download_video(download_link, file_path):

    file_stream = session.get(download_link, stream=True)
    with open(file_path, 'wb') as file:
        for chunk in file_stream.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)


def multi_thread_download(download_links):

    with ThreadPoolExecutor(max_workers=4) as threadpool:
        all_task = [threadpool.submit(download_video, link, path) for link, path in download_links]
        for future in tqdm(as_completed(all_task), total=len(all_task), ascii=True, desc='下载进度', unit='video'):
            future.result()


if __name__ == '__main__':
    login()
    with open('cookies.txt') as f:
        login_cookies = f.read()
    # login_cookies = login()
    print('* 模拟登录宁皓网成功...')
    video_download_links = get_download_link(login_cookies)
    multi_thread_download(video_download_links)
