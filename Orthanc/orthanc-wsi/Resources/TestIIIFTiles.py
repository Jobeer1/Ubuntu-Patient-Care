#!/usr/bin/env python3

import requests
import sys

if len(sys.argv) != 2:
    print('Usage: %s <URL to info.json>' % sys.argv[0])
    exit(-1)

r = requests.get(sys.argv[1])
r.raise_for_status()

info = r.json()

assert(len(info['tiles']) == 1)
assert(len(info['tiles'][0]['scaleFactors']) == len(info['sizes']))

width = None
height = None
for size in info['sizes']:
    if (width == None or
        size['width'] > width):
        width = size['width']
        height = size['height']

tw = info['tiles'][0]['width']
th = info['tiles'][0]['height']

assert(isinstance(width, int))
assert(isinstance(height, int))
assert(isinstance(tw, int))
assert(isinstance(th, int))

def CeilingDivision(a, b):
    if a % b == 0:
        return a // b
    else:
        return a // b + 1

for s in info['tiles'][0]['scaleFactors']:
    assert(isinstance(s, int))

    countTilesX = CeilingDivision(width, tw * s)
    countTilesY = CeilingDivision(height, th * s)
    print(tw * s, th * s, countTilesX, countTilesY)

    for m in range(countTilesY):
        for n in range(countTilesX):

            # Reference:
            # https://iiif.io/api/image/3.0/implementation/#3-tile-region-parameter-calculation

            # Calculate region parameters /xr,yr,wr,hr/
            xr = n * tw * s
            yr = m * th * s
            wr = tw * s
            if (xr + wr > width):
                wr = width - xr
            hr = th * s
            if (yr + hr > height):
                hr = height - yr

            # Calculate size parameters /ws,hs/
            ws = tw
            if (xr + tw*s > width):
                ws = (width - xr + s - 1) / s  # +s-1 in numerator to round up
            hs = th
            if (yr + th*s > height):
                hs = (height - yr + s - 1) / s

            url = '%s/%d,%d,%d,%d/%d,%d/0/default.jpg' % (info['id'], xr, yr, wr, hr, ws, hs)
            r = requests.get(url)

            if r.status_code == 200:
                print('SUCCESS: %s' % url)
            else:
                print('ERROR:   %s' % url)
