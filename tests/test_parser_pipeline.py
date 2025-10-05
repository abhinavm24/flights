import json

from fast_flights_opinionated.parser import ParsedFlights, parse


def _build_raw_payload():
    segment = [None] * 22
    segment[3] = "JFK"
    segment[4] = "John F Kennedy Intl"
    segment[5] = "Los Angeles Intl"
    segment[6] = "LAX"
    segment[8] = [10, 30]
    segment[10] = [13, 15]
    segment[11] = 300
    segment[17] = "Boeing 777"
    segment[20] = [2025, 7, 15]
    segment[21] = [2025, 7, 15]

    extras = [None] * 9
    extras[7] = 120
    extras[8] = 150

    flight_details = [None] * 23
    flight_details[0] = "one-way"
    flight_details[1] = ["AA"]
    flight_details[2] = [segment]
    flight_details[22] = extras

    entry = [flight_details, [[None, 45600]]]

    payload = [None] * 8
    payload[3] = [[entry]]
    payload[7] = [
        None,
        [
            [["SA", "Star Alliance"]],
            [["AA", "American Airlines"]],
        ],
    ]
    return payload


def test_parse_pipeline_produces_parsed_flights():
    payload = _build_raw_payload()
    json_payload = json.dumps(payload)
    html = f'<html><body><script class="ds:1">data:{json_payload},</script></body></html>'

    result = parse(html)

    assert isinstance(result, ParsedFlights)
    assert len(result) == 1

    flight = result[0]
    assert flight.price == 45600
    assert flight.airlines == ["AA"]
    assert flight.flights[0].from_airport.code == "JFK"
    assert flight.flights[0].to_airport.code == "LAX"
    assert flight.carbon.emission == 120
    assert flight.carbon.typical_on_route == 150

    metadata = result.metadata
    assert metadata.airlines[0].code == "AA"
    assert metadata.alliances[0].code == "SA"
