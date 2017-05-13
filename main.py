# -*- coding: utf-8 -*-

import gzip
import json
import os
import platform
import random
import StringIO
import sys
import urllib
import socket


parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'vendor')

sys.path.append(vendor_dir)

import markovify
import moment
import twitter

def info(message):
    print "[INFO]" + str(message)

def handler(event, context):

    info('Event received')

    consumer_key = os.environ['CONSUMER_KEY']
    consumer_secret = os.environ['CONSUMER_SECRET']
    access_token_key = os.environ['ACCESS_TOKEN_KEY']
    access_token_secret = os.environ['ACCESS_TOKEN_SECRET']

    if not consumer_key or not consumer_secret or not access_token_key or not access_token_secret:
        print '[ERROR] The following environment variables are required. CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET'
        raise

    # Download the file
    file_path = get_archive()
    commits = get_commits(file_path)

    # Build the model.
    text_model = markovify.Text(commits)
    messages = text_model.make_sentence().replace('\\n', '\n').split('\n')
    message = random.choice(messages)

    t = twitter.Api(consumer_key=consumer_key,
                    consumer_secret=consumer_secret,
                    access_token_key=access_token_key,
                    access_token_secret=access_token_secret)

    info("Message: " + message)
    
    try:
        t.PostUpdate(message)
    except TwitterError as err:
        print '[WARN] Error posting to Twitter. Trying with a new message.'
        message = random.choice(messages)
        info("Message: " + message)
        t.postUpdate(message = random.choice(messages))

    return { 
        'message': 'ok' 
    }

def get_archive():
    URL_FORMAT = 'http://data.githubarchive.org/{}-4.json.gz'

    yesterday = moment.now().subtract(days=1).format('YYYY-MM-DD')
    url = URL_FORMAT.format(yesterday)

    info('Downloading archive')

    # Set timeout to 30 seconds
    socket.setdefaulttimeout(30)
    
    # Pull down the gzipped file
    response = urllib.urlopen(url)

    info('Download finished')
    info('Unzipping data')
    
    # Get an empty file to plug the data into
    zipped = StringIO.StringIO()
    zipped.write(response.read())
    zipped.seek(0)

    output = gzip.GzipFile(fileobj=zipped, mode='rb')
    return output.read()
    

def get_commits(raw_output):
        info('Extracting commit messages')
        objects = []
        for line in raw_output.split('\n'):
            if line:
                objects.append(json.loads(line, 'UTF-8'))

        commit_events = filter(filter_only_has_commits, objects)
        return '\n'.join(map(map_to_commits, commit_events))

def map_to_commits(event):
    messages = []

    for commit in event['payload']['commits']:
        messages.append(commit['message'])

    return '\n'.join(messages)
               .replace('\n\n', '\n')
               .replace('@', '')

def filter_only_has_commits(event):
    return 'commits' in event['payload'] and event['payload']['commits']

if __name__ == '__main__':
    if platform.system() == 'Darwin':
        handler(1, 2)   

