from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from shivu import shivuu, SUPPORT_CHAT, user_collection, collection
import os
import math
from datetime import datetime

def sc(text):
    """Small caps converter"""
    m = {'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ғ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'s','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'}
    return ''.join(m.get(c.lower(), c) for c in text)

PASS_CFG = {
    'free': {'name': 'ғʀᴇᴇ', 'mul': '1.0x'},
    'premium': {'name': 'ᴘʀᴇᴍɪᴜᴍ', 'mul': '1.5x'},
    'elite': {'name': 'ᴇʟɪᴛᴇ', 'mul': '2.0x'}
}

async def get_stats(uid):
    """Get all user stats"""
    u = await user_collection.find_one({'id': uid})
    if not u:
        return None
    
    # Collection
    chars = u.get('characters', [])
    total = len(chars)
    unique = len(set(c.get('id') for c in chars if isinstance(c, dict) and c.get('id')))
    db_total = await collection.count_documents({})
    completion = (unique / db_total * 100) if db_total > 0 else 0
    
    # Rank
    pipeline = [{"$project": {"id": 1, "cnt": {"$cond": {"if": {"$isArray": "$characters"}, "then": {"$size": "$characters"}, "else": 0}}}}, {"$sort": {"cnt": -1}}]
    ranks = await user_collection.aggregate(pipeline).to_list(length=None)
    rank = next((i+1 for i, r in enumerate(ranks) if r.get('id') == uid), 0)
    
    # Finance
    wallet = u.get('balance', 0)
    bank = u.get('bank', 0)
    wealth = wallet + bank
    wealth_rank = await user_collection.count_documents({'balance': {'$gt': wealth}}) + 1
    
    # Loan
    loan = u.get('loan_amount', 0)
    loan_due = u.get('loan_due_date')
    loan_days = (loan_due - datetime.utcnow()).days if loan_due and isinstance(loan_due, datetime) else 0
    
    # Game
    xp = u.get('user_xp', 0)
    lvl = min(math.floor(math.sqrt(max(xp, 0) / 100)) + 1, 100)
    tier = 'ᴇ' if lvl <= 10 else 'ᴅ' if lvl <= 30 else 'ᴄ' if lvl <= 50 else 'ʙ' if lvl <= 90 else 's'
    next_xp = ((lvl) ** 2) * 100
    need_xp = next_xp - xp
    tokens = u.get('tokens', 0)
    
    # Pass
    pd = u.get('pass_data', {})
    p_tier = pd.get('tier', 'free')
    p_exp = pd.get('elite_expires') if p_tier == 'elite' else pd.get('premium_expires') if p_tier == 'premium' else None
    p_days = (p_exp - datetime.utcnow()).days if p_exp and isinstance(p_exp, datetime) and p_exp > datetime.utcnow() else (None if p_tier == 'free' else 0)
    if p_days == 0 and p_tier != 'free':
        p_tier = 'free'
    p_cfg = PASS_CFG.get(p_tier, PASS_CFG['free'])
    p_claims = pd.get('weekly_claims', 0)
    p_streak = pd.get('streak_count', 0)
    
    return {
        'total': total, 'unique': unique, 'db_total': db_total, 'completion': completion, 'rank': rank,
        'wallet': wallet, 'bank': bank, 'wealth': wealth, 'wealth_rank': wealth_rank,
        'loan': loan, 'loan_days': loan_days,
        'xp': xp, 'lvl': lvl, 'tier': tier, 'need_xp': need_xp, 'tokens': tokens,
        'p_tier': p_tier, 'p_name': p_cfg['name'], 'p_mul': p_cfg['mul'], 'p_days': p_days, 'p_claims': p_claims, 'p_streak': p_streak
    }

@shivuu.on_message(filters.command("sinfo"))
async def profile(client, message):
    # Get target
    if message.reply_to_message:
        tid = message.reply_to_message.from_user.id
    elif len(message.command) == 1:
        tid = message.from_user.id
    else:
        try:
            tid = int(message.command[1])
        except:
            tid = message.text.split(None, 1)[1]
    
    m = await message.reply_text(sc("loading..."))
    
    try:
        u = await shivuu.get_users(tid)
        s = await get_stats(tid)
        
        if not s:
            return await m.edit(f"<blockquote>{sc('user not found')}</blockquote>", parse_mode="HTML")
        
        name = sc(u.first_name)
        uname = u.username or sc("none")
        
        # Build caption
        cap = f"""<blockquote expandable>{sc('hunter license v2.0')}</blockquote>

<blockquote expandable>{sc('profile')}
{sc('name')}: {name}
{sc('id')}: <code>{tid}</code>
{sc('username')}: @{uname}</blockquote>

<blockquote expandable>{sc('collection')}
{sc('owned')}: <code>{s['total']:,}</code>
{sc('unique')}: <code>{s['unique']}</code> / <code>{s['db_total']}</code>
{sc('complete')}: <code>{s['completion']:.1f}%</code>
{sc('rank')}: <code>#{s['rank']}</code></blockquote>

<blockquote expandable>{sc('finance')}
{sc('wallet')}: <code>{s['wallet']:,}</code>
{sc('bank')}: <code>{s['bank']:,}</code>
{sc('total')}: <code>{s['wealth']:,}</code>
{sc('rank')}: <code>#{s['wealth_rank']}</code>"""
        
        if s['loan'] > 0:
            cap += f"\n{sc('loan')}: <code>{s['loan']:,}</code>"
            if s['loan_days'] > 0:
                cap += f" ({s['loan_days']}ᴅ)"
        
        cap += f"""</blockquote>

<blockquote expandable>{sc('game')}
{sc('level')}: <code>{s['lvl']}</code> / <code>100</code>
{sc('rank')}: <code>{s['tier']}</code>
{sc('xp')}: <code>{s['xp']:,}</code>
{sc('next')}: <code>{s['need_xp']:,}</code>
{sc('tokens')}: <code>{s['tokens']:,}</code></blockquote>

<blockquote expandable>{sc('pass')}
{sc('tier')}: <code>{s['p_name']}</code>"""
        
        if s['p_days'] is not None and s['p_days'] > 0:
            cap += f" ({s['p_days']}ᴅ)"
        
        cap += f"""
{sc('mult')}: <code>{s['p_mul']}</code>
{sc('claims')}: <code>{s['p_claims']}</code> / <code>6</code>
{sc('streak')}: <code>{s['p_streak']}</code></blockquote>"""
        
        # Buttons
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(sc("balance"), callback_data=f"si_b_{tid}"), InlineKeyboardButton(sc("games"), callback_data=f"si_g_{tid}")],
            [InlineKeyboardButton(sc("collection"), callback_data=f"si_c_{tid}"), InlineKeyboardButton(sc("pass"), callback_data=f"si_p_{tid}")],
            [InlineKeyboardButton(sc("refresh"), callback_data=f"si_r_{tid}")],
            [InlineKeyboardButton(sc("support"), url=f"https://t.me/{SUPPORT_CHAT}")]
        ])
        
        # Get photo
        photo = u.photo.big_file_id if u.photo else None
        
        if photo:
            try:
                p = await shivuu.download_media(photo)
                await message.reply_photo(p, caption=cap, reply_markup=kb, parse_mode="HTML")
                await m.delete()
                os.remove(p)
            except:
                await m.delete()
                await message.reply_photo("https://files.catbox.moe/z8fhwx.jpg", caption=cap, reply_markup=kb, parse_mode="HTML")
        else:
            await m.delete()
            await message.reply_photo("https://files.catbox.moe/z8fhwx.jpg", caption=cap, reply_markup=kb, parse_mode="HTML")
    
    except Exception as e:
        print(f"sinfo error: {e}")
        import traceback
        traceback.print_exc()
        await m.edit(f"<blockquote>{sc('error')}</blockquote>", parse_mode="HTML")

@shivuu.on_callback_query(filters.regex(r"^si_"))
async def sinfo_cb(client, cq):
    d = cq.data
    parts = d.split("_")
    act = parts[1]
    tid = int(parts[2])
    
    try:
        s = await get_stats(tid)
        if not s:
            return await cq.answer(sc("user not found"), show_alert=True)
        
        back = InlineKeyboardMarkup([[InlineKeyboardButton(sc("back"), callback_data=f"si_r_{tid}")]])
        
        if act == "r":  # Refresh
            u = await shivuu.get_users(tid)
            name = sc(u.first_name)
            uname = u.username or sc("none")
            
            cap = f"""<blockquote expandable>{sc('hunter license v2.0')}</blockquote>

<blockquote expandable>{sc('profile')}
{sc('name')}: {name}
{sc('id')}: <code>{tid}</code>
{sc('username')}: @{uname}</blockquote>

<blockquote expandable>{sc('collection')}
{sc('owned')}: <code>{s['total']:,}</code>
{sc('unique')}: <code>{s['unique']}</code> / <code>{s['db_total']}</code>
{sc('complete')}: <code>{s['completion']:.1f}%</code>
{sc('rank')}: <code>#{s['rank']}</code></blockquote>

<blockquote expandable>{sc('finance')}
{sc('wallet')}: <code>{s['wallet']:,}</code>
{sc('bank')}: <code>{s['bank']:,}</code>
{sc('total')}: <code>{s['wealth']:,}</code>
{sc('rank')}: <code>#{s['wealth_rank']}</code>"""
            
            if s['loan'] > 0:
                cap += f"\n{sc('loan')}: <code>{s['loan']:,}</code>"
                if s['loan_days'] > 0:
                    cap += f" ({s['loan_days']}ᴅ)"
            
            cap += f"""</blockquote>

<blockquote expandable>{sc('game')}
{sc('level')}: <code>{s['lvl']}</code> / <code>100</code>
{sc('rank')}: <code>{s['tier']}</code>
{sc('xp')}: <code>{s['xp']:,}</code>
{sc('next')}: <code>{s['need_xp']:,}</code>
{sc('tokens')}: <code>{s['tokens']:,}</code></blockquote>

<blockquote expandable>{sc('pass')}
{sc('tier')}: <code>{s['p_name']}</code>"""
            
            if s['p_days'] is not None and s['p_days'] > 0:
                cap += f" ({s['p_days']}ᴅ)"
            
            cap += f"""
{sc('mult')}: <code>{s['p_mul']}</code>
{sc('claims')}: <code>{s['p_claims']}</code> / <code>6</code>
{sc('streak')}: <code>{s['p_streak']}</code></blockquote>"""
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(sc("balance"), callback_data=f"si_b_{tid}"), InlineKeyboardButton(sc("games"), callback_data=f"si_g_{tid}")],
                [InlineKeyboardButton(sc("collection"), callback_data=f"si_c_{tid}"), InlineKeyboardButton(sc("pass"), callback_data=f"si_p_{tid}")],
                [InlineKeyboardButton(sc("refresh"), callback_data=f"si_r_{tid}")],
                [InlineKeyboardButton(sc("support"), url=f"https://t.me/{SUPPORT_CHAT}")]
            ])
            
            await cq.edit_message_caption(cap, reply_markup=kb, parse_mode="HTML")
            await cq.answer(sc("refreshed"))
        
        elif act == "b":  # Balance
            cap = f"""<blockquote expandable>{sc('financial system')}</blockquote>

<blockquote expandable>{sc('account')}
{sc('wallet')}: <code>{s['wallet']:,}</code>
{sc('bank')}: <code>{s['bank']:,}</code>
{sc('total')}: <code>{s['wealth']:,}</code>
{sc('rank')}: <code>#{s['wealth_rank']}</code>"""
            
            if s['loan'] > 0:
                cap += f"\n{sc('loan')}: <code>{s['loan']:,}</code>"
                if s['loan_days'] > 0:
                    cap += f"\n{sc('due')}: <code>{s['loan_days']}</code> {sc('days')}"
            
            cap += f"</blockquote>\n\n<blockquote>{sc('use /bal for menu')}</blockquote>"
            
            await cq.edit_message_caption(cap, reply_markup=back, parse_mode="HTML")
            await cq.answer()
        
        elif act == "g":  # Games
            prog = min(100, int((s['xp'] / (((s['lvl']) ** 2) * 100)) * 100)) if s['lvl'] < 100 else 100
            bar = '█' * (prog // 10) + '░' * (10 - prog // 10)
            
            cap = f"""<blockquote expandable>{sc('game matrix')}</blockquote>

<blockquote expandable>{sc('stats')}
{sc('level')}: <code>{s['lvl']}</code> / <code>100</code>
{sc('rank')}: <code>{s['tier']}</code>
{sc('xp')}: <code>{s['xp']:,}</code>
{sc('next')}: <code>{s['need_xp']:,}</code>
{sc('tokens')}: <code>{s['tokens']:,}</code>

{sc('progress')}
{bar} <code>{prog}%</code></blockquote>

<blockquote>{sc('games')}
/sbet /roll /gamble
/basket /dart /stour /riddle</blockquote>"""
            
            await cq.edit_message_caption(cap, reply_markup=back, parse_mode="HTML")
            await cq.answer()
        
        elif act == "c":  # Collection
            prog = int(s['completion'])
            bar = '█' * (prog // 10) + '░' * (10 - prog // 10)
            
            cap = f"""<blockquote expandable>{sc('collection system')}</blockquote>

<blockquote expandable>{sc('database')}
{sc('owned')}: <code>{s['total']:,}</code>
{sc('unique')}: <code>{s['unique']}</code>
{sc('total')}: <code>{s['db_total']}</code>
{sc('complete')}: <code>{s['completion']:.1f}%</code>
{sc('rank')}: <code>#{s['rank']}</code>

{sc('progress')}
{bar} <code>{prog}%</code></blockquote>

<blockquote>{sc('use /harem to view')}</blockquote>"""
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(sc("back"), callback_data=f"si_r_{tid}"), InlineKeyboardButton(sc("view"), switch_inline_query_current_chat=f"collection.{tid}")]
            ])
            
            await cq.edit_message_caption(cap, reply_markup=kb, parse_mode="HTML")
            await cq.answer()
        
        elif act == "p":  # Pass
            cap = f"""<blockquote expandable>{sc('pass system')}</blockquote>

<blockquote expandable>{sc('membership')}
{sc('tier')}: <code>{s['p_name']}</code>"""
            
            if s['p_days'] is not None and s['p_days'] > 0:
                cap += f"\n{sc('expires')}: <code>{s['p_days']}</code> {sc('days')}"
            
            cap += f"""
{sc('mult')}: <code>{s['p_mul']}</code>
{sc('claims')}: <code>{s['p_claims']}</code> / <code>6</code>
{sc('streak')}: <code>{s['p_streak']}</code> {sc('weeks')}</blockquote>

<blockquote>{sc('use /pass for details')}</blockquote>"""
            
            await cq.edit_message_caption(cap, reply_markup=back, parse_mode="HTML")
            await cq.answer()
    
    except Exception as e:
        print(f"callback error: {e}")
        await cq.answer(sc("error"), show_alert=True)