from instagram_private_api import Client
import time
import configparser
import logging
import json
import math
import http
import codecs
import os.path

logger = logging.getLogger("rq.worker.grab")

config_path = 'config/config.ini'
followers_path = './core/followers/'
settings_file_path = 'config/login_cache.json'

INCREMENT = 5000

# load configurations from  config.ini
try:
    config = configparser.ConfigParser()
    config.read(config_path)
    username = config.get('Credentials', 'username').strip()
    password = config.get('Credentials', 'password').strip()
    scrape_limit = int(config.get('Scrape', 'scrape_limit').strip())
except Exception as e:
    print('Error reading configuration details from config.ini')
    print(e)
    raise


def to_json(python_object):
    if isinstance(python_object, bytes):
        return {'__class__': 'bytes',
                '__value__': codecs.encode(python_object, 'base64').decode()}
    raise TypeError(repr(python_object) + ' is not JSON serializable')


def from_json(json_object):
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object


def on_login_callback(api, new_settings_file):
    cache_settings = api.settings
    with open(new_settings_file, 'w') as outfile:
        json.dump(cache_settings, outfile, default=to_json)
        print('SAVED: {0!s}'.format(new_settings_file))


def grab_followers(target_account, scrape_percentage, rescrape):
    target = target_account
    followers = []

    # authenticate
    try:
        if not os.path.isfile(settings_file_path):
            print('[{}] Logging in'.format(target_account))
            print('Username: {} Password: {}'.format(username, password))
            api = Client(username, password, on_login=lambda x: on_login_callback(x, settings_file_path))
        else:
            with open(settings_file_path) as file_data:
                cached_settings = json.load(file_data, object_hook=from_json)
            print('[{}] Reusing settings: {}'.format(target_account, settings_file_path))

            device_id = cached_settings.get('device_id')
            # reuse auth settings
            api = Client(
                username, password,
                settings=cached_settings)
    except Exception as e:
        print('Authentication failed')
        print(e)
        # dbHandler.update_queue_status(target, 1, dbHandler.FAILED)
        raise

    start = time.time()

    try:
        result = api.username_info(target)
        follower_count = result['user']['following_count']
        user_id = result['user']['pk']

        scrape_limit = math.ceil((follower_count * scrape_percentage)/100)
        print('[{}] Grabbing {} of followers for account {}'.format(target_account, scrape_limit, target_account))

        # retrieve first batch of followers
        rank_token = Client.generate_uuid()
        results = api.user_following(user_id, rank_token=rank_token)
        followers.extend(results.get('users', []))
        next_max_id = results.get('next_max_id')

        count = 1

        # main loop where the scraping happens
        periodic_val = INCREMENT
        while next_max_id:
            try:
                results = api.user_following(user_id, rank_token=rank_token, max_id=next_max_id)
                followers.extend(results.get('users', []))

                next_max_id = results.get('next_max_id')
                count += 1
                print('[{}] Followers scraped: {}/{}'.format(target_account, len(followers), scrape_limit))

                if len(followers) >= scrape_limit:  # limit scrape
                    break
                time.sleep(2)

            except http.client.IncompleteRead as e:
                print('[{}] Incomplete read exception. Lets retry'.format(target_account))
                continue
            except ConnectionResetError as e:
                print('[{}] Connection reset error. Lets sleep for a minute'.format(target_account))
                time.sleep(60)
                continue

    except Exception as e:
        print('[{}] Main loop failed'.format(target_account))
        print(e)
        # dbHandler.update_queue_status(target, 1, dbHandler.FAILED)
        raise

    followers.sort(key=lambda x: x['pk'])
    print('[{}] Grabbing complete'.format(target_account))

    # if this is a rescrape, rename previous result file to identify diff
    if rescrape:
        try:
            print('[{}] Renaming previous grab results'.format(target_account))
            os.rename(followers_path + str(target) + "_followers.txt", followers_path + str(target) + "_followers_previous.txt")
        except Exception as e:
            print('Failed when writing results to file')
            print(e)
            # dbHandler.update_queue_status(target, 1, dbHandler.FAILED)
            raise

    try:
        # write execution results to file
        # TODO: paths to be read from config files
        with open(followers_path + str(target) + "_followers.txt", "w") as text_file:
            for follower in followers:
                text_file.write("%s\n" % follower['username'])
    except Exception as e:
        print('Failed when writing results to file')
        print(e)
        # dbHandler.update_queue_status(target, 1, dbHandler.FAILED)
        raise

    print('[{}] Successfully written to file'.format(target_account))

    execution_time = (time.time() - start)


grab_followers('jesssusgomez', 100, False)