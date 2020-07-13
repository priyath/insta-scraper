import csv
import re
import filters

CSV_BASE_PATH = './core/detail/'
CSV_FILE_NAME = 'details.csv'

# [ 'username', 'biography', 'posts', 'following', 'followers', 'has_profile_pic', 'is_private', 'is_verified',
# 'business_category_name', 'overall_category_name', 'category_enum' ]

FILTERED_ROWS = []
ORIGINAL_ROWS = []

TEST_STRING = 'Join Our Facebook Group'

BUSINESS_EXCLUSION_COUNTER = 0
PERSONAL_WEB_EXCLUSION_COUNTER = 0
DUPLICATE_USERNAME_COUNTER = 0
FOLLOWER_THRESHOLD_COUNTER = 0

PROCESSED_USERNAMES = []

with open(CSV_BASE_PATH + CSV_FILE_NAME, newline='') as file:
    reader = csv.reader(file, delimiter=',', quotechar='"')
    for row in reader:
        # ----------------
        # ignore column row
        if row[4] == 'followers':
            continue
        # -----------------

        ORIGINAL_ROWS.append(row)
        SHOULD_EXCLUDE = False
        USERNAME = row[0].strip()
        FOLLOWERS = int(row[4])

        # duplicate username check
        if USERNAME in PROCESSED_USERNAMES:
            DUPLICATE_USERNAME_COUNTER += 1
            continue

        # filter based on follower count
        if not filters.is_ideal_follower_range(FOLLOWERS):
            FOLLOWER_THRESHOLD_COUNTER += 1
            SHOULD_EXCLUDE = True

        #######################################################
        # bio filters
        bio = row[1]

        # exclude if bio has business owner key
        if filters.should_exclude_based_on_business_owner(bio):
            BUSINESS_EXCLUSION_COUNTER += 1
            SHOULD_EXCLUDE = True

        # exclude if personal website
        if filters.should_exclude_based_on_website(bio, USERNAME):
            PERSONAL_WEB_EXCLUSION_COUNTER += 1
            SHOULD_EXCLUDE = True

        ########################################################
        # filter by category
        category_enum = row[10]

        # exclude if not in one of our categories
        if not filters.is_allowed_category(category_enum):
            SHOULD_EXCLUDE = True

        if not SHOULD_EXCLUDE:
            FILTERED_ROWS.append(row)

        # add to processed usernames
        PROCESSED_USERNAMES.append(USERNAME)

    print('Total count: {}'.format(len(ORIGINAL_ROWS)))
    print('Duplicate count: {}'.format(DUPLICATE_USERNAME_COUNTER))
    print('Unique count: {}'.format(len(ORIGINAL_ROWS) - DUPLICATE_USERNAME_COUNTER))
    print('Filtered count: {}'.format(len(FILTERED_ROWS)))
    print('Business owner exclusions: {}'.format(BUSINESS_EXCLUSION_COUNTER))
    print('Personal website exclusions: {}'.format(PERSONAL_WEB_EXCLUSION_COUNTER))
    print('Follower count exclusions: {}'.format(FOLLOWER_THRESHOLD_COUNTER))
