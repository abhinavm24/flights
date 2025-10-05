from fast_flights_opinionated import FlightQuery, Passengers, create_query, get_flights
from pprint import pprint
import datetime

query = create_query(
    flights=[
        FlightQuery(
            date=(datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
            from_airport="MYJ",
            to_airport="TPE",
        ),
    ],
    seat="economy",
    trip="one-way",
    passengers=Passengers(adults=2),
    language="en-US",
)

print(query)
res = get_flights(query)
pprint(res)
