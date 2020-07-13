import os, sys
import random
import concurrent.futures
import requests
import json
import re
import time
from bs4 import BeautifulSoup
import configparser
import os, errno
import csv

config_path = 'config/config.ini'
followers_path = './core/followers/'

start_time = None
scraped_count = 0


def silent_remove(filename):
    try:
        os.remove(filename)
    except OSError as e: # this would be "except OSError, e:" before Python 2.6
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise # re-raise exception if a different error occurred


columns = ['username', 'biography', 'posts', 'following', 'followers', 'has_profile_pic', 'is_private', 'is_verified',
           'business_category_name', 'overall_category_name', 'category_enum']
target_account = ''
index = None

# load configurations from  config.ini
config = configparser.ConfigParser()
config.read(config_path)
proxy_ports = config.get('Ports', 'proxy_ports').split(',')
control_ports = config.get('Ports', 'control_ports').split(',')
MAX_TOR_INSTANCES = int(config.get('Instances', 'tor_instances').strip())
MAX_WORKERS = int(config.get('Instances', 'max_worker_threads').strip())
FAILED_RETRY_LIMIT = int(config.get('Scrape', 'failed_retry_limit').strip())


def build_proxy_list():
    proxy_add = []
    for i in range(len(proxy_ports)):
        proxy_port = proxy_ports[i]
        proxy_add.append('http://127.0.0.1:' + str(proxy_port).strip())
    return proxy_add


PROXY_ADDRESS = build_proxy_list()

desktop_agents = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/602.2.14 (KHTML, like Gecko) Version/10.0.1 Safari/602.2.14',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'
]


def load_user_list(user_filename):
    print('[{}] Reading user list from {}'.format(target_account, user_filename))
    with open(followers_path + user_filename, 'r') as f:
        user_list = f.readlines()
    return user_list


# check if default profile picture
def does_profile_pic_exist(url):
    split_url = url.split('/')
    img_name = split_url[len(split_url) - 1].strip()
    return not (img_name == '11906329_960233084022564_1448528159_a.jpg')


# generic function to access nested properties
def get_nested(data, *args):
    if args and data:
        element = args[0]
        if element:
            value = data.get(element)
            return value if len(args) == 1 else get_nested(value, *args[1:])


def chunkify(l, n):
    # For item i in a range that is a length of l,
    for i in range(0, len(l), n):
        # Create an index range for l of n items:
        yield l[i:i + n]


def get_recent_post_count(edges):
    return len(edges)


def get_recent_post_like_count(edges):
    total_like_count = 0
    for edge in edges:
        edge_like_count = get_nested(edge, 'node', 'edge_liked_by', 'count')
        total_like_count = total_like_count + edge_like_count

    return total_like_count


def get_recent_post_comment_count(edges):
    total_comment_count = 0

    for edge in edges:
        edge_comment_count = get_nested(edge, 'node', 'edge_media_to_comment', 'count')
        total_comment_count = total_comment_count + edge_comment_count

    return total_comment_count


def get_profile_json(username, user_link, count):
    return_object = {
        'success': False,
        'data': None,
        'username': username.strip(),
        'status_code': None
    }
    try:
        proxy_add = PROXY_ADDRESS[count % MAX_TOR_INSTANCES]
        proxies = {
            "http": 'http://136.244.110.197:8080',
            "https": 'https://136.244.110.197:8080',
        }

        headers = {
            'User-Agent': random.choice(desktop_agents)
        }
        r = requests.get(user_link, headers=headers, timeout=20)

        return_object['status_code'] = r.status_code
        html = r.content
        soup = BeautifulSoup(html, 'lxml')

        script = soup.find('script', text=re.compile('window\._sharedData'))
        json_text = re.search(r'^\s*window\._sharedData\s*=\s*({.*?})\s*;\s*$', script.string,
                              flags=re.DOTALL | re.MULTILINE).group(1)
        user_object = json.loads(json_text).get('entry_data').get('ProfilePage')[0].get('graphql').get('user')

        # extracting data from profile user object
        posts = 1 if get_nested(user_object, 'edge_owner_to_timeline_media', 'count') == 0 else get_nested(user_object,
                                                                                                           'edge_owner_to_timeline_media',
                                                                                                           'count')
        follow = 1 if get_nested(user_object, 'edge_follow', 'count') == 0 else get_nested(user_object, 'edge_follow',
                                                                                           'count')
        followed_by = 1 if get_nested(user_object, 'edge_followed_by', 'count') == 0 else get_nested(user_object,
                                                                                                     'edge_followed_by',
                                                                                                     'count')
        profile_pic_exist = 1 if does_profile_pic_exist(get_nested(user_object, 'profile_pic_url')) else 0
        is_private = 1 if get_nested(user_object, 'is_private') else 0
        is_verified = 1 if get_nested(user_object, 'is_verified') else 0

        business_category_name = get_nested(user_object, 'business_category_name') if get_nested(user_object, 'business_category_name') else ''
        biography = get_nested(user_object, 'biography') if get_nested(user_object, 'biography') else ''
        overall_category_name = get_nested(user_object, 'overall_category_name') if get_nested(user_object, 'overall_category_name') else ''
        category_enum = get_nested(user_object, 'category_enum') if get_nested(user_object, 'category_enum') else ''

        profile_line = [username.strip(), biography.strip(), str(posts), str(follow), str(followed_by), str(
            profile_pic_exist), str(is_private), str(is_verified), business_category_name, overall_category_name, category_enum]

        return_object['data'] = profile_line
        return_object['success'] = True
        print('====================={}: SUCCESS====================='.format(username))
        return return_object

    except Exception as e:
        print('============================ERROR===============================')
        return return_object


def write_to_file(path, mode, content):
    try:
        file = open(followers_path + path, mode)
        file.writelines(content)
        file.close()
    except Exception as e:
        print('[{}] Writing scraped content to file failed.'.format(target_account))
        print(e)
        raise e


def write_to_csv(path, content):
    # write csv
    # writing to csv file
    with open(followers_path + path, 'a', newline='') as csvfile:
        # creating a csv writer object
        csvwriter = csv.writer(csvfile)

        # writing the data rows
        csvwriter.writerows(content)

def save_scraped_data(profile_data, failed_list, deleted_list):
    write_to_csv(target_account + '_model_data.csv', profile_data)
    #write_to_file(target_account + '_failed_list.txt', 'w', failed_list)
    #write_to_file(target_account + '_deactivated_list.txt', 'a', deleted_list)


def initate_scraping(user_list, max_workers=MAX_WORKERS, main_loop_counter=1, failed_retries=0):
    global start_time, scraped_count
    profile_json_requests = []

    # multi-threading implementation for scraping
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        count = 0
        for user in user_list[index:]:
            count = count + 1
            user_link = "http://www.instagram.com/" + user.strip() + '/'
            profile_json_requests.append(executor.submit(get_profile_json, user, user_link, count))

        failed_counter = []
        deleted_counter = []
        processed_counter = 0
        profile_data = [columns]

        for future in concurrent.futures.as_completed(profile_json_requests):
            try:
                data = future.result()
                processed_counter = processed_counter + 1
                if data['success']:
                    profile_data.append(data['data'])
                    scraped_count = scraped_count + 1
                else:
                    if data['status_code'] and data['status_code'] == 404:
                        deleted_counter.append(data['username'] + '\n')
                    else:
                        failed_counter.append(data['username'] + '\n')
                print_str = '[' + str(main_loop_counter) + ']processed ' + str(processed_counter) + '/' + str(
                    len(user_list)) + ' Failed count: ' + str(len(failed_counter))

                if (processed_counter % 50) == 0:
                    print('[{}] processed counter {}/{} failed count {} status_code {}'.format(target_account,
                                                                                                 processed_counter,
                                                                                                 len(user_list),
                                                                                                 len(failed_counter),
                                                                                                 data['status_code']))
                    exec_time = time.time() - start_time
            except Exception as exc:
                print('Something went wrong')
                print(exc)
                # dbHandler.update_queue_status(target_account, 2, dbHandler.FAILED)
                raise

        print('[{}] Iteration complete. total count: {} processed count: {} failed count: {} deleted count: {}'
                    .format(target_account, len(user_list), processed_counter, len(failed_counter), len(deleted_counter)))

        save_scraped_data(profile_data, failed_counter, deleted_counter)

        if len(failed_counter) > 0:
            if failed_retries > FAILED_RETRY_LIMIT:
                print('[{}] Failed retry count exceeded. Script will exit.'.format(target_account))
                # dbHandler.update_queue_status(target_account, 2, dbHandler.FAILED)
                raise Exception('[{}] Retry count exceeded'.format(target_account))

            prev_failed_count = len(user_list)
            current_failed_count = len(failed_counter)
            failed_diff = prev_failed_count - current_failed_count

            print('[{}] Scraped account count: {}'.format(target_account, failed_diff))
            if failed_diff == 0:
                failed_retries += 1
            else:
                failed_retries = 0

            max_workers = min(len(failed_counter), MAX_WORKERS)

            print('[{}] Retrying scrape. Accounts: {} Worker threads {} Failed retry count: {}'
                        .format(target_account, len(failed_counter), int(max_workers), failed_retries))

            initate_scraping(failed_counter, max_workers, (main_loop_counter + 1), failed_retries)


def diff(first, second):
    second = set(second)
    return [item for item in first if item not in second]


def get_user_list(target, rescrape):
    if rescrape:
        user_list_previous = load_user_list(target + '_followers_previous.txt')
        user_list_current = load_user_list(target + '_followers.txt')
        user_list = diff(user_list_current, user_list_previous)
        print('[{}] New users diff: {}'.format(target, len(user_list)))

    else:
        silent_remove(followers_path + target + '_model_data.csv')
        user_list = load_user_list(target + '_followers.txt')

    return user_list


def init(target, rescrape):
    global target_account, start_time

    start_time = time.time()
    target_account = target

    user_list = get_user_list(target, rescrape)
    print('[{}] Scraping {} accounts from {}'.format(target_account, len(user_list), target_account))

    initate_scraping(user_list)
    exec_time = (time.time() - start_time)
    print(exec_time)

init('accounts', False)