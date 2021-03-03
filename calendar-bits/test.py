import requests
from icalendar import Calendar, Event

url = "https://outlook.office365.com/owa/calendar/27a2308f94734ab991b77162811c768a@vmware.com/1257a1eb717749809f1ac68d4536e37617655276730703348902/calendar.ics"


icsFile = requests.get(url).text

#print (icsFile)

cal = Calendar.from_ical(icsFile)

print (cal)
