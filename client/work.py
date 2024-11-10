"""
Work dashboard display module for Inky Frame
Displays tasks and calendar events from a remote JSON source
"""

import time
from micropython import const
import inky_frame
import inky_helper as ih
import urequests as requests
import ujson
from secrets import WEBDAV_AUTHORIZATION

# Configuration constants
UPDATE_INTERVAL = const(60)  # in minutes
DATA_URL = const("https://myfiles.fastmail.com/data/work.json")
MAX_ISSUES = const(5)  # maximum number of issues to display
MAX_RETRIES = const(3)
RETRY_DELAY = const(5)  # seconds between retries

class DashboardError(Exception):
    """Base exception for dashboard-related errors"""
    pass

# Display objects passed by launcher
graphics = None
WIDTH = None 
HEIGHT = None

# Global state
status = []
data = {}

def update():
    """
    Fetch latest work data from remote WebDAV source and update local cache.
    Updates global data and status variables.
    
    Raises:
        DashboardError: If there are issues fetching or processing the data
    """
    global data
    global status
    
    status = []  # Clear previous status messages
    
    # Get work data from WebDAV with retries
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Fetching issues from {DATA_URL} (attempt {attempt + 1}/{MAX_RETRIES})")
            response = requests.get(DATA_URL, headers={
                'Authorization': f"Basic {WEBDAV_AUTHORIZATION}",
            })
            
            if response.status_code != 200:
                raise DashboardError(f"HTTP error {response.status_code}")
                
            # Read the complete response content
            content = response.text
            response.close()  # Explicitly close the response
            
            # Validate JSON before writing
            try:
                ujson.loads(content)  # Test parse
            except ValueError as e:
                raise DashboardError(f"Invalid JSON in response: {e}")
            
            # Write to file using context manager
            try:
                with open("/data/work.json", "w") as f:
                    f.write(content)
                    f.flush()
                print("Local issues file updated")
                break  # Success, exit retry loop
                
            except OSError as e:
                raise DashboardError(f"Failed to write cache file: {e}")
                
        except (OSError, DashboardError) as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                error_msg = f"Failed to fetch data after {MAX_RETRIES} attempts: {str(e)}"
                print(error_msg)
                status.append(error_msg)

    # Try to load cached data
    try:
        if ih.file_exists("/data/work.json"):
            with open("/data/work.json", "r") as f:
                file_content = f.read()
            try:
                data = ujson.loads(file_content)
            except ValueError as e:
                error_msg = f"Failed to parse cached JSON: {e}"
                print(error_msg)
                status.append(error_msg)
                data = {"data": {"issues": {}, "events": []}}  # Empty default data
        else:
            print("No cached data found")
            data = {"data": {"issues": {}, "events": []}}
            
    except OSError as e:
        error_msg = f"Failed to read cache file: {e}"
        print(error_msg)
        status.append(error_msg)
        data = {"data": {"issues": {}, "events": []}}

    # Add timestamp to status
    year, month, day, hour, mins, secs, weekday, yearday = time.localtime()
    status.append(f"Last refreshed: {year}-{month:02d}-{day:02d} {hour:02d}:{mins:02d}")


def draw_issue(issue, x, y):
    """
    Draw a single issue/task on the display
    
    Args:
        issue (dict): Issue data containing title, status, and repository
        x (int): X coordinate to start drawing
        y (int): Y coordinate to start drawing
    """
    if issue['status'] == 'In Progress':
        graphics.set_pen(inky_frame.BLUE)
    else:
        graphics.set_pen(graphics.create_pen(170, 170, 170))
    graphics.rectangle(x, y, 5, 50)

    graphics.set_pen(inky_frame.BLACK)
    graphics.text(text=issue['title'], x1=(x + 20), y1=y, wordwrap=350, scale=2)
    graphics.text(text=issue['repository'], x1=(x + 20), y1=(y + 40), wordwrap=350, scale=1)


def draw_event(event, x, y, width):
    """
    Draw a single calendar event on the display
    
    Args:
        event (dict): Event data containing start time and title
        x (int): X coordinate to start drawing
        y (int): Y coordinate to start drawing
        width (int): Maximum width available for drawing
    """
    graphics.set_pen(inky_frame.BLACK)
    graphics.text(text=event['start'], x1=(x), y1=(y), wordwrap=(50), scale=2)
    graphics.text(text=event['title'], x1=(x + 60), y1=y, wordwrap=(width - 50), scale=2)


def draw_header():
    """Draw the header section with title"""
    graphics.set_pen(inky_frame.ORANGE)
    graphics.rectangle(0, 0, WIDTH, 50)
    graphics.set_pen(inky_frame.BLACK)
    title = "Work"
    title_len = graphics.measure_text(title, 4) // 2
    graphics.text(title, (WIDTH // 2 - title_len), 10, WIDTH, 4)

def draw_tasks_column(gutter, tasks_col_width):
    """Draw the tasks column with issues"""
    graphics.text(text='Tasks', x1=gutter, y1=70, wordwrap=(tasks_col_width - 10), scale=3)

    y_offset = 120
    index = 0

    # Combine In Progress and Todo issues
    all_issues = []
    all_issues.extend(data['data']['issues'].get('In Progress', []))
    all_issues.extend(data['data']['issues'].get('Todo', []))
    
    # Display only up to MAX_ISSUES
    for i, issue in enumerate(all_issues[:MAX_ISSUES]):
        draw_issue(issue, 15, y_offset + (i * 60))

def draw_calendar_column(gutter, tasks_col_width):
    """Draw the calendar column with events"""
    x_offset = gutter + tasks_col_width + 20  # increased by 10
    events_col_width = WIDTH - x_offset - gutter - 10  # decreased by 10
    y_offset = 120
    
    graphics.text(text="Today", x1=x_offset, y1=70, wordwrap=(events_col_width - 10), scale=3)

    if not data['data']['events']:
        graphics.set_pen(inky_frame.BLACK)
        graphics.text(text="No events today", x1=x_offset, y1=y_offset, wordwrap=(WIDTH - 75), scale=2)
    else:
        for index, event in enumerate(data['data']['events']):
            draw_event(event, x_offset, y_offset + (index * 60), events_col_width)

def draw_status_bar():
    """Draw the status bar at the bottom"""
    graphics.text(text=' '.join(status), x1=10, y1=HEIGHT - 20, wordwrap=(WIDTH - 75), scale=1)

def draw():
    """
    Main drawing function that renders the entire dashboard layout.
    Displays tasks and calendar events in two columns.
    Uses global graphics, WIDTH, HEIGHT, data and status variables.
    """
    graphics.set_pen(inky_frame.WHITE)
    graphics.clear()

    gutter = 15
    tasks_col_width = (WIDTH // 2) + 10

    draw_header()
    draw_tasks_column(gutter, tasks_col_width)
    draw_calendar_column(gutter, tasks_col_width)
    draw_status_bar()

    graphics.update()

