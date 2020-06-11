#!/usr/bin/python
import logging
import os
import time
import re
# import json
# import urllib
import traceback
# import threading
import utils as _utils
import messages
import traceback

from slack import WebClient, RTMClient
from slack.errors import SlackApiError
from mylog import log
from mylog import W
from mylog import D

LAKEWOOD_CHAVEIRIM_BOT_API_TOKEN = 'xoxp-598678183767-598678184535-1161644462661-440b8f9f94b5c2f3d75fe01419ade10f'

userIDToUserNameDict = {}
# To find this value:
# Go to https://api.slack.com/methods/users.list/test
# click Test
# Find the lkwd_calls user
# Put the id in here
robinstocks_iw = 'U01553LFNUR'

LKWD_CALLS_DISPATCH_BOT_DIRECT_MESSAGE_CHANNEL_ID = 'C0155166R8R'

member_pattern = '(service[\s_\-]?[1-9]|svc[\s_\-]?[1-9]|s[1-9]|[1-9][0-9]/d[1-9][0-9]?|1[0-9][0-9]/d[1-9][0-9]?|1[0-9][0-9]/d1[0-9][0-9]?|[1-9][0-9]/d1[0-9][0-9]|d[1-9][0-9]/[1-9][0-9]|[1-9][0-9]|1[0-9][0-9])'
separator_pattern = '[\s_\-,/]'
sc = None
rtm_client = None
utils = None  # type: _utils.Utils

LOOP_DELAY = .1


# Really, display name
def userName(userID):
    if userID in userIDToUserNameDict:
        return userIDToUserNameDict[userID]
    runSetupTasks()


def runDispatchBot():
    global sc
    global rtm_client
    print('Running disptch bot.')
    print('Creating Slack WebClient...')
    sc = WebClient(token=LAKEWOOD_CHAVEIRIM_BOT_API_TOKEN)
    if os.getenv('DEBUG') == '1':
        sc._logger.setLevel(logging.DEBUG)
    print('Creating Slack RTMClient...')
    rtm_client = RTMClient(token=LAKEWOOD_CHAVEIRIM_BOT_API_TOKEN)
    print('created.')
    global utils
    utils = _utils.Utils(sc)
    while True:
        try:
            print('Running runSetupTasks()...')
            runSetupTasks()
            print('Done.')
            print('Starting rtm_client... this will BLOCK!')
            rtm_client.start()
        except SlackApiError as e:
            print(f'Slack API error, {e.response.get("error")}')
            traceback.print_exc()
        except Exception as e:
            print("Exception!!! " + str(e))
            traceback.print_exc()
        finally:
            print("*** **** RECONNECTING *** ***")
            time.sleep(1)


def runSetupTasks():
    updateUsers()
    utils.updateChannels()


def updateUsers():
    users_obj = utils.call_api("users.list")
    if not users_obj.get('ok'):
        if users_obj.get('error'):
            print(users_obj['error'])
        else:
            print('Unknown error!')
            print(users_obj)
        return
    for member_obj in users_obj['members']:
        if member_obj['deleted']:
            continue
        user_id = member_obj['id']
        user_name = member_obj.get('profile', {}).get('display_name', '')
        if user_name == '':
            print('ERROR! No user_name for member ' + user_id)
        userIDToUserNameDict[user_id] = user_name
    print(userIDToUserNameDict)
    print('dispatchBotID=' + robinstocks_iw)


@RTMClient.run_on(event='reaction_added')
def processRTMReactionAdded(**payload):
    data = payload['data']
    if str(data['user']) == str(robinstocks_iw):
        # ignore
        # print "... by dispatchBot, ignoring..."
        return
    processReactionAdded(data)


@RTMClient.run_on(event='message')
def processRTMMessage(**payload):
    data = payload['data']
    processMessage(data)


@RTMClient.run_on(event='team_join')
@RTMClient.run_on(event='user_change')
def processRTMTeamJoin(**payload):
    updateUsers()

def processReactionAdded(msg_dict):
    emoji_name = msg_dict['reaction']
    if emoji_name == 'runner' or emoji_name == 'running':
        print('its a runner!')
        processRunnerAdded(msg_dict)

    elif emoji_name.startswith('unit_'):
        timestamp = msg_dict['item']['ts']
        channel = utils.channelForChannel(msg_dict['item']['channel'])
        message = messages.findMessage(timestamp, channel)
        user = msg_dict['user']
        username = userName(user)
        if message is not None:
            callnum = message.callNumber()
            utils.markEmojiAdded(username, callnum, emoji_name)
        else:
            log(W, "user covering emoji " + str(emoji_name) + ' added by ' + str(
                username) + ', but message with timestamp ' + str(timestamp) + " not in found :(")

        # remove the 'runner' logo as the bot
        # why?
        # logos_obj=printing_json_api_call("reactions.get", timestamp=msg_ts, channel=ch)
        # reactions_obj = logos_obj['message']['reactions']
        # for reaction_obj in reactions_obj:
        #  if reaction_obj['name']=='runner' or reaction_obj['name']=='running':
        #    if dispatchBotID in reaction_obj['users']:
        #      printing_json_api_call("reactions.remove", name='runner', channel=ch, timestamp=msg_ts)
        #      #print sc.api_call("reactions.add", timestamp=msg_ts, channel=ch, name='lkwd-chaveirim')
        #    break
    elif emoji_name == 'no_pedestrians' or emoji_name == 'x':
        print("call is cancelled via emoji... cancel :runner: and dispatch message")

        timestamp = msg_dict['item']['ts']
        channel = utils.channelForChannel(msg_dict['item']['channel'])
        message = messages.findMessage(timestamp, channel)
        user = msg_dict['user']
        username = userName(user)
        if message is not None:
            callnum = message.callNumber()
            utils.dispatchMessage(str(callnum) + '-000', username)
            #     utils.removeRunnerFromMessage(message) will be done on dispatch return.
        else:
            log(W, "user clicked cancel, but msg_ts=" + timestamp + " not in found :(")
    elif emoji_name == 'shofar':
        print('Second request!')
        timestamp = msg_dict['item']['ts']
        channel = utils.channelForChannel(msg_dict['item']['channel'])
        message = messages.findMessage(timestamp, channel)
        user = msg_dict['user']
        username = userName(user)
        if message is not None:
            callnum = message.callNumber()
            utils.dispatchMessage(str(callnum) + '-222', username)
            #     utils.removeRunnerFromMessage(message) will be done on dispatch return.
            # shofar will be added on dispatch return
        else:
            log(W, "user clicked cancel, but msg_ts=" + timestamp + " not in found :(")


def processRunnerAdded(msg_dict):
    user = msg_dict['user']
    username = userName(user)
    # Have AppEngine send: [Unit (unit)] (call number). They'll direct-message that to us & we'll add the icon then.
    # logo=logoNameFromUsername(username)
    timestamp = msg_dict['item']['ts']
    channel = utils.channelForChannel(msg_dict['item']['channel'])
    # printing_json_api_call("reactions.add", timestamp=msg_ts, channel=callsChannelID, name=logo)
    # # send message to everyone

    # if re.match('\[[0-9]{3}\] .*', )
    # postdata=urllib.urlencode({'user_name': username, 'msg': })
    # urllib.urlopen('https://lakewood-chaveirim.appspot.com/slack/dispatch', )
    message = messages.findMessage(timestamp, channel)
    if message is not None:
        callnum = message.callNumber()
        utils.dispatchMessage(str(callnum), username)
    else:
        log(W, "user clicked covering, but msg_ts=" + timestamp + " not in found :(")

    # remove the 'runner' logo as the bot
    # eh, who cares.
    #
    # logos_obj=printing_json_api_call("reactions.get", timestamp=msg_ts, channel=ch)
    # reactions_obj = logos_obj['message']['reactions']
    # for reaction_obj in reactions_obj:
    #   if reaction_obj['name']=='runner' or reaction_obj['name']=='running':
    #     if dispatchBotID in reaction_obj['users']:
    #       printing_json_api_call("reactions.remove", name='runner', channel=ch, timestamp=msg_ts)
    #       #print sc.api_call("reactions.add", timestamp=msg_ts, channel=ch, name='lkwd-chaveirim')
    #     break
    # utils.removeRunnerFromMessage(message)


def processMessage(msg_dict):
    # new message?

    if 'subtype' in msg_dict and msg_dict['subtype'] == 'message_changed':
        """
    [{u'event_ts': u'1449455820.410369', u'ts': u'1449455820.002106', u'subtype': u'message_changed',
      u'message': {u'text': u'9:36 PM: [190] Support: test 1 To respond, please /dispatch msg',
         u'type': u'message', u'user': u'U0CDGF256', u'ts': u'1449455799.002103',
         u'edited': {u'user': u'U0CDGF256', u'ts': u'1449455820.000000'}},
      u'type': u'message',
      u'hidden': True, u'channel': u'C0C8T9467',
      u'previous_message': {u'text': u'9:36 PM: [190] Support: test 1 To respond, please /dispatch msg', u'type': u'message', u'user': u'U0CDGF256',
        u'ts': u'1449455799.002103', u'edited': {u'user': u'U0CDGF256', u'ts': u'1449455819.000000'}}}]"""
        log(D, 'message changed, ignoring...')
        return

    # for now send all messages to #calls and read messages from there. New version can be smarter.
    if 'channel' in msg_dict and msg_dict['channel'] == LKWD_CALLS_DISPATCH_BOT_DIRECT_MESSAGE_CHANNEL_ID:
        log(D, "Direct message! Processing...")
        handleDirectMessage(msg_dict)
        return
    else:
        log(D, f"Not a direct message. channel={msg_dict.get('channel')}. Ignoring.")


def handleDirectMessage(msg_dict):
    if not 'text' in msg_dict:
        log(W, 'No text in message: ' + str(msg_dict))
        return
    text = msg_dict['text']
    # text = re.sub('[<][^|]+[|]([^>]+)[>]', r'\1', text)
    # instead let's let Slack parse these
    isDispatchMessage = utils.isDispatchMessage(text)
    if isDispatchMessage:
        channel = utils.channelForChannel('#calls')  # '#test'
        call_number = utils.callNumberForDispatchMessage(text)
    else:
        channel = utils.channelForChannel('#responses')  # '#test2'
        call_number = None
    m = utils.postMessage(channel, text, call_number, bold=isDispatchMessage, save=isDispatchMessage)
    if m is None:
        return
    if isDispatchMessage:
        utils.addRunnerToMessage(m)
    else:
        processNonDispatchMessage(m)


def processNonDispatchMessage(m):
    text = m.text()
    # dispatcher marked user as responding ?
    dispatcher_marked_user_as_responding_pattern = '1?[0-9]:[0-5][0-9] [ap]m: \[unit (.*?)\] ' + \
                                                   member_pattern + separator_pattern + \
                                                   member_pattern + '?' + separator_pattern + '?' + \
                                                   member_pattern + '?' + separator_pattern + '?' + \
                                                   member_pattern + '?' + separator_pattern + '?' + \
                                                   member_pattern + '?' + separator_pattern + '?' + \
                                                   member_pattern + '?' + separator_pattern + '?' + \
                                                   member_pattern + '?' + separator_pattern + '?' + \
                                                   member_pattern + '?' + separator_pattern + '?' + \
                                                   member_pattern + '?' + separator_pattern + '?' + \
                                                   '([3-9][0-9]{2})'
    match = re.match(dispatcher_marked_user_as_responding_pattern, text.lower())
    if match is not None:
        processDispatcherMarkedUnitsAsResponding(m, match)
        return
    else:
        log(D, "Message is not a 'dispatcher marked unit as responding' message")

    # user responding?
    user_responding_match = re.match('1?[0-9]:[0-5][0-9] [AP]M: \[Unit (.*?)\] ([0-9]{3})(.*)', text)
    if user_responding_match is not None:
        processUserResponding(m, user_responding_match)
        return
    else:
        log(D, "Message is not a 'user marking themselves as responding' message")


def processDispatcherMarkedUnitsAsResponding(covering_message, match):
    unit_number = match.group(1)
    callnum = match.group(11)
    units = [match.group(2)]
    for i in range(3, 11):
        if match.group(i) is not None:
            units.append(match.group(i))

    message = messages.findMessage(call_number=callnum)
    if message is None:
        log(W, 'Can\'t update original message, no match found for call num=' + callnum)
        return
    for unit_number in units:
        utils.markUnitAsCoveringMessage(message, unit_number)

    first_unit = None
    if len(units):
        first_unit = units[0]

    utils.updateMessage(message)
    utils.scheduleMessageForClearing(message)
    utils.maybeSendFirstText(message, first_unit)


def processUserResponding(response_message, match):
    unit_number = match.group(1)
    callnum = match.group(2)
    extra = match.group(3)

    logo_name = utils.logoNameForUnitNumber(unit_number)

    message = messages.findMessage(call_number=callnum)
    if message is None:
        log(W, 'Could not find matching dispatch message for call number ' + callnum)
        return

    if re.match('[ \-/_]+000', extra) is not None:
        utils.removeRunnerFromMessage(message)
        utils.addNoPedestriansToMessage(message)
        utils.scheduleMessageForClearing(message)
        utils.updateMessage(message)  # in case it was 222'd
        return
    if re.match('[ \-/_]+111', extra) is not None:
        # Covered by phone. Same as cancel.
        utils.removeRunnerFromMessage(message)
        utils.addNoPedestriansToMessage(message)
        utils.scheduleMessageForClearing(message)
        return
    if extra.startswith('-222') or extra.startswith('-222'):
        # print "call " + callnum + " - second reminder! Adding a shofar :)"
        utils.addShofarToMessage(message)
        utils.updateMessage(message, red=True)
        return

    if re.search('\(?[0-9]{3}\)?[ \-]?[0-9]{3}[ \-]?[0-9]{4}', extra) is not None:
        print("extra contains a phone number, probably dispatcher forgot ###")
        return

    # print "assuming unit " + unit_number + " is covering call " + callnum + " based on extra=" + extra
    # don't add bot's user logo responding, if dispatcher already added it
    # eh... who cares.
    #
    # add_logo = True
    # logos_obj=json.loads(sc.api_call("reactions.get", timestamp=msg_ts, channel=callsChannelID))
    # reactions_obj = logos_obj['message']['reactions']
    # for reaction_obj in reactions_obj:
    #   if reaction_obj['name']==logo:
    #     #if dispatchBotID in reaction_obj['users']:
    #     #  print sc.api_call("reactions.remove", name='runner', channel=callsChannelID, timestamp=msg_ts)
    #     #  #print sc.api_call("reactions.add", timestamp=msg_ts, channel=ch, name='lkwd-chaveirim')
    #     #break
    #     add_logo = False
    # if add_logo:
    #  printing_json_api_call("reactions.add", timestamp=msg_ts, channel=callsChannelID, name=logo)
    #  printing_json_api_call('chat.update',ts=msg_ts,channel=callsChannelID,text=timestampToTextDict[msg_ts],attachments=timestampToAttachmentsArrayDict[msg_ts],parse='none')
    utils.updateMessage(message)
    utils.markUnitAsCoveringMessage(message, unit_number)
    utils.scheduleMessageForClearing(message)
    utils.maybeSendFirstText(message, unit_number)
    return


if __name__ == '__main__':
    runDispatchBot()
