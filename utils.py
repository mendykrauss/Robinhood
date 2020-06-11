#!/usr/bin/python

#import time
import re
import json
#import logging
import time
import traceback
import urllib.request, urllib.parse, urllib.error
import requests
#import traceback
import threading

from slack.errors import SlackApiError

import messages

from mylog import log
from mylog import D
from mylog import W
from mylog import E
#from mylog import E


from messages import Message
#from slackclient import SlackClient
#from twilio.rest import Client

import unicodedata

LAKEWOOD_CHAVEIRIM_BOT_API_TOKEN='xoxp-598678183767-598678184535-1161644462661-440b8f9f94b5c2f3d75fe01419ade10f'
#TWILIO_SID='AC4531abd362e2e3ffbe066989c81df4b59'
#TWILIO_AUTH_TOKEN='4c1ca2aad3efc28aa5e8963309cbeb165'

#QUEUED_MESSAGES_FILE = '/home/flyashi/queued_messages.txt'


class Utils():
  _sc = None
  _userIDToUsernameMap = {}
  _channel_name_to_id_dict = {}
  #_twilio = None

  def __init__(self, sc):
    self._sc=sc
    #self._twilio = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

  def call_api(self, method, **kwargs):
    log(D, "api: " + method + " kwargs: " + str(kwargs))
    # DEBUG ONLY
    #if 'chat' in method or 'reaction' in method:
    #  return {}
    max_attempts = 3
    ret = None
    for i in range(3):
      try:
        ret=self._sc.api_call(method, data=kwargs)
        break
      except SlackApiError as e:
        log(E, f'Slack API error, {e.response.get("error")}')
        log(E, traceback.format_exc())
        log(E, f'Full response: {e.response}')
        time.sleep(2**i)
      except Exception as e:
        log(W, f'method call {method} failed, attempt {i+1} of {max_attempts}')
        log(W, traceback.format_exc())
        time.sleep(2**i)
    if ret is None:
      log(E, 'api response failed after {} attempts'.format(max_attempts))
      return {'ok': False}
    log(D, f"api response: type={type(ret)} val={ret}")
    if type(ret) == str:
      try:
        json_obj = json.loads(ret)
      except:
        log(D, "JSON conversion failed for " + method + " :(")
        return {"ok": False}
      log(D, "Converted to JSON.")
      return json_obj
    else:
      log(D, "response returned as is.")
      return ret

  def moveMessageFromCallsToCleared(self, message):
    if not message or not isinstance(message, Message):
      log(W, "Invalid message: " + str(message))
      return
    message_text=message.text()
    attachments=message.attachmentsArray()
    if message.channel() != self.channelForChannel('#calls'):  # '#test':
      log(W, 'Trying to move message from calls to cleared, but it\'s not in #calls! msg=' + str(message))
      return
    reactions_to_add = []
    resp_obj = self.call_api("reactions.get", channel=self.channelForChannel(message.channel()), timestamp=message.timestamp())
    # resp_obj = resp_obj.get('data', {})
    if resp_obj.get('message'):
      m=resp_obj["message"]
      if "reactions" in m:
        r=m["reactions"]
        for entry in r:
          if "name" in entry and entry["name"] != 'runner':
            reactions_to_add.append(entry["name"])
    log(D, f'reactions to add: {reactions_to_add}')
    resp_obj = self.call_api("chat.delete", ts=message.timestamp(), channel=self.channelForChannel(message.channel()))
    if not resp_obj["ok"]:
      e="unknown error, 'error' not in resp_obj"
      if "error" in resp_obj:
        e=resp_obj["error"]
      log(W, "Could not delete from main channel; perhaps already deleted? e=" + e)
      return
    resp_obj = self.call_api("chat.postMessage", as_user=True, channel='#history', text=message_text, attachments=attachments, unfurl_links=False, unfurl_media=False)
    if resp_obj.get('ts'):
      ts=resp_obj["ts"]
      for reaction in reactions_to_add:
        self.call_api("reactions.add", timestamp=ts, channel=self.channelForChannel("#robinhood"), name=reaction)

  def postMessage(self, message):
    self.postMessage(message.channel(), message.text())

  def postMessage(self, channel, text, call_number = None, save = False, bold = False, red = False):
    if red:
      text_to_post = '*`' + text + '`*'
    elif bold:
      text_to_post = '*' + text + '*'
    else:
      text_to_post = text
    response = self.call_api(
        'chat.postMessage',
        as_user=True,
        icon_emoji=':lkwd-chaveirim:',
        channel=self.channelForChannel(channel),
        text=text_to_post,
        username='Lkwd Calls',
        unfurl_links=False,
        unfurl_media=False
    )
        # parse='none' if needed
    if not response.get('ts'):
      log(W, "No 'ts' in response: " + str(response))
      return None
    timestamp = response['ts']
    m = Message(channel, timestamp, text, call_number=call_number)
    if save:
      messages.addMessage(m)
    return m

  def updateMessage(self, message, save = False, bold = False, red = False):
    text = message.text()
    text = re.sub('[<]tel[^|]+[|]([^>]+)[>]', r'\1', text)
    if red:
      text_to_post = '*`' + text + '`*'
    elif bold:
      text_to_post = '*' + text + '*'
    else:
      text_to_post = text
    response = self.call_api(
        'chat.update',
         ts=message.timestamp(),
         channel=self.channelForChannel(message.channel()),
         text=text_to_post,
         attachments=message.attachmentsArray())
    # parse='none' if needed
    if not response.get('ts'):
      log(W, "No 'ts' in response: " + str(response))
      return None
    timestamp = response['ts']
    message._timestamp = timestamp
    if save:
      messages.updateMessage(message)
    return message

  def isDispatchMessage(self, text):
    newMsg = re.match('1?[0-9]:[0-5][0-9] [AP]M: \[([0-9]{3})\] ', text)
    return newMsg is not None

  def callNumberForDispatchMessage(self, text):
    newMsg = re.match('1?[0-9]:[0-5][0-9] [AP]M: \[([0-9]{3})\] ', text)
    if newMsg is None:
      return None
    return newMsg.group(1)

  def logoNameForUnitNumber(self, unit_number):
    if unit_number is None or len(unit_number) < 2:
      log(W, "invalidly short unit number: '" + str(unit_number) + "'")
      return 'wavy_dash'
    unit_number = unit_number.lower()
    r=re.match('s.*([1-9])', unit_number)
    if r is not None:
      return 'unit_s' + r.group(1)
    for part in unit_number.split('/'):
      if re.match('1?[0-9][0-9]|[1-9][0-9]', part):
        return 'unit_' + part
    log(W, "Unknown unit '" + unit_number + "'")
    return 'wavy_dash'

  def addRunnerToMessage(self, message):
    self.call_api(
       "reactions.add",
        timestamp=message.timestamp(),
        channel=self.channelForChannel(message.channel()),
        name='runner')

  def addShofarToMessage(self, message):
    self.call_api(
       "reactions.add",
        timestamp=message.timestamp(),
        channel=self.channelForChannel(message.channel()),
        name='shofar')

  def removeRunnerFromMessage(self, message):
    self.call_api(
       "reactions.remove",
        timestamp=message.timestamp(),
        channel=self.channelForChannel(message.channel()),
        name='runner')

  def addNoPedestriansToMessage(self, message):
    self.call_api(
       "reactions.add",
        timestamp=message.timestamp(),
        channel=self.channelForChannel(message.channel()),
        name='no_pedestrians')

  def markUnitAsCoveringMessage(self, message, unit_number):
    logo_name = self.logoNameForUnitNumber(unit_number)
    self.call_api(
        "reactions.add",
        timestamp=message.timestamp(),
        channel=self.channelForChannel(message.channel()),
        name=logo_name)

  def scheduleMessageForClearing(self, message):
    threading.Timer(600, self.moveMessageFromCallsToCleared, kwargs={"message": message}).start()

  def dispatchMessage(self, text, user_name):
    postdata={'user_name': user_name, 'text': text}
    try:
      log(D, f"Posting {postdata} to https://lakewood-chaveirim.appspot.com/slack/dispatch ...")
      r = requests.post('https://lakewood-chaveirim.appspot.com/slack/dispatch', json=postdata)
      #print "done"
      log(D, f'status={r.status_code} content={r.content}')
    except Exception as e:
      log(W, "urllib may have failed, check lakewood-chaveirim logs. e=" + str(e))

  def markEmojiAdded(self, user_name, callnum, emoji_name):
    postdata={'user_name': user_name, 'call_number': callnum, 'emoji': emoji_name}
    try:
      log(W, f"Posting {postdata} to https://lakewood-chaveirim.appspot.com/slack/emojiadded ...")
      r = requests.post('https://lakewood-chaveirim.appspot.com/slack/emojiadded', json=postdata)
      #print "done"
      log(D, f'status={r.status_code} content={r.content}')
    except Exception as e:
      log(W, "urllib may have failed, check lakewood-chaveirim logs. e=" + str(e))

  def updateChannels(self):
    channels_obj = self.call_api("conversations.list", exclude_archived=True)
    if not channels_obj.get('channels'):
      log(W, 'Bah! No \'channels\'!')
      log(W, str(channels_obj))
      return
    for channel_obj in channels_obj['channels']:
      self._channel_name_to_id_dict['#' + channel_obj['name']] = channel_obj['id']

  def channelForChannel(self, channel):
    if channel in list(self._channel_name_to_id_dict.keys()):
      log(D, 'channelForChannel: channel id for name ' + channel + ' is ' + self._channel_name_to_id_dict[channel])
      return self._channel_name_to_id_dict[channel]
    if channel[0] == '#':
      channel2 = channel[1:]
      if channel2 in list(self._channel_name_to_id_dict.keys()):
        log(D, 'channelForChannel: channel2 id for name ' + channel2 + ' is ' + self._channel_name_to_id_dict[channel2])
        return self._channel_name_to_id_dict[channel2]
    log(D, 'channelForChannel: channel name ' + str(channel) + ' not in dict, returning as is')
    log(D, f'for the record self._channel_name_to_id_dict is: {self._channel_name_to_id_dict}')
    return channel

  def maybeSendFirstText(self, message, unit_number = None):
    if message.sentFirstText():
      log(D, 'Sent first text, not sending again.')
      return
    phoneNumber = re.search("\(?([0-9][0-9][0-9])\)? ?-?([0-9][0-9][0-9]) ?-?([0-9][0-9][0-9][0-9])", message.text())
    if phoneNumber is None:
      log(D, 'No phone number match in msg: ' + message)
      return

    if len(phoneNumber.groups()) != 3:
      log(W, 'Invalid match: number of groups=' + str(len(phoneNumber.groups())) + ' which is not 3! They are ' + str(phoneNumber.groups()) + ' for ' + str(phoneNumber.group()))
      return

    g1=phoneNumber.group(1)
    g2=phoneNumber.group(2)
    g3=phoneNumber.group(3)
    if len(g1) != 3 or len(g2) != 3 or len(g3) != 4:
      log(W, 'Phone number group lengths aren\'t 3-3-4: ' + str(len(g1)) + '-' + str(len(g2)) + '-' + str(len(g3)))
      return
    phoneNumber = "+1" + str(g1) + str(g2) + str(g3)
    fromNumber = "+17322301289"
    #fromNumber = "+17323702229"

    # Strip /d11  or /D3 style part of unit_number
    if unit_number is not None and '/' in unit_number:
      unit_number = unit_number[:unit_number.find('/')]

    msg_body_default = """Message from Lakewood Chaveirim: A dedicated volunteer is on his way.  Please keep your phone line clear & look out for him.
Thank you.
Bit.ly/SupportChaveirim1"""
    # msg_body_with_unit_number = """Message from @LkwdChaveirim: A dedicated volunteer is on his way. Please keep ur phone line clear & look out for him. Thank you. rayze.it/re4chaveirim/unit{}""".format(unit_number)
    msg_body_sept2018 = """Message from ..."""
    msg_body_may2019 = """Msg from Chaveirim:
A volunteer is on his way. Please keep your phone line clear & look out for him. Ty
*To Donate:*
Click Here: Bit.ly/SupportChaveirim1
No internet? Reply YES for a call back."""
    msg_body_jun2019 = """Msg from Chaveirim:
A volunteer is on his way. Please keep your phone line clear & look out for him. Ty
*To Donate:*
Click Here: Bit.ly/SupportChaveirim1
Want to donate by phone?
Reply YES and we will call you"""
    # msg_body = msg_body_default if unit_number is None else msg_body_with_unit_number
    #msg_body = msg_body_jun2019
    #twilio_message = self._twilio.messages.create(body=msg_body,
                                     #to=phoneNumber,
                                     #from_=fromNumber)
    #log(D, "Message SID=" + str(twilio_message.sid))
    #messages.markMessageAsSentFirstText(message)
    #try:
      #followup_message_campaign = "Hello from ur friends @LkwdChaveirim. We hope we met ur expectations today. Pls consider helping us w/ a tax deductible donation: rayze.it/re4chaveirim/unit{}".format(unit_number)
      #followup_message_sept2018 = "Hello from ur friends @LkwdChaveirim. We hope we met ur expectations today. Pls consider helping us with a tax deductible donation: bit.ly/SupportChaveirim1"
      #followup_message_may2019 = """Hello from ur friends @LkwdChaveirim. We hope we met ur expectations today. Pls consider helping us with a tax deductible donation: bit.ly/SupportChaveirim1
#No internet? Reply YES for a call back."""
      #followup_message_jun2019 = """Hello from ur friends @LkwdChaveirim. We hope we met ur expectations today. Pls consider helping us with a tax deductible donation: bit.ly/SupportChaveirim1
#Want to donate by phone?
#Reply YES and we will call you"""
      #followup_message = followup_message_jun2019
      #with open(QUEUED_MESSAGES_FILE, 'a') as f:
        #f.write(phoneNumber + "|" + followup_message + "\n")
    #except Exception as e:
      #print(("Got exception!", e.message))

  # https://stackoverflow.com/a/14785625
  @staticmethod
  def normalize(some_string):
    return unicodedata.normalize('NFKD', str(some_string, "ISO-8859-1")).encode("ascii", "ignore")