from base64 import b64decode
from datetime import datetime, timedelta
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
    doit_url = 'https://data.cityofchicago.org/resource/4ijn-s7e5.json?$where=starts_with(aka_name,{})'.format(aka_name)
    
    r = requests.get(doit_url)
    if r.status_code == 200:
        results = json.loads(r.text)
        sorted_results = sorted(results, key=lambda x: datetime.strptime(x['inspection_date'], '%Y-%m-%dT%H:%M:%S'), reverse=True)
        last_inspection = sorted_results[0]
        last_inspection_date = last_inspection['inspection_date']
        last_inspection_date_formatted = datetime.strptime(last_inspection_date, '%Y-%m-%dT%H:%M:%S')
        
        # if new inspection data appeared in the last 24 hours
        if datetime.now() - last_inspection_date_formatted < timedelta(days=200):

            # grab inspection data
            inspection_type = last_inspection['inspection_type']
            results = last_inspection['results']
            url_for_last_inspection = '{}&inspection_date={}'.format(doit_url, last_inspection_date)
            
            # create slack payload
            payload = {
                "channel": "#general",
                "username": "SunWahBot",
                "icon_emoji": ":bird:",
                "text": '*New inspection. May be tasty -and- safe!* \ntype: {}\ndate: {}\nresults: {}\ncomplete record: <{}>'.format(
                    inspection_type, last_inspection_date, results, url_for_last_inspection)
            }

            # post to slack
            headers = {'Content-type': 'application/json'}
            response = requests.post(slack_url, json=payload, headers=headers)       

    else:
        payload = {
            "channel": channel,
            "username": "SunWahBot",
            "icon_emoji": ":bird:",
            "text": "Inspection request failed with error {}".format(r.status_code)
        }
        headers = {'Content-type': 'application/json'}
        response = requests.post(slack_url, json=payload, headers=headers)


def lambda_handler(event, context):
    download_process_inspections(slack_url, aka_name)
