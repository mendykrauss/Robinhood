#!/usr/bin/env python

import dataset
#import mylog
import json

from mylog import log
from mylog import W
from mylog import D
from mylog import E

import os

db = dataset.connect(os.environ.get('DB_PATH', 'sqlite:///lkwd_calls.db'))
table = db['messages']

class Message():
  _channel = None
  _timestamp = None
  _text = None
  _attachments_array = None
  _call_number = None
  _sent_first_text = False

  def __init__(self, channel, timestamp, text="", attachments_array=[], call_number = 0, sent_first_text = False):
    self._channel = channel
    self._timestamp = timestamp
    self._text = text
    self._sent_first_text = sent_first_text
    if isinstance(attachments_array, str) or isinstance(attachments_array, str):
      try:
        self._attachments_array = json.loads(attachments_array)
      except Exception as e:
        log(E, "Error deserializing JSON '" + attachments_array + "': " + str(e))
    elif isinstance(attachments_array, list):
      self._attachments_array = attachments_array
    else:
      log(E, "Don't know what kind of thing attachments_array is!")
      self._attachments_array = []
    self._attachments_array = attachments_array
    self._call_number = call_number

  def channel(self):
    return self._channel

  def timestamp(self):
    return self._timestamp

  def text(self):
    return self._text

  def attachmentsArray(self):
    return self._attachments_array

  def callNumber(self):
    return self._call_number

  def sentFirstText(self):
    return self._sent_first_text

  def toDict(self):
    return dict(
      channel = self._channel,
      timestamp = self._timestamp,
      text = self._text,
      attachmentsArray = json.dumps(self._attachments_array),
      callNumber = self._call_number,
      sentFirstText = self._sent_first_text
    )

  def __str__(self):
    return "<message channel='{channel}' timestamp='{timestamp}' text='{text}' callNumber='{callNumber}' attachments='{attachments}' sentFirstText='{sentFirstText}'>".format(
      channel=self._channel, timestamp=self._timestamp, text=self._text, callNumber=str(self._call_number), attachments=str(self._attachments_array), sentFirstText=str(self._sent_first_text)
    )

def messageFromDict(dict):
  channel = dict["channel"]
  timestamp = dict["timestamp"]
  text = dict["text"]
  # if type(text) == str:
  #   text = text.encode('utf-8', 'replace')
  attachmentsArray = dict["attachmentsArray"]
  callNumber = dict["callNumber"]
  sentFirstText = dict["sentFirstText"] if "sentFirstText" in dict else False
  return Message(channel, timestamp, text, attachmentsArray, callNumber, sentFirstText)

def addMessage(message):
  if not message or not isinstance(message, Message):
    log(W, "Invalid message: " + str(message))
  table.insert(message.toDict())
  log(D, "Added: " + str(message))

def updateMessage(message):
  # TODO(yakov): implement!
  return None

def markMessageAsSentFirstText(message):
  result = table.find_one(timestamp=message.timestamp(), channel=message.channel())
  if result is None:
    log(E, 'Couldn\'t find message to mark as sent first text: ' + str(message))
    return False
  #table.update(result, sentFirstText=True)

  row=dict(id=result['id'], sentFirstText=True)
  table.update(row, ['id'])
  log(D, 'Updated: sent first text for message: ' + str(message))
  return True

def findMessage(timestamp = None, channel = None, call_number = None):
  if not (timestamp is not None and channel is not None) and call_number is None:
    log(W, "Need either channel and timestamp, or call number. Got timestamp=" + str(timestamp) + " channel=" + str(channel) + " call_number=" + str(call_number))
  if timestamp is not None and channel is not None:
    result=table.find_one(timestamp=timestamp, channel=channel)
    if result is None:
      log(W, "No result for channel='" + channel + "' timestamp='" + timestamp + "'")
      return None
    log(D, "Found message: " + str(result))
    message = messageFromDict(result)
    log(D, 'Returning: ' + str(message))
    return message
  elif call_number is not None:
    results = table.find(callNumber = call_number, _limit=1, order_by='-id')
    result = next(results, None)
    if result is None:
      log(W, "No result for call_number=" + str(call_number))
      return None
    log(D, "Found message: " + str(result))
    message = messageFromDict(result)
    log(D, 'Returning: ' + str(message))
    return message
  else:
    log(W, "Need another else :)")
    return None