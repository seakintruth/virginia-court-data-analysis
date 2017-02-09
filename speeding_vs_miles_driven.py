import csv
import sys
import re
import matplotlib.pyplot as plt
from os import environ, listdir
from os.path import isfile, join
from pprint import pprint

SPEEDING_KEYWORDS = ['SP', 'RD', 'R.D.', 'R/D', 'R D', 'RECK']
SPEEDING_VIOLATION_PATTERN = re.compile('[0-9]{2,3}\/[0-9]{1,2}')

def run():
    # Load daily vehicle miles traveled by locality from VDOT
    traffic_by_court = load_traffic_data()

    # Load court cases with speeding violations
    court_data_path = sys.argv[1]
    load_court_cases(court_data_path, traffic_by_court)

    # Graph miles driven per ticket by locality
    data = []
    # For each locality, create a tuple with the name of the locality
    # and the miles driven per ticket
    for court in traffic_by_court:
        # Remove Manassas because it makes the locality name too long
        localities = [l for l in court['locality'] if 'Manassas' not in l]
        locality = ' / '.join(localities)
        # Remove York and Craig because they are too high and skew the graph
        data.append((locality, court['all'] * 365 / court['chargeCount']))

    plt.figure(figsize=(10, 30))

    # Plot in order of miles per violation
    data.sort(key=lambda x: x[1], reverse=True)
    create_graph(data, 'miles_driven_vs_tickets_order_by_data.png')

    data = [x for x in data if 'York' not in x[0] and 'Craig' not in x[0]]
    data.sort(key=lambda x: x[0], reverse=True)
    create_graph(data, 'miles_driven_vs_tickets_order_by_locality.png')

def create_graph(data, filename):
    plt.clf()
    plt.barh(
        range(len(data)),
        [x[1] for x in data],
        tick_label=[x[0] for x in data])
    plt.tight_layout()
    plt.savefig(filename)

def load_traffic_data():
    traffic = {}
    with open('data/traffic_daily_vehicle_miles_traveled_2015.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['District Court FIPS Codes'] == '':
                continue
            if row['District Court FIPS Codes'] not in traffic:
                # Some district courts are represented in the traffic data
                # by mulitple localities. So instead of just loading the traffic
                # data, we have to make sure we combine rows that represent
                # the same court.
                traffic[row['District Court FIPS Codes']] = {
                    'locality': [],
                    'fips': [int(fips) for fips in row['District Court FIPS Codes'].split(',')],
                    'all': 0,
                    'interstate': 0,
                    'primary': 0,
                    'secondary': 0,
                    'limits': {},
                    'chargeCount': 0
                }
            cur = traffic[row['District Court FIPS Codes']]
            cur['locality'].append(row['Locality'].replace('City of ', ''))
            cur['all'] += int(row['All'])
            cur['interstate'] += int(row['Interstate'])
            cur['primary'] += int(row['Primary'])
            cur['secondary'] += int(row['Secondary'])
    return [traffic[fips] for fips in traffic]

def load_court_cases(path, traffic_by_court):
    files = [join(path, f) for f in listdir(path) if isfile(join(path, f))]

    # Read through court data and find cases with speeding charge, which have the
    # general form "actual_speed / speed_limit" e.g. 82/70. For each case, find
    # the traffic data that cooresponds with the court in which the charge was
    # filed. Store the charge in a dict where the key is the speed limit and
    # the value is a list of actual speeds that were in excess of that limit.
    for f in files:
        if not f.endswith('.csv'):
            continue
        print f
        with open(f) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                violation = get_speeding_violation(row['Charge'])
                if violation is None:
                    continue
                speed_actual = int(violation.split('/')[0])
                speed_limit = int(violation.split('/')[1])
                for court in traffic_by_court:
                    if int(row['court_fips']) in court['fips']:
                        if speed_limit not in court['limits']:
                            court['limits'][speed_limit] = []
                        #court['limits'][speed_limit].append(speed_actual)
                        court['chargeCount'] += 1
                        break
        break

def get_speeding_violation(charge):
    match = SPEEDING_VIOLATION_PATTERN.search(charge)
    if not match:
        # No regex match
        return None

    violation = match.group(0)
    if all([keyword not in charge for keyword in SPEEDING_KEYWORDS]) and violation != charge:
        # None of the speeding keywords are in the charge
        # and the violation isn't the only thing in the charge
        return None

    return violation

run()