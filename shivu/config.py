class Config(object):
    LOGGER = True

    # Get this value from my.telegram.org/apps
    OWNER_ID = "5147822244"
    sudo_users = ["6507226414", "7938543259", "5147822244",]
    GROUP_ID = "-1002191083108"
    TOKEN = "7535325516:AAEyxQHqlrKMAChi4svzzxtQgtAwjOZMjfI"
    mongo_url = "mongodb+srv://Epic2:w85NP8dEHmQxA5s7@cluster0.tttvsf9.mongodb.net/?retryWrites=true&w=majority"
    PHOTO_URL = ["https://telegra.ph//file/e64337bbc6cdac7e6b178.jpg", "https://telegra.ph/file/ed23556d07d33db18402d.jpg", "https://telegra.ph//file/32556c77847dff110577c.jpg", "https://telegra.ph//file/0650844fc5db4049959bc.jpg"]
    SUPPORT_CHAT = "siya_infoo"
    UPDATE_CHAT = "siya_infoo"
    BOT_USERNAME = "Pick_x_catcher_Bot"
    CHARA_CHANNEL_ID = "-1002059929123"
    api_id = "17944283"
    api_hash = "03f2f561ca86def71fe88d3ae16ed529"

    
class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
