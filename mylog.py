#!/usr/bin/env python

#from googleapiclient.discovery import build
#from oauth2client.client import GoogleCredentials
import datetime
import threading

D = "DEBUG"
I = "INFO"
V = "VERBOSE"
W = "WARNING"
E = "ERROR"


#def create_logging_client():
#  """Returns a Cloud Logging service client for calling the API."""
#  credentials = GoogleCredentials.get_application_default()
#  return build('logging', 'v1beta3', credentials=credentials)


#def log(level, msg):
#  t = threading.Thread(target=reallog, kwargs={'level': level, 'msg': msg})
#  t.start()
#
def log(level, msg):

  print(str(datetime.datetime.now()) + ": " + msg)

#  try:
#
#    client = create_logging_client()
#
#    entry_metadata = {
#      "timestamp": datetime.datetime.now().isoformat('T') + 'Z',
#      "region": "us-east1",
#      "zone": "us-east1-b",
#      "serviceName": "compute.googleapis.com",
#      "severity": level,
#      "labels": {}
#    }
#
#    # Create a POST body for the write log entries request.
#    body = {
#      "commonLabels": {
#        "compute.googleapis.com/resource_id": "lkwd_calls",
#        "compute.googleapis.com/resource_type": "instance",
#      },
#      "entries": [
#        {
#          "metadata": entry_metadata,
#          "log": "mylog",
#          "textPayload": msg
#        }
#        # ,
#        #   {
#        #       "metadata": entry_metadata,
#        #       "log": "mylog",
#        #       "textPayload": "Test message two."
#        #   }
#      ]
#    }
#
#    resp = client.projects().logs().entries().write(
#        projectsId="lakewood-chaveirim", logsId="mylog", body=body).execute()
#    if resp != {}:
#      print("Google logging API returned " + str(resp))
#  except Exception as e:
#    print("Google Logging API threw Exception: " + str(e))
#  # DEBUG ONLY
#  #if level == D:
#  #  logging.debug(msg)
#  #elif level == I:
#  #  logging.info(msg)
#  #elif level == W:
#  #  logging.warn(msg)
#  #elif level == E:
#  #  logging.error(msg)
#  #elif level == V:
#  #  logging.log(level, msg)