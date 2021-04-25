#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Since AWS lambda has a hard size limit for its applications, we compressed on a zip file:
serverless.yml -> custom -> pythonRequirements -> zip: true
Before anything, this should run in order to unzip and run this application.
In case you deploy this on a dedicated machine, this can be removed
'''
try:
  import unzip_requirements
except ImportError:
  pass

import json
from datetime import datetime
from src.configs.configs import REDEMET_BUCKET
from src.configs.configs import USERS_BUCKET
from src.services.s3 import S3
from src.functions.radar_data import load_data
from src.functions.precipitation import update_alerts, make_clusters



def hello(event, context):
    body = {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "input": event
    }
    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response

def get_radar(event=None, context=None):
    print(event)
    radar_image, bbox = zip(*list(load_data()))
    args = {
        'radar_image': list(radar_image),
        'bbox': list(bbox)
    }
    # radar_image, bbox = list(radar_image), list(bbox)
    location_bucket = S3(USERS_BUCKET)
    locations = location_bucket.load('users.json')
    updated_locations = dict(update_alerts(locations, **args))

    # Fill locations not covered by radar info
    utcnow = datetime.utcnow()
    alerts_bucket = S3()
               

    # Save data to bucket
    # if len(updated_locations) > 0:    
    if event.get('debug'):
        return updated_locations
    now = utcnow.strftime('%Y%m%dT%H%M')
    filepath = f"radar/{now}.json"
    alerts_bucket.upload(json.dumps({
        'periods':utcnow.strftime('%Y-%m-%dT%H:%M:%S'),
            'locations': updated_locations
            }, indent=4), filepath)
