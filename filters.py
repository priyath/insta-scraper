import re

BUSINESS_OWNER_EXCLUDE = ['Co-owner', 'Owner', 'Founder', 'Co-founder', 'CEO', 'My brand']

ALLOWED_URLS = ['youtube', '21button', 'liketoknow', 'linkt', 'depop', 'amazon', 'etsy', 'bit.ly', 'app.21',
                'facebook', 'linkin', 'linkedin', 'twitter', 'youtu', 'tapmybio', 'allmylinks', 'pinterest',
                'patreon', 'cameo']

IMPORTANT_CATS = ['DIGITAL_CREATOR', 'PERSONAL_BLOG', 'BLOGGER', 'TOPIC_JUST_FOR_FUN', 'PERSON',
                  'TOPIC_SHOPPING_RETAIL', 'HEALTH_BEAUTY', 'FASHION_DESIGNER', 'FASHION_MODEL', 'NOT_A_BUSINESS']


def is_allowed_category(category_enum):
    if category_enum in IMPORTANT_CATS:
        return True
    return False


def is_ideal_follower_range(follower_count):
    return 300000 < follower_count < 750000


def should_exclude_based_on_business_owner(bio_str):
    for key in BUSINESS_OWNER_EXCLUDE:
        if key in bio_str:
            return True
        return False


def find_url(string):
    # findall() has been used
    # with valid conditions for urls in string
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, string)
    return [x[0] for x in url]


# exclude if first three letters of username is available in url
def should_exclude_based_on_website(bio_str, username):
    partial_username = username[:3]
    urls = find_url(bio_str)

    for url in urls:
        lower_url = url.lower()
        for key in ALLOWED_URLS:
            if key in lower_url:
                return False
        if partial_username in url:
            return True
    return False

