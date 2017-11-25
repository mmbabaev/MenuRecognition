

from vk import Session, API

from facebook_sdk.exceptions import FacebookResponseException
from facebook_sdk.facebook import Facebook

facebook = Facebook(
    app_id='126705831315228',
    app_secret='1eab07b5da9a647017cef30bfd4cb063',
    default_graph_version='v2.10',
)


def fb_info(id, token):
    facebook.set_default_access_token(access_token=str(token))

    try:
        response = facebook.get(endpoint='/me?fields=id,name,email,picture')
        print(response)
    except FacebookResponseException as e:
        print e
        return None

    json = response.json_body

    name = json.get("name").split(' ')

    json["first_name"] = name[0]
    json["last_name"] = name[1]
    json["image_url"] = "http://graph.facebook.com/" + id + "/picture?type=square"

    return json


def vk_info(id, token):
    session = Session(access_token=token)
    vk_api = API(session)
    result = vk_api.users.get(user_ids=[0], fields=['photo_200'])[0]

    result['image_url'] = result['photo_200']

    return result
