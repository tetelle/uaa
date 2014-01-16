
CREATE TABLE settings(
	id INTEGER PRIMARY KEY,
	username TEXT,
	email TEXT,
	phone TEXT,
	alert_hours INTEGER,
	alert_minutes INTEGER
);

/* Basic sensor info - could really do with a separate schedule
and a setting for the email address that the notification will come 
from. For another way ..... */
CREATE TABLE sensors(
	id INTEGER PRIMARY KEY,
	user INTEGER,
	name TEXT,
	active BOOLEAN,
	start TEXT,
	end TEXT
);



CREATE TABLE add_sensors(
	id INTEGER PRIMARY KEY,
	name TEXT
);