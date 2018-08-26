#!/usr/bin/env python3
import requests
import sys
import bs4
import time
import os
import math
import speedtest
from datetime import datetime

if len(sys.argv) > 1:
    cookie = sys.argv[1]
else:
    print("{} <cookie>".format(sys.argv[0]))
    sys.exit()
cookies = {'ips4_IPSSessionFront': cookie}
headers = requests.utils.default_headers()
headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.109 Safari/537.36'})
save_location = ""

r = requests.get('https://linustechtips.com/main/forum/91-the-floatplane-club/',
                 cookies=cookies, headers=headers)

if r.status_code == 404:
    print("Cookie is invalid")
    sys.exit()
elif not r.ok:
    raise(Exception(r.status_code, r.headers))

print("Getting download speed...")

s = speedtest.Speedtest()
s.get_best_server()
speed = math.floor(s.download() / 125000) / 100

print(f"Download speed: {speed} MBps")

front_page = bs4.BeautifulSoup(r.text, "lxml")

floatplane_posts = []
print("Getting all posts in floatplane club...")
for post in front_page.find_all('a'):
    if "href" in post.attrs:
        url = str(post.attrs['href'])
        if url.startswith('https://linustechtips.com/main/topic/'):
            # if "-ltt-" in url or "-tq-" in url or "-csf-" in url:
            if not "?" in url:
                floatplane_posts.append(url)
print("Done!")

print("Getting all videos...")
videos = []
for post in floatplane_posts:
    new_post = requests.get(post, cookies=cookies, headers=headers)

    if not new_post.ok:
        raise(Exception(new_post.status_code, post))

    try:
        video_id = bs4.BeautifulSoup(new_post.text, "lxml").find_all(
            class_="floatplane-script")[0].attrs['data-video-guid']
        title = bs4.BeautifulSoup(
            new_post.text, "lxml").find_all('title')[0].text
        real_title = title
        post_time = bs4.BeautifulSoup(new_post.text, "lxml").find_all('time')[
            0].attrs['datetime']
        post_time = datetime.strptime(post_time.replace(
            'T', '%').replace('Z', '%'), "%Y-%m-%d%%%X%%").timestamp()
    except IndexError:
        continue
    except KeyError:
        print(post)
    fake_title = ""
    for word in title.split():
        if word == "-":
            break
        fake_title += word + " "
    title = fake_title[:len(fake_title) - 1].replace(' ', '-').lower()
    invalid_chars = ".,#<>$%!&*'{}?:\\ @\"/"
    for char in title:
        if char in invalid_chars:
            title = title.replace(char, '')
    if os.path.isfile(f"{save_location}{title}.mp4"):
        continue
    videos.append({"id": video_id, "title": real_title, "time": post_time,
                   "size": "", "dl_time": "", "file": fake_title})
    time.sleep(1)
print("Done!")

print("Calculating time to complete...")
full_time = 0
full_size = 0
for video in videos:
    post_calc = requests.get('https://linustechtips.com/main/applications/floatplane/interface/video_url.php?video_guid={}&video_quality=1080'.format(
        video['id']), cookies=cookies, headers=headers)
    post_calc = requests.get(post_calc.text.replace(
        '/playlist.m3u8', '', 1), cookies=cookies, headers=headers, stream=True)
    video['size'] = math.floor(
        int(post_calc.headers['content-length'])/1000000)
    video['dl_time'] = math.floor(video['size'] * (1/speed))
    full_size += video['size']
    full_time += video['dl_time']

print(
    f"Downloading {len(videos)} new videos ({full_size} MB - about {full_time} seconds)")
for video in videos:
    new_video_location = requests.get(
        'https://linustechtips.com/main/applications/floatplane/interface/video_url.php?video_guid={}&video_quality=1080'.format(video['id']), cookies=cookies, headers=headers)
    if not new_video_location.ok:
        raise(Exception(new_video_location.status_code))
    try:
        new_video = requests.get(new_video_location.text.replace(
            '/playlist.m3u8', '', 1), cookies=cookies, headers=headers, stream=True)
        print(
            f"Downloading video {video['file']} ({video['size']} MB - about {video['dl_time']} seconds)")
        print(f"Title: {video['title']}")
        print(
            f"Thumbnail: https://cms.linustechtips.com/get/thumbnails/by_guid/{video['id']}")
    except requests.exceptions.ConnectionError:
        continue
    if new_video.status_code == 404:
        continue
    elif not new_video.ok:
        raise(Exception(new_video.status_code))
    with open(f'{save_location}{video["file"]}.mp4', 'wb') as f:
        for chunk in new_video.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    os.utime(f'{save_location}{video["file"]}.mp4',
             times=(video['time'], video['time']))
    print(f"Video downloaded {video['file']}")
    time.sleep(1)

print("Complete!")
