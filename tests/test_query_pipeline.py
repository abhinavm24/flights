from datetime import date, timedelta

from fast_flights import FlightQuery, Passengers, create_query
from fast_flights.pb.flights_pb2 import Passenger as PbPassenger, Seat, Trip


def test_create_query_to_proto_roundtrip():
    departure = (date.today() + timedelta(days=30)).isoformat()
    flight = FlightQuery(date=departure, from_airport="JFK", to_airport="LAX")
    passengers = Passengers(adults=2, children=1, infants_in_seat=1)

    query = create_query(
        flights=[flight],
        seat="economy",
        trip="one-way",
        passengers=passengers,
        language="en-US",
        currency="USD",
    )

    info = query.to_proto()

    assert info.seat == Seat.ECONOMY
    assert info.trip == Trip.ONE_WAY
    assert info.data[0].from_airport.airport == "JFK"
    assert info.data[0].to_airport.airport == "LAX"
    assert info.data[0].date == departure

    passenger_values = list(info.passengers)
    assert passenger_values.count(PbPassenger.ADULT) == 2
    assert passenger_values.count(PbPassenger.CHILD) == 1
    assert passenger_values.count(PbPassenger.INFANT_IN_SEAT) == 1

    params = query.params()
    assert params["hl"] == "en-US"
    assert params["curr"] == "USD"
    assert "tfs" in params and params["tfs"]


def test_query_flight_data_property_matches_proto():
    future_date = date.today() + timedelta(days=30)
    flight = FlightQuery(date=future_date.isoformat(), from_airport="SFO", to_airport="ORD")
    query = create_query(flights=[flight], language="en-US", currency="USD")

    proto = query.to_proto()
    generated_flight = query.flight_data[0]

    assert generated_flight.date == proto.data[0].date
    assert generated_flight.from_airport.airport == proto.data[0].from_airport.airport
    assert generated_flight.to_airport.airport == proto.data[0].to_airport.airport


def test_flight_query_to_proto_accessor():
    flight = FlightQuery(date="2026-01-05", from_airport="CDG", to_airport="JFK")
    proto_flight = flight.to_proto()

    assert proto_flight.date == "2026-01-05"
    assert proto_flight.from_airport.airport == "CDG"
    assert proto_flight.to_airport.airport == "JFK"


def test_flight_query_to_proto_omits_optional_fields_when_missing():
    flight = FlightQuery(date="2026-06-01", from_airport="SFO", to_airport="NRT")

    proto = flight.to_proto()

    assert not proto.HasField("max_stops")
    assert list(proto.airlines) == []
