import gc
import inky_frame
import inky_helper as ih
import json
import urequests as requests
from urllib import urequest
from ujson import load
from picographics import PicoGraphics, PEN_RGB565, PEN_RGB332, DISPLAY_INKY_FRAME_7 as DISPLAY

graphics = None
WIDTH = None
HEIGHT = None

UPDATE_INTERVAL = 60  # in minutes

API_URL = "http://192.168.1.206:8087/api/work/issues"
TIME_URL = "http://192.168.1.206:8087/api/meta/time"

issues = None
status = []

def update():
    global issues
    global status
    
    try:
        print("Fetching time from {}".format(TIME_URL))
        response = requests.get(TIME_URL)
        time = response.text
        status.append("Last screen update: {}.".format(time))
    except OSError as e:
        print(e)
        status.append("Could not fetch time from server.")
        
    try:
        print("Fetching issues from {}".format(API_URL))
        response = requests.get(API_URL)
        
        with open("/data/issues.json", "w") as f:
            f.write(response.text)
            f.flush()

        print("Local issues file updated")

    except OSError as e:
        print("Could not get latest issues list")
        status.append("Could not get latest issues list: {}".format(e))

    if ih.file_exists("/data/issues.json"):
        issues = json.loads(open("/data/issues.json", "r").read())


def draw_issue(issue, x, y):
    global graphics
    global WIDTH
    global HEIGHT

    if issue['status'] == 'In Progress':
        graphics.set_pen(inky_frame.BLUE)
    else:
        graphics.set_pen(graphics.create_pen(170, 170, 170))
    graphics.rectangle(x, y, 5, 50)

    graphics.set_pen(inky_frame.BLACK)
    graphics.text(text=issue['title'], x1=(x + 20), y1=y, wordwrap=350, scale=2)
    graphics.text(text=issue['sprint'], x1=(x + 20), y1=(y + 40), wordwrap=350, scale=1)


def draw():
    global issues
    global status

    graphics.set_pen(inky_frame.WHITE)
    graphics.clear()

    graphics.set_pen(graphics.create_pen(255, 215, 0))
    graphics.rectangle(0, 0, WIDTH, 50)
    graphics.set_pen(inky_frame.BLACK)
    title = "Work"
    title_len = graphics.measure_text(title, 4) // 2
    graphics.text(title, (WIDTH // 2 - title_len), 10, WIDTH, 4)
    
    col_width = WIDTH // 2
    graphics.text(text='Tasks', x1=10, y1=70, wordwrap=(col_width - 10), scale=3)

    #graphics.text(text='Calendar', x1=col_width, y1=70, wordwrap=(col_width - 10), scale=3)
    #events = [
    #    { "time": "03:00", "title": "Docs review" },
    #    { "time": "09:30", "title": "Team call - discussing things that might cause word wrapping" },
    #]
    
    y_offset = 120
    index = 0

    for issue in issues['In Progress']:
        draw_issue(issue, 10, y_offset + (index * 60))
        index = index + 1
            
    y_offset = y_offset + (index * 60) + 20
    index = 0

    for issue in issues['Todo']:
        draw_issue(issue, 10, y_offset + (index * 60))
        index = index + 1

    # Draw status message
    graphics.text(text=' '.join(status), x1=10, y1=HEIGHT - 20, wordwrap=(WIDTH - 75), scale=1)

    graphics.update()

