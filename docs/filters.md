# :material-filter: Filters
Filters are used to generate the `tfs` query parameter. In short, you make queries with filters.

You can create a query with `create_query()` and pass it to `get_flights()` (optionally with an integration name if you want to use a provider like Bright Data).

## FlightData
This specifies the general flight data: the date, departure & arrival airport, and the maximum number of stops (untested).

```python
data = FlightData(
    date="2025-01-01", 
    from_airport="TPE", 
    to_airport="MYJ", 
    airlines=["DL", "AA", "STAR_ALLIANCE"], # optional
    max_stops=10  # optional
)
```

Note that for `round-trip` trips, you'll need to specify more than one `FlightData` object for the `flight_data` parameter.

The values in `airlines` has to be a valid 2 letter IATA airline code, case insensitive. They can also be one of `SKYTEAM`, `STAR_ALLIANCE` or `ONEWORLD`. Note that the server side currently ignores the `airlines` parameter added to the `FlightData`s of all the flights which is not the first flight. In other words, if you have two `FlightData`s for a `round-trip` trip: JFK-MIA and MIA-JFK, and you add `airlines` parameter to both `FlightData`s, only the first `airlines` will be considered for the whole search. So technically `airlines` could be a better fit as a parameter for `TFSData` but adding to `FlightData` is the correct usage because if the backend changes and brings more flexibility to filter with different airlines for different flight segments in the future, which it should, this will come in handy.

## Trip
Either one of:

- `round-trip`
- `one-way`
- :material-alert: `multi-city` (unimplemented)

...can be used.

If you're using `round-trip`, see [FlightData](#flightdata).

## Seat
Now it's time to see who's the people who got $$$ dollar signs in their names. Either one of:

- `economy`
- `premium-economy`
- `business`
- `first`

...can be used, sorted from the least to the most expensive.

## Passengers
A family trip? No problem. Just tell us how many adults, children & infants are there.

There are some checks made, though:

- The sum of `adults`, `children`, `infants_in_seat` and `infants_on_lap` must not exceed `9`.
- You must have at least one adult per infant on lap (which frankly, is easy to forget).

```python
passengers = Passengers(
    adults=2,
    children=1,
    infants_in_seat=0,
    infants_on_lap=0
)
```

## Example
Here's a simple example on how to create a query:

```python
query = create_query(
    flights=[
        FlightQuery(
            date="2025-01-01",
            from_airport="TPE",
            to_airport="MYJ",
        )
    ],
    trip="round-trip",
    passengers=Passengers(adults=2, children=1, infants_in_seat=0, infants_on_lap=0),
    seat="economy",
    max_stops=1,
)

query.to_str()  # Base64-encoded payload used for ?tfs
query.url()     # Full Google Flights URL (handy for debugging)
```
