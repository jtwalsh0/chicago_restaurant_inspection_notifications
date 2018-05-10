from base64 import b64decode
from datetime import datetime
import json
import os
import sys

import boto3
from botocore.vendored import requests


# get slack credentials
slack_url_encrypted = os.environ['SLACK_URL']
slack_url = boto3.client('kms').decrypt(CiphertextBlob=b64decode(slack_url_encrypted))['Plaintext'].decode('utf-8')

# get slack channel
slack_channel_encrypted = os.environ['CHANNEL']
slack_channel  = boto3.client('kms').decrypt(CiphertextBlob=b64decode(slack_channel_encrypted))['Plaintext'].decode('utf-8')

# restaurant to search for
aka_name_encrypted = os.environ['AKA_NAME']
aka_name = boto3.client('kms').decrypt(CiphertextBlob=b64decode(aka_name_encrypted))['Plaintext'].decode('utf-8')


# function to download and process inspections data
def download_process_inspections(slack_url, aka_name):
    print(slack_url)
    print(aka_name)
    doit_url = ('https://data.cityofchicago.org/resource/4ijn-s7e5.json?$where=starts_with(aka_name,' +
        aka_name +
        ')')
    print(doit_url)
    
    r = requests.get(doit_url)
    if r.status_code == 200:
        new_results = json.loads(r.text)
        sorted_new_results = sorted(new_results, key=lambda x: datetime.strptime(x['inspection_date'], '%Y-%m-%dT%H:%M:%S'), reverse=True)
        recent_inspection_date = datetime.strptime(sorted_new_results[0]['inspection_date'], '%Y-%m-%dT%H:%M:%S')
        
        # if new inspection data appeared in the last 24 hours
        if datetime.now() - last_inspection_date < timedelta(days=1):

            # grab inspection data
            inspection_date = sorted_new_results[0]['inspection_date']
            inspection_type = sorted_new_results[0]['inspection_type']
            results = sorted_new_results[0]['results']
            url_for_latest_inspection = doit_url + '&inspection_date={}'.format(inspection_date)
            
            # create slack payload
            payload = {
                "channel": "#general",
                "username": "InspectionBot",
                "icon_emoji": ":robot_face:",
                "text": '*New inspection. May be tasty -and- safe!* \n' +
                        'type: ' + inspection_type + '\n' +
                        'date: ' + inspection_date + '\n' +
                        'results: ' + results + '\n' +
                        'complete record: <' + url_for_latest_inspection + '>'
            }

            # post to slack
            headers = {'Content-type': 'application/json'}
            response = requests.post(slack_url, json=payload, headers=headers)
            

    else:
        payload = {
            "channel": channel,
            "username": "InspectionBot",
            "icon_emoji": ":robot_face:",
            "text": "Inspection request failed with error {}".format(r.status_code)
        }
        headers = {'Content-type': 'application/json'}
        response = requests.post(slack_url, json=payload, headers=headers)


def lambda_handler(event, context):
    download_process_inspections(slack_url, aka_name)
