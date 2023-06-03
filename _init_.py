#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect, flash
import pymysql
pymysql.install_as_MySQLdb()
import pymysql.cursors

from functools import wraps
import ast
import hashlib
import datetime

#Initialize the app from Flask
app = Flask(__name__)

#Secret Key
app.secret_key = 'secretsecret'

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='',
                       db = 'air ticket reservation system',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

# confirm customer login requirement for access
def customer_login_confirmation(f):
	@wraps(f)
	def dec(*args, **kwargs):
		if not "username" in session:  # if they're not logged in, make them login
			return redirect(url_for("login"))
		elif session["userType"] != "customer":
			userType = session["userType"]
			if userType == "staff":
				return redirect(url_for("staff"))
		return f(*args, **kwargs)
	return dec

# confirm customer login requirement for access
def staff_login_confirmation(f):
	@wraps(f)
	def dec(*args, **kwargs):
		if not "username" in session:  # if they're not logged in, make them login
			return redirect(url_for("login"))
		elif session["userType"] != "staff":
			userType = session["userType"]
			if userType == "customer":
				return redirect(url_for("customer"))
		return f(*args, **kwargs)
	return dec


#Define a route to hello function
@app.route('/')
def hello():
	return render_template('index.html')

#Define route for login
@app.route("/Login", methods=["GET", "POST"])
def login():
	cursor = conn.cursor()
	if request.method == "POST":
		# check the credentials here...
		customerQuery = "SELECT * FROM customer WHERE customer_email = %s AND password = %s"
		staffQuery = "SELECT * FROM staff WHERE username = %s AND password = %s"

		# successful customer login
		if cursor.execute(customerQuery, (request.form['username'], request.form['password'])):
			session["username"] = request.form['username']
			session["userType"] = "customer"
			cursor.close()
			return redirect(url_for('customer'))

		# successful staff login
		elif cursor.execute(staffQuery, (request.form['username'], request.form['password'])):
			session["username"] = request.form['username']
			session["userType"] = "staff"

			query = 'SELECT airline_name FROM staff WHERE username = %s'
			cursor.execute(query,(session['username']))

			airline_name = cursor.fetchone()['airline_name']
			session['airline_name'] = airline_name

			cursor.close()
			return redirect(url_for('staff'))

		else:  # failed login
			flash('ERROR: INVALID USERNAME AND/OR PASSWORD! Please try again."', category='error')

	cursor.close()
	return render_template("login.html")

#Define route for register
@app.route("/Register", methods=["GET", "POST"])
def register():
	if request.method == "POST":
		userType = request.form['userType']  # customer or staff
		if userType == "customer":
			return redirect(url_for('register_customer')) # customer registration form

		elif userType == "staff":
			return redirect(url_for('register_staff')) # staff registration form

	return render_template("register.html") 


# registration for customers
@app.route("/Register/Customer", methods=["GET", "POST"])
def register_customer():
	cursor = conn.cursor()
	if request.method == "POST":
		# Checking if email is in the database already
		query = "Select * from customer where customer_email = %s"
		if cursor.execute(query, (request.form['email'])):  # if email already exists in database
			flash('ERROR: Email already exists, please try a different email.', category='error')
			return render_template("register_customer.html")

		if (len(request.form['email']) > 20):
			flash('ERROR: Email too long', category='error')
			return render_template("register_customer.html")

		if (len(request.form['password']) > 20):
			flash('ERROR: password too long', category='error')
			return render_template("register_customer.html")

		# else insert into database
		query = 'INSERT INTO customer VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
		try:
		   cursor.execute(query,(request.form['name'], request.form['email'],
		request.form['password'], request.form['buildingNum'], request.form['street'], 
		request.form['city'], request.form['state'], request.form['phoneNum'], request.form['passportNum'],
		request.form['expDate'], request.form['passportCountry'], request.form['DOB']))

		except:
			flash('Error! One or more fields not correctly filled out!', category='error')

		else: # successful registration
			conn.commit()
			cursor.close()
			flash('Account Created!', category='success')
			return redirect(url_for('login'))

	return render_template("register_customer.html")


# define route for registration for airline staff
@app.route("/Register/Staff", methods=["GET", "POST"])
def register_staff():
	cursor = conn.cursor()
	if request.method == "POST":
		# Checking if username is in the database already
		query = 'Select * from staff where username = %s'
		if cursor.execute(query, (request.form['email'])):  # if the email already exists in the database
			flash("ERROR: Email already exists, please try a different email.", category='error')
			return render_template("register_customer.html")

		# insert into database
		query = 'INSERT INTO staff VALUES (%s, %s, %s, %s, %s, %s, %s)'

		try: # test/try registering
		   cursor.execute(query,(request.form['username'], request.form['password'], 
		request.form['name'], request.form['DOB'], 
		request.form['phoneNum'], request.form['email'], request.form['airlineName']))

		except:  # error in registration
			flash('Error! One or more fields not correctly filled out!', category='error')

		else:  # successful registration
			conn.commit()
			cursor.close()
			flash('Staff Account Created!', category='success')
			return redirect(url_for('login'))

	return render_template("register_staff.html")


# Searching Directory
@app.route("/Search", methods=["GET", "POST"])
def search():
	cursor = conn.cursor()
	queryDepart = ""
	queryRound = "Select * FROM flight WHERE flight_number = -1"

	if request.method == "POST":
		if request.form.get("Search Airport"):
			depAirport = request.form['depAirport']
			arrAirport = request.form['arrAirport']
			depDate = request.form['depDate']
			retDate = request.form['retDate']

			# query checks flights with requested departure airport, arrivial airport and depature date
			queryDepart = "SELECT * FROM flight WHERE departure_airport = \"" + depAirport + "\" AND arrival_airport = \"" + arrAirport + "\"AND departure_date = \"" + depDate + "\""

			# IF Round trip
			if request.form['retDate']:
				# query checks round flights with requested departure airport, arrivial airport and depature date
				queryRound = "SELECT * FROM flight WHERE departure_airport = \"" + arrAirport + "\" AND arrival_airport = \"" + depAirport + "\"AND departure_date = \"" + retDate+ "\""

		if request.form.get("Search City"):
			depCity = request.form['depCity']
			arrCity = request.form['arrCity']

			# query checks airports within requested departure city
			query = "SELECT airport_name FROM airport WHERE city = \"" + depCity + "\""
			cursor.execute(query)
			dep_airports_in_city = cursor.fetchall()

			# query checks airports within requested arrivial city
			query = "SELECT airport_name FROM airport WHERE city = \"" + arrCity + "\""
			cursor.execute(query)
			arr_airports_in_city = cursor.fetchall()

			# query checks airports within range dates
			queryDepart = "SELECT * FROM flight WHERE departure_date = \"" + request.form['depDate'] + "\" AND ("

			# query checks airports that match city
			queryAirport1 = "";
			for dep in dep_airports_in_city:		# AND checks depature airports within the city
				for arr in arr_airports_in_city:	# AND checks arrival airports within the city
					queryAirport1 += "(departure_airport = \"" + dep.get('airport_name') + "\" AND arrival_airport = \"" + arr.get('airport_name') + "\") OR "
			
			queryAirport1 += "flight_number = -1)"
			queryDepart += queryAirport1;

			# if round trip
			if request.form['retDate']:
				# query checks airports within range dates
				queryRound = "Select * FROM flight WHERE arrival_date = \"" + request.form['retDate'] + "\" AND ("

				# query checks airports that match city
				queryAirport2 = "";
				for dep in dep_airports_in_city:		# AND checks departure airports within the city
					for arr in arr_airports_in_city:	# AND checks arrival airports within the city
						queryAirport2 += "(departure_airport = \"" + arr.get('airport_name') + "\" AND arrival_airport = \"" + dep.get('airport_name') + "\") OR "
				
				queryAirport2 += "flight_number = -1)"
				queryRound += queryAirport2;

		if request.form.get("Search Status"):
			airlineName = request.form['airlineName']
			flightNum =  request.form['flightNumber']
			depDate = request.form['depDate'] 
			arrDate = request.form['arrDate'] 

			# gets data on flight based on requested form information
			queryDepart = "SELECT * FROM flight WHERE airline_name = \"" + airlineName + "\" AND flight_number = \"" + flightNum+ "\"AND departure_date = \"" + depDate  + "\"" + "AND arrival_date = \"" + arrDate + "\""

		cursor.close()
		return redirect(url_for("results", queryDepart=queryDepart, queryRound=queryRound))

	cursor.close()
	if not "username" in session:
		return render_template("search.html")

	elif session['userType'] == "customer":
		return render_template("customer_search.html")

	elif session['userType'] == "staff":
		return render_template("staff_view.html")

# define route to result of search
@app.route("/Results/<queryDepart>/<queryRound>", methods=["GET", "POST"])
def results(queryDepart, queryRound=""):
	# query data for departing
	cursor = conn.cursor()
	cursor.execute(queryDepart)
	data = cursor.fetchall()

	# query data for round trip
	cursor = conn.cursor()
	cursor.execute(queryRound)
	data1 = cursor.fetchall()

	# Public User
	if not "username" in session:
		return render_template("results.html", data=data, data1=data1)

	# Customer, difference between customer and public user is that customer has option to buy a ticket for flight
	if session["userType"] == "customer":
		if request.method == "POST":
			flight_data = list(request.form)[0]
			return (redirect(url_for("customer_purchase", flight_data=flight_data)))

		return render_template("customer_results.html", data=data, data1=data1)

	cursor.close()
	return render_template("results.html", data=data, data1=data1)

# Define route for customer home page, confirmation required
@app.route("/Customer/Home")
@customer_login_confirmation
def customer():
	cursor = conn.cursor()

	# query gets all data of customer user
	query = 'Select * from customer where customer_email = %s'
	cursor.execute(query, (session['username']))

	profile = cursor.fetchone()
	name = profile['name']
	email = session['username']
	DoB = profile['date_of_birth']
	phoneNum = profile['phone_number']

	buildNum = profile['building_number']
	street = profile['street']
	city = profile['city']
	state = profile['state']

	pp_country = profile['passport_country']

	cursor.close()
	return render_template("customer.html", name=name, email = email, DoB = DoB, phoneNum = phoneNum,
					   buildNum = buildNum, street = street, city = city, state = state, pp_country = pp_country)

# Define route to customer's flights
@app.route("/Customer/MyFlights", methods=["GET", "POST"])
@customer_login_confirmation
def customer_flights():
	today = datetime.datetime.now()	# todays date
	timelimit = today - datetime.timedelta(days = 1) # 24 hour limit
	cursor = conn.cursor()

	# View Future Flights of Customer
	query = 'SELECT * FROM purchases NATURAL JOIN ticket NATURAL JOIN flight WHERE customer_email = %s AND departure_date > %s'
	cursor.execute(query, (session['username'], today))
	data = cursor.fetchall()

	query = 'SELECT * FROM purchases NATURAL JOIN ticket NATURAL JOIN flight WHERE customer_email = %s AND departure_date <= %s'
	cursor.execute(query, (session['username'], today))
	data1 = cursor.fetchall()

	if request.method == "POST":
		form = request.form.to_dict()
		customer_email = session['username']
		flightNum = list(form)[0]

		# getting customer’s ticket for flight and seeing if it is pass the time limit (24 hours) to cancel
		query = 'SELECT ticket_ID FROM ticket NATURAL JOIN purchases NATURAL JOIN flight WHERE customer_email = %s  AND flight_number = %s AND departure_date > %s ORDER BY ticket_ID DESC LIMIT 1'

		try:
			cursor.execute(query, (customer_email, flightNum, timelimit))
		except:
			flash('Too late to cancel this Flight!', category='error')
		else:
			ticket_ID = cursor.fetchone()['ticket_ID']

			# if there is still time, delete ticket purchase
			query = 'DELETE FROM purchases WHERE ticket_ID = %s'
			cursor.execute(query, (ticket_ID))

			flash('Flight Cancelled Succesfully', category='success')
			conn.commit()
			cursor.close()
			return redirect(url_for('customer'))

		cursor.close()

	cursor.close()
	return render_template("customer_flights.html", data=data, data1 = data1)

#Define route to customer purchasing flight ticket
@app.route("/Customer/Purchase/<flight_data>", methods=["POST", "GET"])
@customer_login_confirmation
def customer_purchase(flight_data):
	cursor = conn.cursor()
	data = flight_data.split("|")
	flightNum = data[0]
	airline_name = data[1]
	base_price = data[2]
	depDate = data[3]
	depTime = data[4]

	# getting airplane id for specific flight
	query = 'SELECT airplane_ID FROM flight WHERE flight_number = %s AND departure_date = %s AND departure_time = %s'
	cursor.execute(query,(flightNum, depDate, depTime))
	airplane_ID = cursor.fetchone()['airplane_ID']

	# getting number of seats of airplane based on airplane_ID
	query = 'SELECT num_seats FROM airplane WHERE airplane_ID = %s'
	cursor.execute(query, (airplane_ID))
	num_seats = cursor.fetchone()['num_seats']

	# getting number of tickets for flight
	query = 'SELECT count(*) FROM ticket WHERE flight_number = %s'
	cursor.execute(query, (flightNum))
	passengers = cursor.fetchone()['count(*)']

	# if number of seats for flight about to be filled up, increase base price of tickets
	if passengers >= (num_seats * 0.8):
		base_price = int(base_price) * 2

	curr = datetime.datetime.now()
	date = curr.strftime('%Y-%m-%d') 
	time = curr.strftime('%H:%M:00')

	if request.method == "POST":
		# seeing if and which tickets still available for purchase
		query = 'SELECT `ticket`.`ticket_ID` FROM `ticket` NATURAL JOIN flight LEFT JOIN `purchases` ON `purchases`.`ticket_ID` = `ticket`.`ticket_ID` WHERE customer_email IS NULL AND flight_number = %s AND departure_date > %s'
		cursor.execute(query, (flightNum, date))
		
		try:
			ticket_ID = cursor.fetchone()['ticket_ID']
			#  customer official buys ticket for flight if available
			query = 'INSERT into purchases VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)'
			cursor.execute(query, (ticket_ID, session['username'], base_price, date, time, request.form['cardType'], request.form['cardNumber'], request.form['cardName'], request.form['expDate']))
		except:
			flash('Ticket Unavailable! Can Not Be Purchased!', category = 'error')
		else:
			conn.commit()
			flash('Ticket succesfully purchased!', category = 'success')

	cursor.close()
	return render_template("customer_purchase.html", airline_name=airline_name, flightNum = flightNum, price=base_price, date = depDate, time = depTime)


# Review involves Rating & Comments
@app.route("/Review", methods=["GET", "POST"])
@customer_login_confirmation
def customer_review():
	cursor = conn.cursor()
	current_date = datetime.datetime.now()					# todays date
	today = current_date.strftime("%Y-%m-%d")				# break date up into year-month-day

	# getting all flights customer have already been on and they have not left a review for
	query = 'SELECT * FROM `purchases` NATURAL JOIN `ticket`  NATURAL JOIN `flight` LEFT JOIN `review` ON `review`.`flight_number` = `ticket`.`flight_number` WHERE `purchases`.`customer_email`= %s AND flight.arrival_date < %s AND `review`.`customer_email`IS NULL'
	cursor.execute(query, (session['username'], today))
	data = cursor.fetchall()

	if request.method == "POST":
		form = request.form.to_dict()
		flightNum = list(form)[2]
		comment = form['comment']
		rating = form['rating']
		customer_email = session['username']

		# after filling out form, customer can submit review
		query = 'INSERT into review VALUES(%s, %s, %s, %s)'
		try:
			cursor.execute(query,(customer_email, flightNum, rating, comment))
		except:
			flash('You have already rated this flight', category='error')
		else:
			conn.commit()
			flash('Review for this Flight have been submited!', category='success')
			cursor.close()

	cursor.close()
	return render_template("customer_review.html", data=data)

# Define route for customer Track Spending Budget
@app.route("/Spending", methods=["POST", "GET"])
@customer_login_confirmation
def spending():
	# Default shows spendings from last six months
	today = datetime.datetime.now()	# todays date
	last_year = today - datetime.timedelta(days = 365) # date of last six months
	last_six_months = today - datetime.timedelta(days = 183) # date of last six months
	start_date2 = last_year.strftime("%Y-%m-%d")			# break date up into year-month-day
	start_date = last_six_months.strftime("%Y-%m-%d")	# break date up into year-month-day
	end_date = today.strftime("%Y-%m-%d")				# break date up into year-month-day

	Months = [ 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'] # list of months abbreviated
	month_year = {}	# dictionary to keep track of unique months and years
	graph_labels = [] # x axis for graph
	graph_val = []		# y axis for graph

	cur_month = int(today.month)	# current month for today
	counter = cur_month - 5 # minus 5 because we are including this month

	for count in range(6): # get last 6 months including this months for graph
		if counter < 0:		# its negative when we go back the previous year
			month_year.update({Months[counter-1]: int(today.year) - 1})
		else:
			month_year.update({Months[counter-1]: int(today.year)})

		graph_labels.append(Months[counter-1])
		counter = counter + 1
	
	cursor = conn.cursor()
	total_spending = 0

	# getting purchase date and sold price of tickets that user bought within a time period
	query = 'SELECT purchase_date, sold_price FROM purchases WHERE customer_email = %s AND purchase_date >= %s AND purchase_date <= %s'
	cursor.execute(query, (session['username'], start_date, end_date))
	for price in cursor.fetchall():
		total_spending += price['sold_price']


	# track spendings by month for past 6 months
	monthly_spending = 0
	for mon in range(6):
		# getting purchase date and sold price of tickets that user bought within a time period
		query = 'SELECT purchase_date, sold_price FROM purchases WHERE customer_email = %s AND purchase_date >= %s AND purchase_date <= %s'
		cursor.execute(query, (session['username'], start_date, end_date))
		for price in cursor.fetchall():
			month_num = price['purchase_date'].month
			year_num = price['purchase_date'].year
			if (Months[month_num-1] == graph_labels[mon]) and (year_num == month_year.get(Months[month_num-1])):
				monthly_spending += price['sold_price']
		
		graph_val.append(monthly_spending)
		monthly_spending = 0 # reset for next month
	
	if request.method == "POST": # Update dates and total spending
		start_date = request.form['date1']	# new start date
		end_date = request.form['date2']	# new end date
		month_year = {}						# reset
		graph_labels = []					# reset
		graph_val = []						# reset

		date1 = datetime.datetime.strptime(start_date, "%Y-%m-%d")
		date2 = datetime.datetime.strptime(end_date, "%Y-%m-%d")

		start_year = int(date1.year)
		start_month = int(date1.month)
		
		end_year = int(date2.year)
		end_month = int(date2.month)

		year_counter = end_year - start_year
		month_counter = end_month - start_month + 1

		month_count = month_counter + (12 * year_counter)
		counter = start_month
		y_count = start_year

		for count in range(month_count): 
			if count < 12:
				if counter > 12:
					counter = 1
					y_count = y_count + 1

				month_year.update({Months[counter-1]: [y_count]})

			else:
				if counter > 12:
					counter = 1
					y_count = y_count + 1

				month_year[Months[counter-1]].append(y_count)

			graph_labels.append(Months[counter-1])
			counter = counter + 1

		cursor = conn.cursor()
		total_spending = 0
		monthly_spending = 0
		y_count = 0
		m_count = 0

		# track spendings by month with new timeframe
		for mon in range(month_count):
			if m_count > 11:
				m_count = 0
				y_count = y_count + 1
			
			# getting purchase date and sold price of tickets that user bought within a time period
			query = 'SELECT purchase_date, sold_price FROM purchases WHERE customer_email = %s AND purchase_date >= %s AND purchase_date <= %s'
			cursor.execute(query, (session['username'], date1, date2))
			for price in cursor.fetchall():
				month_num = price['purchase_date'].month
				year_num = price['purchase_date'].year
				if (Months[month_num-1] == graph_labels[mon]) and (year_num == month_year.get(Months[month_num-1])[y_count]):
					total_spending += price['sold_price']
					monthly_spending += price['sold_price']

			m_count = m_count + 1
			graph_val.append(monthly_spending)
			monthly_spending = 0 # reset

	cursor.close()
	return render_template("customer_spending.html", total = total_spending, labels=graph_labels, values=graph_val, start_date=start_date, end_date=end_date)

# STAFF PRIVILEGES
# Define route for staff home page, staff confirmation required
@app.route("/Staff/Home")
@staff_login_confirmation
def staff():
	cursor = conn.cursor()
	query = 'Select * from staff where username = %s'
	cursor.execute(query, (session['username']))

	profile = cursor.fetchone()

	username = session['username']
	name = profile['name']
	DoB = profile['date_of_birth']
	phoneNum = profile['phone_number']
	email = profile['staff_email']
	airline = profile['airline_name']


	cursor.close()
	return render_template("staff.html", username = username, name=name, DoB = DoB, phoneNum = phoneNum, email = email, airline = airline)


# Define route for staff viewing flights
@app.route("/View/Flights", methods=["POST", "GET"])
@staff_login_confirmation
def staff_flights():
	start_date = datetime.datetime.now()	# todays date
	end_date = start_date + datetime.timedelta(days = 30) # 24 hour limit

	start_date = start_date.strftime("%Y-%m-%d")			# break date up into year-month-day
	end_date = end_date.strftime("%Y-%m-%d")				# break date up into year-month-day
	cursor = conn.cursor()

	# see all flights for staff’s airline within time period (default 30 days)
	query = 'SELECT * FROM flight WHERE departure_date >= %s AND departure_date <= %s AND airline_name = %s'
	cursor.execute(query, (start_date, end_date, session['airline_name']))
	data = cursor.fetchall()

	if request.method == "POST":
		if request.form.get("update"):
			start_date = request.form['date1']	# new start date
			end_date = request.form['date2']	# new end date
			dep_port = request.form['airport1']	# departure airport
			arr_port = request.form['airport2']	# arrivial airport

			# see all flight for staff’s airline based on a range of dates, source/destination airports
			query = 'SELECT * FROM flight WHERE departure_date >= %s AND departure_date <= %s AND departure_airport = %s AND arrival_airport = %s AND airline_name = %s'
			cursor.execute(query, (start_date, end_date, dep_port, arr_port, session['airline_name']))
			data = cursor.fetchall()

		else:
			flight_data = list(request.form)[0]
			return (redirect(url_for("flight_passengers", flight_data=flight_data)))

	cursor.close()
	return render_template("staff_view.html", old = start_date, today = end_date, data=data)

@app.route("/View/Flights/<flight_data>", methods=["POST", "GET"])
@staff_login_confirmation
def flight_passengers(flight_data):
	cursor = conn.cursor()
	data = flight_data.split("|")

	flightNum = data[0]
	customer_email = data[1]
	purchase_date = data[2]
	customer_name = data[3]
	
	# see all passengers within the flight
	query = 'SELECT * FROM flight NATURAL JOIN purchases NATURAL JOIN ticket WHERE flight_number = %s AND airline_name = %s'
	cursor.execute(query,(flightNum, session['airline_name']))
	data = cursor.fetchall()

	cursor.close()
	return render_template("flightpassengers.html", data = data)

@app.route("/Create/Flight", methods=["GET", "POST"])
@staff_login_confirmation
def create_flight():
	if request.method == "POST":
		cursor = conn.cursor()

		flightNum = request.form['flightNumber']
		status = request.form['status']

		depAirport = request.form['departure_airport']
		depDate = request.form['departure_date']
		depTime = request.form['departure_time']

		arrAirport = request.form['arrival_airport']
		arrDate = request.form['arrival_date']
		arrTime = request.form['arrival_time']

		price = request.form['base_price']
		airplane_ID = request.form['airplane_ID']
		airline_name = session['airline_name']

		# Add/Create new flight into system
		query = 'INSERT into flight values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'

		try:
			cursor.execute(query, (flightNum, status, depAirport, depDate, depTime, arrAirport, arrDate,arrTime,price,airplane_ID,airline_name))
		except:
			flash('Error: Could Not Create this Flight!', category='error')
		else:
			conn.commit()
			flash('Flight has been created and added to database!', category='success')

			# getting number of seats in airplane for this newly created flight
			query = 'SELECT num_seats FROM airplane WHERE airplane_ID = %s'
			cursor.execute(query, (airplane_ID))
			num_seats = int(cursor.fetchone()['num_seats'])

			# get latest/highest ticket ID
			query = 'SELECT ticket_ID FROM ticket ORDER BY ticket_ID DESC'
			cursor.execute(query)
			tick = int(cursor.fetchone()['ticket_ID']) + 1

			for new_id in range(num_seats):
				if (new_id + tick) > 9999999999:
					flash('Error Can Not Create Any More Tickets!', category ='error')
					break
				else:
					# creating new tickets for new flight, number of new tickets = number of seats airplane has
					query = 'INSERT into ticket values (%s, %s, %s)'
					cursor.execute(query, (tick + new_id, airline_name, flightNum))
					conn.commit()

			cursor.close()
		
		cursor.close()

	return render_template("staff_create_flight.html")

@app.route("/Change/Status", methods=["GET", "POST"])
@staff_login_confirmation
def change_status():
	if request.method == "POST":
		cursor = conn.cursor()
		
		status = request.form['status']
		flightNum = request.form['flight_number']
		depAirport = request.form['departure_airport']
		depDate = request.form['departure_date']
		depTime = request.form['departure_time']
		status = request.form['status']

		# Update status of flight based on requested flight Number, departure airport, date and time
		query = 'Update flight SET status = %s WHERE flight_number = %s AND departure_airport = %s AND departure_date = %s AND departure_time = %s'
		try:
			cursor.execute(query,(status, flightNum, depAirport, depDate, depTime))
		except:
			flash("Error: Update to Status Failed", category = 'error')
		else:
			flash("Update to Status Successful", category = 'success')
			conn.commit()

		cursor.close()
	return render_template("staff_change_status.html")

@app.route("/Add", methods=["GET", "POST"])
@staff_login_confirmation
def add():
	cursor = conn.cursor()
	query = 'SELECT * FROM airplane WHERE airline_name = %s'
	cursor.execute(query, (session['airline_name']))
	data = cursor.fetchall()

	if request.method == "POST":
		cursor = conn.cursor()
		
		if request.form.get("airplane"):  # add new airplane
			airplane_ID = request.form['airplaneID']
			seats = request.form['seats']
			airline = session['airline_name']
			manufacture = request.form['manufacturer']
			age = request.form['age']

			# Add into system new airplane
			query = 'INSERT into airplane values (%s, %s, %s, %s, %s)'
			try:
				cursor.execute(query, (airplane_ID, seats, airline, manufacture, age))
			except:
				flash("Could Not Add Airplane", category = 'error')
			else:
				flash("Airplane Added Succesfully", category = 'success')
				conn.commit()

		elif request.form.get("airport"):  # add new airport
			airport = request.form['airportName']
			city = request.form['city']
			country = request.form['country']
			flight_type = request.form['type']

			# Add into system new airport
			query = 'INSERT into airport values (%s, %s, %s, %s)'
			try:
				cursor.execute(query, (airport, city, country, flight_type))
			except:
				flash("Could Not Add Airport", category = 'error')
			else:
				flash("Airport Added Succesfully", category = 'success')
				conn.commit()

		cursor.close()

	cursor.close()
	return render_template("staff_add.html", data = data, airline = session['airline_name'])

@app.route("/Ratings", methods=["POST", "GET"])
@staff_login_confirmation
def ratings():
	cursor = conn.cursor()

	# get all flights for airline ordered by recency
	query = 'SELECT * from flight where airline_name = %s ORDER BY departure_date DESC'
	cursor.execute(query, (session["airline_name"]))
	data = cursor.fetchall()

	if request.method == "POST":
		# get average rating of specific flight
		query = 'SELECT AVG(rating) FROM review WHERE flight_number = %s'
		cursor.execute(query, (request.form["flight_number"]))
		avg = cursor.fetchone()["AVG(rating)"]

		# get comments and rating from each customer that submitted a review
		query = 'SELECT customer_email, comment, rating FROM review WHERE flight_number = %s'
		cursor.execute(query, (request.form["flight_number"]))
		data = cursor.fetchall()
		cursor.close()

		return render_template("staff_review.html", avg=avg, data=data)

	cursor.close()
	return render_template("staff_rating.html", data=data)

@app.route("/Frequent")
@staff_login_confirmation
def frequent():
	cursor = conn.cursor()

	today = datetime.datetime.now()
	today = today.strftime("%Y-%m-%d")

	year_ago = datetime.datetime.now() - datetime.timedelta(days = 365)
	year_ago = year_ago.strftime("%Y-%m-%d")

	# Get customer who purchased the most tickets within a year's time
	query = 'SELECT customer_email FROM purchases NATURAL JOIN ticket WHERE airline_name = %s AND purchase_date >= %s AND purchase_date <= %s GROUP BY customer_email ORDER BY count(ticket_id) desc limit 1'
	cursor.execute(query, (session['airline_name'], year_ago, today))
	frequent_customer = cursor.fetchone()['customer_email']

	# Get basic information of this frequent customer
	query = 'SELECT * FROM customer WHERE customer_email = %s'
	cursor.execute(query, (frequent_customer))
	data = cursor.fetchall()

	# List all flights frequent customer has been on involving this airline
	query = 'SELECT * FROM flight NATURAL JOIN ticket NATURAL JOIN purchases WHERE airline_name = %s AND customer_email = %s ORDER BY departure_date DESC'
	cursor.execute(query, (session['airline_name'],frequent_customer))
	flight_data = cursor.fetchall()

	cursor.close()

	return render_template("staff_frequent.html", data=data, flight_data = flight_data, year_ago = year_ago, today = today)

@app.route("/Reports", methods=["POST", "GET"])
@staff_login_confirmation
def report():
	# Default shows spendings from last six months
	today = datetime.datetime.now()	# todays date
	last_year = today - datetime.timedelta(days = 365) # date of last six months
	last_six_months = today - datetime.timedelta(days = 183) # date of last six months
	start_date = last_six_months.strftime("%Y-%m-%d")	# break date up into year-month-day
	end_date = today.strftime("%Y-%m-%d")				# break date up into year-month-day

	Months = [ 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'] # list of months abbreviated
	month_year = {}	# dictionary to keep track of unique months and years
	graph_labels = [] # x axis for graph
	graph_val = []		# y axis for graph

	cur_month = int(today.month)	# current month for today
	counter = cur_month - 5 # minus 5 because we are including this month

	for count in range(6): # get last 6 months including this months for graph
		if counter < 0:		# its negative when we go back the previous year
			month_year.update({Months[counter-1]: int(today.year) - 1})
		else:
			month_year.update({Months[counter-1]: int(today.year)})

		graph_labels.append(Months[counter-1])
		counter = counter + 1
	
	cursor = conn.cursor()

	# track tickets by month for past 6 months
	num_tickets = 0
	total_tickets = 0
	for mon in range(6):
		# get purchase date and number of tickets within time fram
		query = 'SELECT purchase_date, count(ticket_ID) FROM purchases WHERE purchase_date >= %s AND purchase_date <= %s GROUP BY purchase_date'
		cursor.execute(query, (start_date, end_date))
		for tick in cursor.fetchall():
			month_num = tick['purchase_date'].month
			year_num = tick['purchase_date'].year
			if (Months[month_num-1] == graph_labels[mon]) and (year_num == month_year.get(Months[month_num-1])):
				num_tickets += tick['count(ticket_ID)']
				total_tickets += tick['count(ticket_ID)']
		
		graph_val.append(num_tickets)
		num_tickets = 0 # reset for next month
	
	if request.method == "POST": # Update dates
		start_date = request.form['date1']	# new start date
		end_date = request.form['date2']	# new end date
		month_year = {}						# reset
		graph_labels = []					# reset
		graph_val = []						# reset

		date1 = datetime.datetime.strptime(start_date, "%Y-%m-%d")
		date2 = datetime.datetime.strptime(end_date, "%Y-%m-%d")

		start_year = int(date1.year)
		start_month = int(date1.month)
		
		end_year = int(date2.year)
		end_month = int(date2.month)

		year_counter = end_year - start_year
		month_counter = end_month - start_month + 1

		month_count = month_counter + (12 * year_counter)
		counter = start_month
		y_count = start_year

		for count in range(month_count): 
			if count < 12:
				if counter > 12:
					counter = 1
					y_count = y_count + 1

				month_year.update({Months[counter-1]: [y_count]})

			else:
				if counter > 12:
					counter = 1
					y_count = y_count + 1

				month_year[Months[counter-1]].append(y_count)

			graph_labels.append(Months[counter-1])
			counter = counter + 1

		cursor = conn.cursor()
		num_tickets = 0
		total_tickets = 0
		y_count = 0
		m_count = 0
		
		# track tickets by month with new timeframe
		for mon in range(month_count):
			if m_count > 11:
				m_count = 0
				y_count = y_count + 1
			
			# get purchase date and number of tickets within time fram
			query = 'SELECT purchase_date, count(ticket_ID) FROM purchases WHERE purchase_date >= %s AND purchase_date <= %s GROUP BY purchase_date'
			cursor.execute(query, (date1, date2))
			for tick in cursor.fetchall():
				month_num = tick['purchase_date'].month
				year_num = tick['purchase_date'].year
				if (Months[month_num-1] == graph_labels[mon]) and (year_num == month_year.get(Months[month_num-1])[y_count]):
					num_tickets += tick['count(ticket_ID)']
					total_tickets += tick['count(ticket_ID)']

			m_count = m_count + 1
			graph_val.append(num_tickets)
			num_tickets = 0 # reset

	cursor.close()
	return render_template("staff_report.html", labels=graph_labels, values=graph_val, total_tickets = total_tickets, start_date=start_date, end_date=end_date)


@app.route("/Revenue", methods=["POST", "GET"])
@staff_login_confirmation
def revenue():
	today = datetime.datetime.now()	# todays date
	last_year = today - datetime.timedelta(days = 365) # date of last six months

	start_date2 = last_year.strftime("%Y-%m-%d")	# break date up into year-month-day
	end_date = today.strftime("%Y-%m-%d")				# break date up into year-month-day

	Months = [ 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'] # list of months abbreviated

	month_year = {}			# dictionary1 to keep track of unique months and years
	graph_labels = []		# x axis for graph1
	graph_val = []			# y axis for graph1

	month_year2 = {}		# dictionary2 to keep track of unique months and years
	graph_labels2 = []		# x axis for graph2
	graph_val2 = []			# y axis for graph2

	cursor = conn.cursor()
	last_month = int(today.month) - 1	# current month for today
	start_date1 = Months[last_month-1]	# break date up into year-month-day
	
	if last_month < 0:		# its negative when we go back the previous year
		month_year.update({Months[last_month-1]: int(today.year) - 1})
	else:
		month_year.update({Months[last_month-1]: int(today.year)})

	graph_labels.append(Months[last_month-1])

	# track tickets by month for last month
	month_rev = 0

	# get purchase date and sold price within time frame
	query = 'SELECT purchase_date, sold_price FROM purchases WHERE purchase_date >= %s AND purchase_date <= %s'
	cursor.execute(query, (start_date1, end_date))
	for tick in cursor.fetchall():
		month_num = tick['purchase_date'].month
		year_num = tick['purchase_date'].year
		if (Months[month_num-1] == graph_labels[0]) and (year_num == month_year.get(Months[month_num-1])):
			month_rev += tick['sold_price']	
	graph_val.append(month_rev)

	counter = last_month - 10
	for count in range(12): # get last 12 months including this months for graph
		if counter < 0:		# its negative when we go back the previous year
			month_year2.update({Months[counter-1]: int(today.year) - 1})
		else:
			month_year2.update({Months[counter-1]: int(today.year)})

		graph_labels2.append(Months[counter-1])
		counter = counter + 1
	
	# track tickets by month for past 12 months
	monthly_revenue = 0
	total_rev = 0
	for mon in range(12):
		# get purchase date and sold price within time frame
		query = 'SELECT purchase_date, sold_price FROM purchases WHERE purchase_date >= %s AND purchase_date <= %s'
		cursor.execute(query, (start_date2, end_date))
		for tick in cursor.fetchall():
			month_num = tick['purchase_date'].month
			year_num = tick['purchase_date'].year
			if (Months[month_num-1] == graph_labels2[mon]) and (year_num == month_year2.get(Months[month_num-1])):
				monthly_revenue += tick['sold_price']	

		graph_val2.append(monthly_revenue)
		total_rev += monthly_revenue
		monthly_revenue = 0 # reset for next month

	cursor.close()
	return render_template("staff_revenue.html", labels=graph_labels, values=graph_val, month_rev = month_rev, total_rev = total_rev,
					   labels2=graph_labels2, values2=graph_val2, start_date1 = start_date1, start_date2 = start_date2, end_date = end_date)

@app.route('/logout')
def logout():
	session.pop('username')
	flash("Logged Out Successfully", category = 'success')
	return redirect('/')
		
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
	app.run('127.0.0.1', 5000, debug = True)
