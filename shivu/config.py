class Config(object):
    LOGGER = True

    # Get this value from my.telegram.org/apps
    OWNER_ID = "5147822244"
    sudo_users = ["8297659126", "8420981179", "5147822244", "7843303499", "7435049371", "6863917190", "1201153141", "7410843798"]
    GROUP_ID = "-1002191083108"
    TOKEN = "7688322975:AAGe-E3psXNoEPxcM0Ek809uztcD22UkQIE"
    mongo_url = "mongodb+srv://Epic2:w85NP8dEHmQxA5s7@cluster0.tttvsf9.mongodb.net/?retryWrites=true&w=majority"
    PHOTO_URL = ["https://telegra.ph//file/e64337bbc6cdac7e6b178.jpg", "https://telegra.ph/file/ed23556d07d33db18402d.jpg", "https://telegra.ph//file/32556c77847dff110577c.jpg", "https://telegra.ph//file/0650844fc5db4049959bc.jpg"]
    SUPPORT_CHAT = "PICK_X_SUPPORT"
    UPDATE_CHAT = "PICK_X_UPDATE"
    BOT_USERNAME = "shadwo_pro_bot"
    CHARA_CHANNEL_ID = "-1002621325936"
    api_id = "21705508"
    api_hash = "1d590f4c3d2029a7ef7df087707d7441"

    
class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
