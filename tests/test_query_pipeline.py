from fast_flights import FlightQuery, Passengers, create_query
from fast_flights.pb.flights_pb2 import Passenger as PbPassenger, Seat, Trip


def test_create_query_to_proto_roundtrip():
    flight = FlightQuery(date="2025-07-15", from_airport="JFK", to_airport="LAX")
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
    assert info.data[0].date == "2025-07-15"

    assert info.passengers.count(PbPassenger.ADULT) == 2
    assert info.passengers.count(PbPassenger.CHILD) == 1
    assert info.passengers.count(PbPassenger.INFANT_IN_SEAT) == 1

    params = query.params()
    assert params["hl"] == "en-US"
    assert params["curr"] == "USD"
    assert "tfs" in params and params["tfs"]


def test_query_flight_data_property_matches_proto():
    flight = FlightQuery(date="2025-12-01", from_airport="SFO", to_airport="ORD")
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
