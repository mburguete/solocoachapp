import os
import pytz
from datetime import datetime, timedelta, time, date
from dateutil.parser import parse as dtparse
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import requests
from ics import Calendar, Event

load_dotenv()
BASE_DIR = os.path.dirname(__file__)
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET','dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///solocoach.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

TZ_NAME = os.getenv('TZ','Africa/Ceuta')
TZ = pytz.timezone(TZ_NAME)
CITY_PALMA = os.getenv('HOME_CITY_PALMA','Palma de Mallorca')
CITY_MADRID = os.getenv('HOME_CITY_MADRID','Madrid')

TELEGRAM_BOT_TOKEN = os.getenv(8418506074:AAEMAqSivC6VIVOj12kARJ0Cd1E27gtNABg)
TELEGRAM_CHAT_ID = os.getenv(@Solocoach_mBot)

# --- Models ---
class Flight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    depart_city = db.Column(db.String(64))
    arrive_city = db.Column(db.String(64))
    depart_time = db.Column(db.String(64))  # ISO string
    arrive_time = db.Column(db.String(64))  # ISO string
    note = db.Column(db.String(140))

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    context = db.Column(db.String(32), default='any')  # 'airport', 'home', 'any'
    minutes = db.Column(db.Integer, default=45)
    project = db.Column(db.String(64), default='Side Project')

class Streak(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10))  # YYYY-MM-DD
    training = db.Column(db.Boolean, default=False)
    protein = db.Column(db.Boolean, default=False)
    deepwork = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

# --- Helpers ---
def today_str(dt=None):
    dt = dt or datetime.now(TZ)
    return dt.strftime('%Y-%m-%d')

def localize(dt):
    if dt.tzinfo is None:
        return TZ.localize(dt)
    return dt.astimezone(TZ)

def get_weather(city):
    # Open-Meteo geocoding + forecast (no key required)
    try:
        geo = requests.get('https://geocoding-api.open-meteo.com/v1/search', params={'name': city, 'count':1}).json()
        lat = geo['results'][0]['latitude']
        lon = geo['results'][0]['longitude']
        wx = requests.get('https://api.open-meteo.com/v1/forecast', params={
            'latitude': lat, 'longitude': lon, 'hourly':'windspeed_10m,temperature_2m', 'timezone': TZ_NAME
        }).json()
        now = datetime.now(TZ).replace(minute=0, second=0, microsecond=0)
        times = wx['hourly']['time']
        if now.strftime('%Y-%m-%dT%H:00') in times:
            idx = times.index(now.strftime('%Y-%m-%dT%H:00'))
        else:
            idx = 0
        return {
            'temp': wx['hourly']['temperature_2m'][idx],
            'wind': wx['hourly']['windspeed_10m'][idx]
        }
    except Exception as e:
        return {'temp': None, 'wind': None}

def city_for_datetime(dt):
    # Assume Palma Thu night/Fri morning through Mon night/Tue early
    dow = dt.weekday()  # Mon=0 ... Sun=6
    if dow in (4,5,6,0):  # Fri, Sat, Sun, Mon
        return CITY_PALMA
    return CITY_MADRID

def active_flight_slots(day):
    """Return list of (start,end,flight) in local tz for that day"""
    slots = []
    start = TZ.localize(datetime.combine(day, time.min))
    end = TZ.localize(datetime.combine(day, time.max))
    flights = Flight.query.all()
    for f in flights:
        dt = localize(dtparse(f.depart_time))
        at = localize(dtparse(f.arrive_time))
        if start.date() <= dt.date() <= end.date() or start.date() <= at.date() <= end.date():
            slots.append((dt, at, f))
    return sorted(slots, key=lambda x:x[0])

def pack_airport_tasks(duration_min):
    tasks = Task.query.filter((Task.context=='airport') | (Task.context=='any')).order_by(Task.minutes.asc()).all()
    res, total = [], 0
    for t in tasks:
        if total + t.minutes <= duration_min:
            res.append(t)
            total += t.minutes
    return res

def generate_plan(for_date=None):
    now = datetime.now(TZ)
    day = (for_date or now.date())
    city = city_for_datetime(TZ.localize(datetime.combine(day, time(8,0))))
    weather = get_weather(city)
    wind = weather.get('wind')
    if city == CITY_PALMA:
        if wind and wind >= 18:
            training = "Kitesurf/Windsurf (windy) + mobility 20min"
        else:
            training = "Outdoor endurance: Road bike or Run (90min) + 10min strides"
    else:
        training = "Gym Strength (45–60min) + 20min treadmill brick"
    flights = active_flight_slots(day)
    schedule = []
    def add_block(start, end, title, desc=''):
        schedule.append({'start': start, 'end': end, 'title': title, 'desc': desc})
    start = TZ.localize(datetime.combine(day, time(6,30)))
    end = TZ.localize(datetime.combine(day, time(9,0)))
    add_block(start, end, f"Training — {training}", "Take creatine + protein at 07:00 and post-workout.")
    cursor = TZ.localize(datetime.combine(day, time(9,30)))
    end_of_day = TZ.localize(datetime.combine(day, time(21,30)))
    for (fd, fa, f) in flights:
        if cursor < fd:
            add_block(cursor, fd, "Google Deep Work", "Focus sprint")
        wait_start = fd - timedelta(minutes=60)
        if wait_start > cursor:
            add_block(wait_start, fd, "Airport Deep Work", "No entertainment — execute preloaded tasks.")
        add_block(fd, fa, f"FLIGHT {f.depart_city} → {f.arrive_city}", f.note or "")
        cursor = fa + timedelta(minutes=30)
    if cursor < end_of_day:
        add_block(cursor, end_of_day, "Side Projects / Dental Clinic", "KPI review, marketing, digitization")
    add_block(TZ.localize(datetime.combine(day, time(21,0))), TZ.localize(datetime.combine(day, time(21,20))), "Reflection & habit log", "Mark Training/Protein/Deepwork")
    return {'city': city, 'weather': weather, 'schedule': schedule}

def send_telegram(msg):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        import requests
        requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': msg})
        return True
    except Exception:
        return False

def schedule_to_ics(plan):
    cal = Calendar()
    for blk in plan['schedule']:
        e = Event()
        e.name = blk['title']
        e.begin = blk['start']
        e.end = blk['end']
        e.description = blk['desc']
        cal.events.add(e)
    return cal

@app.route('/')
def index():
    today = datetime.now(TZ).date()
    plan = generate_plan(today)
    streak = Streak.query.filter_by(date=today_str()).first()
    flights = Flight.query.order_by(Flight.depart_time.asc()).all()
    tasks = Task.query.order_by(Task.context.asc()).all()
    return render_template('index.html', plan=plan, streak=streak, flights=flights, tasks=tasks, tz=TZ_NAME)

@app.route('/streak', methods=['POST'])
def streak_update():
    date_str = today_str()
    s = Streak.query.filter_by(date=date_str).first()
    if not s:
        s = Streak(date=date_str)
        db.session.add(s)
    for k in ['training','protein','deepwork']:
        if k in request.form:
            setattr(s, k, True)
    db.session.commit()
    flash('Streak updated!', 'success')
    return redirect(url_for('index'))

@app.route('/flight/new', methods=['POST'])
def flight_new():
    f = Flight(
        depart_city=request.form['depart_city'],
        arrive_city=request.form['arrive_city'],
        depart_time=request.form['depart_time'],
        arrive_time=request.form['arrive_time'],
        note=request.form.get('note','')
    )
    db.session.add(f)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/task/new', methods=['POST'])
def task_new():
    t = Task(
        title=request.form['title'],
        context=request.form['context'],
        minutes=int(request.form.get('minutes',45)),
        project=request.form.get('project','Side Project')
    )
    db.session.add(t)
    db.session.commit()
    return redirect(url_for('index'))

@app.route("/plan/ics")
def plan_ics():
    from ics import Calendar, Event
    from datetime import datetime
    import pytz

    tz = pytz.timezone(os.getenv("TZ", "Africa/Ceuta"))
    now = datetime.now(tz)

    c = Calendar()
    e = Event()
    e.name = "SoloCoach Plan"
    e.begin = now
    e.end = now.replace(hour=23, minute=59)
    c.events.add(e)

    path = os.path.join(os.path.dirname(__file__), 'plan.ics')
    with open(path, 'w') as f:
        f.writelines(c)

    return send_file(path, as_attachment=True, download_name='plan.ics')


@app.route('/cron/morning')
def cron_morning():
    plan = generate_plan(datetime.now(TZ).date())
    top = plan['schedule'][0]
    msg = f"Good morning! City: {plan['city']}. Weather: {plan['weather']}\\nToday's training: {top['title']}\\nRemember: Protein + Creatine."
    send_telegram(msg)
    return jsonify({'ok': True})

@app.route('/cron/evening')
def cron_evening():
    msg = "Evening check-in: Did you complete Training, Protein+Creatine, and a Deep-Work sprint today? Open SoloCoach to tick your streak boxes."
    send_telegram(msg)
    return jsonify({'ok': True})

@app.template_filter('hm')
def fmt_hm(dt):
    return localize(dt).strftime('%H:%M')

if __name__ == '__main__':
    app.run(debug=True)
