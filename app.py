# -*- coding: utf-8 -*-
from flask import session,render_template, redirect, flash, request,url_for 	                # Flask is a microframework for Python 
from flask.ext.login import login_required,login_user,logout_user 				                # Some pages required login
from config import oid,app,lm,User,DB_USER,DB_NAME,DB_PWD,MY_EMAIL,LoginForm, SERVER, PORT, URL # All my config variables
from dateutil import tz  # For timezones
from flask import abort  # For errors whith ping/notify

import MySQLdb 	# Module to use mysql database
import datetime # Module to use date and time 
import time     # To use time (due to timestamps used for sensors, it is required to convert times into mins and hours)
import dateutil # Useful to parse dates&times
import smtplib  # Used to send emails
import uuid		# To generate unique ids


""" Init mail server """
server = smtplib.SMTP(SERVER,PORT)


""" Init database and retrieve all users (users are saved in a global dictionary called USERS) """
app.config.from_object('config')
try:
	db = MySQLdb.connect(user=DB_USER,passwd=DB_PWD,db=DB_NAME)
	cursor = db.cursor()
except:
	db.close()

USERS = {}
cursor.execute("select userid,username from users")
allusers = cursor.fetchall()
for u in allusers:
	my_user = User(u[1],u[0])
	USERS.update({u[0]:my_user}) 

""" --------------------------------------------------------------------------------------------------------------------- """
""" Check the length of a field in a form """
def check_length(str,n):
	if len(str)<n:
		return str
	else:
		return str[0:n]


""" Check it is a valid email addresss, return True or False """
def check_email(a):
	pos=a.find("@")
	if pos<=0:
		return False
	
	secondpart=a[pos::]
	dot=secondpart.find(".")
	return (dot>0 and len(secondpart)>3)


""" Convert a string to a new string, removing specific characters such as ' and keeping only ascii characters and spaces """
def remove_chars(txt): 
	import string
	res = []
	for ch in txt:
		if ch in string.ascii_lowercase:
			res.append(ch)
		elif ch in string.ascii_uppercase:
			res.append(ch)
		elif ch==" ":
			res.append(' ')
		elif ch.isdigit():
			res.append(ch)

	return "".join(res)


""" Remove all characters except punctuation, letters and numbers """
def format_comment(txt):
	import re
	return re.sub('[^A-Za-z0-9 !?,.:;]+','',txt)


""" User has requested to change password, get the date and the email of this user from its random generated key """
def request_details(akey):
	results = db_fetch_one("select date_application, email from pwd_reset where link='%s'" %akey)
	try:
		if results != [] and results[0] and results[1]:
			return results[0],results[1]
	except:
		pass
	return '',''		


""" Convert a string containing phone numbers, remove all unwanted characters """
def convert_string(astring):
	numbers = ['0','1','2','3','4','5','6','7','8','9']
	result = ''
	for i in range(len(astring)):
		if astring[i] in numbers:
			result += astring[i]
	return result


""" Check username compared to list of USERS """
def check_allowed(aname):
	for u in USERS.itervalues():
		if u.name == aname:
			return True
	return False


""" Check that this user is authorised and compare the given password with the one in database 
	Returns True if the user and passwords are correct, False otherwise """
def check_password(aname,apwd):
	if check_allowed(aname):
		right_password = db_fetch_one("select userid from users where username='%s' and password=md5('%s')" %(aname,apwd))
		# If the query does not return an empty set it means that the password is correct
		if right_password and right_password != []: 
			return True
	return False 


""" Get a result from a database query """
def db_fetch_one(aquery):
	try:
		cursor.execute(aquery)
		result = cursor.fetchone()
		return result
	except: #catching errors with query
		return []


""" From a given username get user details """
def	db_get_user(aname):
	my_user = db_fetch_one("select userid,username,email,phone,alert_hours,alert_minutes \
		                  from users where username='%s'" %aname)
	return my_user


""" Get all results from a query, returns an array """
def db_fetch_all(aquery):
	try:
		cursor.execute(aquery)
		result = cursor.fetchall()
		return result
	except: #catching errors with query
		return []


""" Check this email address is in database, returns the user id """
def is_email(myemail):
	results = db_fetch_one("select userid from users where email='%s'" %myemail)
	if results and results != []:
		return results[0]
	else:
		return 0 # userid=0 if no user with this email address in database


""" Get the last notify timestamp from database (from a phone number) """
def get_notify(phone):
	my_timestamp = db_fetch_one("select lastnotify from sensors where phonenumber='%s'" %phone)
	if my_timestamp and my_timestamp != []:
		return my_timestamp[0]
	else:
		return ""


""" Get the last ping timestamp from database (from a phone number) """
def get_ping(phone):
	my_timestamp = db_fetch_one("select lastping from sensors where phonenumber='%s'" %phone)
	if my_timestamp and my_timestamp != []:
		return my_timestamp[0]
	else:
		return ""


""" Get the last ping timestamp from database from an id (a sensor id) """
def get_ping_from_id(n):
	my_timestamp = db_fetch_one("select lastping from sensors where sensorid=%s" %n)
	if my_timestamp and my_timestamp != []:
		return my_timestamp[0]
	else:
		return ""


""" Get the flag (switch 'on' or 'off') from database from an id (a sensor id) """
def get_flag(n):
	my_flag = db_fetch_one("select flag from sensors where sensorid=%s" %n)
	if my_flag and my_flag != []:
		return my_flag[0]
	else:
		return 'off'


""" Insert some data into the database, this can also be used for updating queries """
def db_insert(aquery):
	cursor.execute(aquery)
	db.commit()


""" Get schedule id from a specific user """
def get_schedule_id(someone):
	result = db_fetch_one("select id from schedule where user=%s" %someone)
	if result and result != []:
		return result[0] # returns schedule id
	else:
		return 0 # schedule id = 0 if this user cannot be found


""" convert a string into an integer
	the function int() could be used 
	but it would crash with e.g.10.30 """
def convert_int(astring):
	import re
	dot = astring.find('.')
	if dot > 0:
		s =	astring[0:dot]
	else:
		s = astring

	number = re.sub(r'[^\d-]+', '', s)
	if number == '':
		return 0

	return int(number)

""" Check validity of times in schedule, insert this schedule into the database and return errors """
def validate_and_update(uid,category,params):
	errors  = {}
	counter = 0
	my_id   = get_schedule_id(uid)
	param_list = ['monday_start','monday_end','tuesday_start','tuesday_end','wednesday_start','wednesday_end',\
		'thursday_start','thursday_end','friday_start','friday_end','saturday_start','saturday_end','sunday_start','sunday_end']

	# SCHEDULE CATEGORY: Simple or Advanced 
	if my_id > 0 : # save changes in schedule
		db_insert("update schedule set category='%s' where id=%s" %(category,my_id))
	else: 		   # create a new schedule for this user 
		db_insert("insert into schedule (category,user) values ('%s',%s)" %(category,uid))
		my_id = get_schedule_id(uid)

	# CHECK TIME: needs to be 4 digits and start time < end time
	if category == 'Simple': 
		if len(params['start_time']) != 4 or not params['start_time'].isdigit(): # number with 4 digits
			errors['start_time'] = "HHMM"
		elif int(params['start_time'][0:2]) > 24 or int (params['start_time'][2:4]) > 60: #start time max hours 24 and max mins 60
			errors['start_time'] = "check HH<24 and MM<60"
		if len(params['end_time']) != 4 or not params['end_time'].isdigit():
			errors['end_time'] = "HHMM"
		elif int(params['end_time'][0:2]) > 24 or int (params['end_time'][2:4]) > 60: #end time max hours 24 nd max mins 60
			errors['end_time'] = "check HH<24 and MM<60"
		if convert_int(params['start_time']) > convert_int(params['end_time']): #start time before end time
			errors['end_time'] = "start time BEFORE end time"
		db_insert("update schedule set daily_start='%s', daily_end='%s' where id=%s" %(params['start_time'][0:4],params['end_time'][0:4],my_id))	
	else: # Advanced schedule 					 
		for p in param_list:
			if len(params[p]) != 4 or not params[p].isdigit(): # number with 4 digits
				errors[p] = "error"
			elif int(params[p][0:2]) > 24 or int(params[p][2:4]) > 60: #a time contains a max of 24 hours and 60 minutes
				errors[p] = "time!" 
			db_insert("update schedule set %s='%s' where id=%s" %(p,params[p][0:4],my_id))	
		for i in range(1,len(param_list),2): # check starting times are earlier than ending times
			if params[param_list[counter]] and params[param_list[i]] and convert_int(params[param_list[counter]])>convert_int(params[param_list[i]]):
				errors[param_list[counter]] = 'earlier'
			counter += 2
	return errors


""" Get current user, returns results as a dictionary rather an array """
def get_user(aname):
	user={}
	my_user = db_get_user(aname)
	if my_user:
		user['userid'] = my_user[0]
		user['username'] = my_user[1]
		user['email'] = my_user[2]
		user['phone'] = my_user[3]
		user['alert_hours'] = my_user[4]
		user['alert_minutes'] = my_user[5]
	return user


""" Retrieves all sensors in database """
def get_sensors(userid):
	all_sensors = db_fetch_all("select sensorname,flag,sensorid,lastping,lastnotify \
		                      from sensors where userref=%s" %userid)
	if all_sensors:
		return all_sensors
	else:
		return []


""" Retrieve a schedule in database (from a specific user) """
def get_schedule(userid):
	my_schedule = {} 
	my_schedule['start_times'] = []
	my_schedule['end_times'] = []

	all_times = db_fetch_one("select * from schedule where user=%s" % userid) # Schedule for this user in database

	if all_times and all_times != []:	
		if all_times[2] == 'Simple': # One start time, one end time
			my_schedule['times'] = 'Simple'
			my_schedule['start_times'] = [all_times[3]]
			my_schedule['end_times'] = [all_times[4]]	
		else: # 7 start times, 7 end times for every day in the week
			my_schedule['times'] = 'Advanced'
			timetable = [all_times[x] for x in range(5,19)]
			my_schedule['start_times'] = timetable[::2] # Every 2 values in my timetable
			my_schedule['end_times'] = [timetable[x] for x in range(1,14,2)] # all the rest of timetable
	else:
		my_schedule['times'] = 'Simple'		

	return my_schedule


""" From a sensors list returns an extended copy of this list
    The new list contains a status (ok or warning) and a time since the last update (format '... ago') """
def time_difference(sensor_list,someone):
	# The list indexes  0: name       1: flag (on/off)       2: id           3: ping        4: notify
	# The new list will have          5: alert status (ok/warning)           6: time since the last ping
	my_new_list = []

	alerts = db_fetch_one("select alert_hours,alert_minutes from users where userid=%s" %someone) # alert settings for this user
	diff_hours = alerts[0]
	diff_minutes = alerts[1]

	for s in sensor_list:
		my_alert="ok"
		my_difference=""
		if s[1] == "on" and s[3]: # this sensor is on and there is a ping
			dt = s[3].replace(tzinfo=dateutil.tz.gettz('UTC')) # Last notify is s[4] but without timezone				
			my_alert,my_difference = humanize(dt,diff_hours,diff_minutes) # diff_hours=0 diff_minutes=30 my_alert='ok' or 'warning'

		my_new_list.append([s[0],s[1],s[2],s[3],s[4],my_alert,my_difference]) 
	
	return my_new_list


""" compares a given date and time until now
	and returns a string that represents a time e.g. 3 days ago, 5 hours ago etc.
    Original by Dan Jacob - http://flask.pocoo.org/snippets/33/ but changed to use timezone awareness """
def humanize(dt,hh,mm,default="now"):
	# hh and mm are defined by the user (set length of time before alert)
    now = datetime.datetime.now(dateutil.tz.tzutc())

    diff = now - dt
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
       )

    # This bit has been added to alert the user if the sensor has been activated a long time ago  
    # If it has been more than a year or more than a month or more than a day  
    # or more than the user specified, then return a warning alert 
    # note that the time could be less than an hour but not the date so check date first
    alert = "ok"
    if periods[0][0] > 0 or periods[1][0] > 0 or periods[3][0] > 0:
    	alert = "warning"
    elif periods[4][0] > hh or (periods[4][0] == hh and periods[5][0] > mm):
	    alert = "warning"
    
    for period, singular, plural in periods:
        if period > 0:
            return alert,"%d %s ago" % (period, singular if period == 1 else plural)
        elif period < 0:
            break
    return alert,default


""" get today's day of the week (this is used to check if today is in schedule or not) """
def get_day():
	days_list = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
	d = datetime.datetime.today().weekday()
	return d, days_list[d]


""" compared the time now to a start and end time """
def is_in_schedule(start_time,end_time):
	ok = True 					  # by default, no schedule set up means it's fine
	now = datetime.datetime.now() # time now
	if start_time and start_time != "" and end_time and end_time != "":
		if int(start_time[0:2]) < now.hour and now.hour < int(end_time[0:2]):
			ok = True
		elif int(start_time[0:2]) == now.hour and int(start_time[2:4]) < now.minute and now.hour < int(end_time[0:2]):
			ok = True
		elif int(end_time[0:2]) == now.hour and  now.minute < int(end_time[2:4]):
			ok = True
		else:
			ok = False
	return ok		


""" get current user """
def current():
	try:
		if 'id' in session:
			current_user = get_user(session.get('id'))
		else:
			current_user = []
	except:
		current_user = []

	return current_user


""" Get error messages and part of the query depending on values given in form (new registration) """
def get_errors(who,pwd1,pwd2,phone,email,name):
	error=""
	query="insert into users(username,password"
	if who != "" and pwd1 != "": # Check given fields 
		if pwd1 != pwd2:
			error = "Passwords don\'t match"
		else:
			if phone != "":
				query += ",phone"
			if email != "" and check_email(email):
				query += ",email"
			if name !="":
				query += ",fullname"
	else:
		error = "Username and password are required"
	return error,query	

""" --------------------------------------------------------------------------------------------------------------------- """
""" Main route """
@app.route('/')
def main():
	return render_template('index.html',userdetails=current())


""" Contact page """
@app.route('/contact',methods=['GET','POST'])
def contact():
	if request.method == "POST":
		em = check_length(request.form['email'],30)
		if em != "" and check_email(em) and request.form['comments'] != "":
			# my message should appear like this:
			#from:....
			#to:......
			#name:....
			#
			#<message>
			message = 'from:' + em + '\nto:' + MY_EMAIL + '\n' + \
		          	  'name:'+ request.form['name'] + '\n\n' + format_comment(request.form['comments'])
			server.sendmail(request.form['email'],MY_EMAIL, message)
			return redirect(url_for('main'))
		else:
			return render_template('contact.html',userdetails=current(),errors="Email address is required and you have to fill the comments box")	
	return render_template('contact.html',userdetails=current())


""" About page """
@app.route('/about')
def about():
	return render_template('about.html',userdetails=current())


""" New registration """
@app.route('/new_user',methods=['GET','POST'])
def registration():
	if request.method == "POST":
		if len(request.form['username']) > 30 or len(request.form['pwd1']) > 60 or len(request.form['phone']) > 20\
		    or len(request.form['email']) > 30 or len(request.form['full_name']) > 50:
		    error = "Too many characters in field(s)"
		else:
			error, query = get_errors(request.form['username'],request.form['pwd1'],request.form['pwd2'],request.form['phone'],\
								 request.form['email'],request.form['full_name'])

		if error != "": # form incomplete, an errors has occured
			return render_template('register.html', message=error,username=request.form['username'])
		else:
			new_username = remove_chars(request.form['username'])
			query += ",alert_minutes,alert_hours) values('%s',md5('%s')" %(new_username,request.form['pwd1'])
			if "phone" in query:
				query += ",'%s'" %request.form['phone']
			if "email" in query:
				query += ",'%s'" %request.form['email']
			if "fullname" in query:
				query += ",'%s'" %remove_chars(request.form['full_name'])
			query += ",0,4)" #by default 4 hours before alert
			db_insert(query)		
			last_id = db_fetch_one("select userid from users where username='%s' and password=md5('%s')" %(new_username,request.form['pwd1']))
			my_user = User(new_username,last_id[0])
			USERS.update({last_id[0]:my_user}) 

			USER_NAMES = dict((u.name, u) for u in USERS.itervalues())
			login_user(USER_NAMES[new_username])
			oid = new_username
			session['id'] = new_username

			return redirect(url_for('settings'))
	return render_template('register.html')		


""" The user requires assistance with password """
@app.route('/reset_password',methods=['GET','POST'])
def reset_password():
	if request.method == "POST":
		if request.form['email'] and request.form['email'] != '' \
		and check_email(request.form['email']) and len(request.form['email']) <= 30: # an email has been provided 
			i = is_email(request.form['email']) 				  # id of user who registered this email address  
			message = 'from:' + request.form['email'] + '\nto:' + MY_EMAIL + '\n\n'
		
			if i > 0: # insert request into database and send an email to the user
				current_timestamp = datetime.datetime.now(dateutil.tz.tzutc()) 
				dt = current_timestamp.replace(tzinfo=None) #now without timezone
				secret = str(uuid.uuid4()) #secret string made of random letters and numbers
				db_insert("insert into pwd_reset (link,email,date_application) values ('%s','%s','%s')" %(secret,request.form['email'],dt))
				server.sendmail(request.form['email'],MY_EMAIL, message + 'You have requested to reset your password, to activate use this link:\n' +\
				URL + '/password/'+secret)
				return redirect(url_for('main'))
			else: # this email address is not in database, notify the user
				server.sendmail(request.form['email'],MY_EMAIL, message+'Sorry, your email is not registered. Please create an account with your email.')
				return render_template('newpassword.html',message="This email address does not exist in the database")	

		else: #error
			return render_template('newpassword.html',message="Email address is required (30 chars max.)")
	return render_template('newpassword.html')

	
""" The user is using the special link sent by email """
@app.route('/password/<string:query>', methods=['GET','POST'])
def save_password(query):
	if request.method == 'GET':
		return render_template('savepassword.html',user=query)

	elif request.method == "POST":
		dt, email = request_details(query) 
		if dt != '' : # this link exists check 	
			d = dt.replace(tzinfo=dateutil.tz.gettz('UTC')) 					# time with timezone (missing in database)
			alert, message = humanize(d,0,10) 									# time difference hours=0 minutes=10
			if alert == "ok" and request.form['pwd1'] == request.form['pwd2'] \
			and request.form['pwd1'] != "" and len(request.form['pwd1'])<= 60: 	# passwords matching and time ok
				if email != '': # update database
					db_insert("update users set password=md5('%s') where email='%s'" %(request.form['pwd1'],email))
					return redirect(url_for('main'))
				else:
					return render_template('savepassword.html',error="Email address not valid")	
			else:
				return render_template('savepassword.html',error="Matching passwords (60 chars max) are required and time limit is 10 mins")	
	
	return render_template('index.html', message="An error has occured")		


""" Checks the user login """
@app.route('/login',methods=['GET','POST'])
@oid.loginhandler
def login():
	form = LoginForm() 										   # Data in form saved for later
	USER_NAMES = dict((u.name, u) for u in USERS.itervalues()) # Load users allowed to login
	
	try: # If the user and the password are correct, change URL otherwise try again!
		if check_password(request.form['username'],request.form['password']) and login_user(USER_NAMES[request.form['username']],True):
			oid = request.form['username']
			session['remember_me'] = form.remember_me.data
			session['id'] = request.form['username']
		
			return redirect(url_for('settings'))
	except: # username is required, avoid errors for browsers that do not support the 'required' in the form
		pass

	return render_template('index.html',form=form)


""" Loads a user """
@lm.user_loader
def load_user(userid):
	return USERS.get(userid)


""" User wants to logout """
@app.route('/logout')
@login_required
def logout():
	if 'id' in session:
		session.pop('id', None)
	logout_user()
	return redirect(url_for('main'))


""" Adds a new sensor and inserts it into the database """
@app.route('/new_sensor',methods=['GET','POST'])	
@login_required
def add_sensor():
	if request.form['sensorname'] != "" and request.form['sensorcontact'] != "": # required fields 
		current_user = get_user(session.get('id'))
		current_timestamp = datetime.datetime.now(dateutil.tz.tzutc()) # utcnow().strftime('%Y-%m-%d %H:%M:%S')
		dt = current_timestamp.replace(tzinfo=None)
		db_insert("insert into sensors (sensorname,phonenumber,userref,flag,lastnotify) \
			values ('%s','%s',%s,'off','%s')" %(check_length(remove_chars(request.form['sensorname']),50),\
			check_length(convert_string(request.form['sensorcontact']),20),current_user['userid'],dt))
	return redirect(url_for('settings'))


""" The user requested a reset in its schedule (advanced schedule rather than simple schedule) """
@app.route('/reset_schedule',methods=['GET','POST'])	
@login_required
def reset():
	current_user = get_user(session.get('id'))
	my_id   = get_schedule_id(current_user['userid'])
	if my_id > 0: # means query update is possible 
		db_insert("update schedule set category='Advanced', daily_start='', daily_end ='' where user=%s" %current_user['userid'])
	return redirect(url_for('settings'))


""" The current user wants to delete this sensor """
@app.route('/delete_sensor/<string:query>', methods=['GET','POST'])
@login_required
def delete(query):
	# Delete sensor
	cursor.execute("delete from sensors where sensorid=%s" %query)
	db.commit()
	return redirect(url_for('settings'))


""" Pings a number, no login required for this """
@app.route('/api/ping/<string:query>')
def ping(query):
	# Get current date and time, mysql timestamp does not support timezone so turn off timezone
	current_timestamp = datetime.datetime.now(dateutil.tz.tzutc()) 
	dt = current_timestamp.replace(tzinfo=None) 

	phone_exist = db_fetch_one("select * from sensors where phonenumber='%s'" %query)
	# Update the last ping timestamp but careful not to lose the last notify timestamp, 
	# (if last notify is not in the query, mysql updates it automatically and set it to now)
	notify = get_notify(query)
	if phone_exist and phone_exist != []:
		db_insert("update sensors set lastping='%s',lastnotify='%s' where phonenumber='%s'"\
			       %(dt,notify,query))
		return "OK"
	else:
		#abort(404)
		return "Check number"	


""" Notifies a number, no login required for this """
@app.route('/api/notify/<string:query>')
def notify(query):
	phone_exist = db_fetch_one("select * from sensors where phonenumber='%s'" %query) # to check phone number
	ping = get_ping(query)

	if phone_exist and phone_exist != []: # this phone number exists
		user_details = db_fetch_one("select * from users where userid=%s" % phone_exist[3]) # user details
		alert_in_hour = user_details[6] # alert set by user in hour
		alert_in_min = user_details[7]  # alert set by user in minutes
		schedule_details = db_fetch_one("select * from schedule where user=%s" % phone_exist[3]) # schedule for this user
		
		ok = True # by default it is fine, even if there is no schedule set yet
		if schedule_details:
			if schedule_details[2] == "Advanced":
				d, my_day = get_day() # d for number of my day (0 for monday, 6 for sunday) or in letters my_day (useful for xxx_start, xxx_end)
				start_time = schedule_details[5 + 2*d] # 5 is monday_start,7,9,11,13,15,17 is sunday_start
				end_time = schedule_details[6 + 2*d]   # 6 is monday_end,8,10,12,14,16,18 is sunday_end
			else: # Simple schedule
				start_time = schedule_details[3]
				end_time = schedule_details[4]
			ok = is_in_schedule(start_time,end_time) #check time is in schedule	
				
		if ok: # update database
			now = datetime.datetime.now(dateutil.tz.tzutc())
			now = now.replace(tzinfo=None)
			db_insert("update sensors set lastnotify='%s',lastping='%s' where phonenumber='%s'"\
		          		%(now,ping,query))
		return "OK"
	else:
		#abort(404)
		return "Check number"


""" The current user is logged on and wants to know his/her settings """
@app.route('/settings',methods=['GET','POST'])
@login_required
def settings():
	all_settings = {} 
	errs = {}
	current_user = get_user(session.get('id')) # Look up for user and details (email,phone,alert settings)
	
	if request.method == "POST":	
		current_timestamp = datetime.datetime.now(dateutil.tz.tzutc()) 	# Current date&time 
		dt = current_timestamp.replace(tzinfo=None)						# Remove timezone for mysql
		sensors_list = get_sensors(current_user['userid'])				# Get all sensor ids for this user
		
		for sensor in sensors_list: # CHECK EACH SENSOR: ON OR OFF?
			s = "sensor_number["+str(sensor[2])+"]"
			my_flag = get_flag(sensor[2])
			ping = get_ping_from_id(sensor[2])
			try: # some request.form[sensor_number[?]] do not exist if the user has not changed the switch
				if (my_flag != request.form[s]): 
					db_insert("update sensors set flag='%s',lastping='%s',lastnotify='%s' where sensorid=%s" %(request.form[s],ping,dt,sensor[2]))
			except: 
				db_insert("update sensors set flag='off' where sensorid=%s" %sensor[2])

		# SCHEDULE SIMPLE/ADVANCED		
		if request.form['start_time'] != '' and request.form['end_time'] != '': # 1 start time, 1 end time
			all_settings['times'] = 'Simple'
		else: # 1 start time and 1 end time for each day of the week
			all_settings['times'] = 'Advanced'
		errs = validate_and_update(current_user['userid'],all_settings['times'],request.form) # Check no errors in schedule
	
		# PERSONAL INFO FOR USER
		h = convert_int(request.form['alert_hours'])
		m = convert_int(request.form['alert_mins'])
		if h > 24:
			h = 23
		if m > 50:
			m = 59
		if request.form['email'] == "" or check_email(request.form['email']):
			db_insert("update users set phone='%s',email='%s',alert_hours=%s,alert_minutes=%s where userid=%s" \
			%(check_length(convert_string(request.form['phone']),20),check_length(request.form['email'],30),str(h),str(m),current_user['userid']))
		else:
			#str(convert_int(request.form['alert_hours']))
			db_insert("update users set phone='%s',alert_hours=%s,alert_minutes=%s where userid=%s" \
			%(check_length(convert_string(request.form['phone']),20),str(h),str(m),current_user['userid']))
		if not errs:
			return redirect(url_for('settings'))

	sensors_list = get_sensors(current_user['userid']) 		
	current_schedule = get_schedule(current_user['userid']) 
	all_settings['switches'] = time_difference(sensors_list,current_user['userid']) # if sensor is ON check time    
	all_settings['start_times'] = current_schedule['start_times']
	all_settings['end_times'] = current_schedule['end_times']
	all_settings['times'] = current_schedule['times']
	return render_template('u.html',userdetails=get_user(current_user['username']),mysettings=all_settings,errors=errs)	


""" Run application """
if __name__ == '__main__':
  app.run(debug=True)
 