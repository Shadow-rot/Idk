class Config(object):
    LOGGER = True

    # Get this value from my.telegram.org/apps
    OWNER_ID = "6584789596"
    sudo_users = ["5630057244", "2010819209", "5702598840", "6101457748", "6154972031", "1735664760", "7036005233", "6100011620", "7297953309", "6412447141", "7244871367", "5530116994", "6584789596", "949302414"]
    GROUP_ID = "-1002000314620"
    TOKEN = "6600186454:AAE066bOjW327LQX5WsIACvTz8NCK5yBal4"
    mongo_url = "mongodb+srv://Epic2:w85NP8dEHmQxA5s7@cluster0.tttvsf9.mongodb.net/?retryWrites=true&w=majority"
    PHOTO_URL = ["https://telegra.ph//file/e64337bbc6cdac7e6b178.jpg", "https://telegra.ph/file/ed23556d07d33db18402d.jpg", "https://telegra.ph//file/32556c77847dff110577c.jpg", "https://telegra.ph//file/0650844fc5db4049959bc.jpg"]
    SUPPORT_CHAT = "Grabbing_Your_WH_Group"
    UPDATE_CHAT = "FLEX_BOTS_NEWS"
    BOT_USERNAME = "Grabbing_Your_Waifu_Bot"
    CHARA_CHANNEL_ID = "-1002009998662"
    api_id = "20533795"
    api_hash = "f6cadf28523943f525e706e6ace8a250"

    
class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
