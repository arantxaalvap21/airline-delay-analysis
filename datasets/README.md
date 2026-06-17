# Datasets

Los datos utilizados en este proyecto provienen de la base pública **Reporting Carrier On-Time Performance** del Bureau of Transportation Statistics (BTS).

Por tamaño, los archivos CSV no se incluyen directamente en el repositorio. Para reproducir el proyecto, descargar manualmente los datos desde TranStats (https://www.transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ&utm_source=chatgpt.com) con los siguientes filtros:

- Database: On-Time
- Table: Reporting Carrier On-Time Performance
- Geography: All
- Year: 2026
- Periods: January, February, March


Marcando las siguientes casillas:
- Year
- Quarter
- Month
- DayofMonth
- DayOfWeek
- FlightDate

- Reporting_Airline
- DOT_ID_Reporting_Airline
- IATA_CODE_Reporting_Airline
- Flight_Number_Reporting_Airline

- OriginAirportID
- Origin
- OriginCityName
- OriginState
- OriginStateName

- DestAirportID
- Dest
- DestCityName
- DestState
- DestStateName

- CRSDepTime
- DepTime
- DepDelay
- DepDelayMinutes
- DepDel15
- DepTimeBlk
- TaxiOut
- WheelsOff

- CRSArrTime
- ArrTime
- ArrDelay
- ArrDelayMinutes
- ArrDel15
- ArrTimeBlk
- TaxiIn
- WheelsOn

- Cancelled
- CancellationCode
- Diverted

- CRSElapsedTime
- ActualElapsedTime
- AirTime
- Flights
- Distance
- DistanceGroup

- CarrierDelay
- WeatherDelay
- NASDelay
- SecurityDelay
- LateAircraftDelay

Guardar los archivos en:

datasets/raw/

con los siguientes nombres:

- flights_2026_01.csv
- flights_2026_02.csv
- flights_2026_03.csv
