from math import sqrt
from random import random
import json
import os
import requests

# Getting the data
def get_data_():
    # legislator id and their corresponding votes on bills (yes/no)
    # vote values: (1: yes) (0: no)
    # {legislator_id1 : { bill_id1: vote_value1, bill_id2: vote_value2, ...}, ...}
    legislator_votes = {}
    legislator_names = {}

    # list of bill ids
    bill_list = []

    # get bill information from California and load the JSON (one page of 2000 entries)
    url = "http://openstates.org/api/v1/bills/?state=ca&type=bill&page=1&per_page=1000"
    #url = "http://openstates.org/api/v1/bills/?state=ca&chamber=upper&type=bill&page=1&per_page=10"
    response = requests.get(url)

    # process json content
    content = response.json()

    bill_id = ''
    for bill_struct in content:
        bill_id = bill_struct['id']

        if bill_id != '':
            bill_list.append(bill_id)

    # process bill list so we can get votes and legislators
    for bill_id in bill_list:
        url = "http://openstates.org/api/v1/bills/" + bill_id
        bill_response = requests.get(url)

        content = bill_response.json()
        votes = content['votes'][0]

        # go through all the yes votes
        yes_votes = votes['yes_votes']
        for yes in yes_votes:
            if not legislator_votes.__contains__(yes['leg_id']):
                # we need to add the legislator to the vote and name list!
                legislator_votes[yes['leg_id']] = {}
                legislator_names[yes['leg_id']] = [yes['name']]

            # vote value 1 means 'yes'
            legislator_votes[yes['leg_id']][bill_id] = 1

        # go through all the no votes
        no_votes = votes['no_votes']
        for no in no_votes:
            if not legislator_votes.__contains__(no['leg_id']):
                # we need to add the legislator to the vote and name list!
                legislator_votes[no['leg_id']] = {}
                legislator_names[no['leg_id']] = [no['name']]

            # vote value 0 means 'no'
            legislator_votes[no['leg_id']][bill_id] = 0

    # go through each legislator and get their party
    # legislator ids are taken from bill info, so we could get a mix of active
    # and inactive legislators in our graph data
    for leg_index in legislator_names:
        url = "http://openstates.org/api/v1/legislators/" + leg_index
        leg_response = requests.get(url)

        content = leg_response.json()

        if 'party' in content.keys():
            party_string = content['party']
            if party_string == "Democratic":
                legislator_names.get(leg_index).append('blue')
            elif party_string == "Republican":
                legislator_names.get(leg_index).append('red')
        else:
            legislator_names.get(leg_index).append('gray')

    return legislator_votes, legislator_names

# Returns a distance-based similarity score for person1 and person2
def sim_distance(data, person1, person2):
    # Get the list of shared_items
    si = {}
    for bill in data[person1]:
        if bill in data[person2]:
            si[bill] = 1

    # if they have no ratings in common, return 0
    if len(si) == 0:
        return 1

    # Add up the squares of all the differences of the votes
    sum_of_squares = sum([pow(data[person1][bill]-data[person2][bill], 2)
                          for bill in si])

    #return sqrt(sum_of_squares)
    return 1 - 1/(1+sqrt(sum_of_squares))

def scaledown(data, distance=sim_distance, rate=0.01):
    n = len(data)

    # The real distances between every pair of items
    data_keys = list(data.keys())
    realdist = [[distance(data, data_keys[i], data_keys[j]) for j in range(n)]
                for i in range(0, n)]
    print("realdist= ", realdist)

    # Randomly initialize the starting points of the locations in 2D
    loc = [[random(), random()] for i in range(n)]
    fakedist = [[0.0 for j in range(n)] for i in range(n)]

    lasterror = None
    for i in range(0, 1000):
        # Find projected distances
        for k in range(n):
            for j in range(n):
                fakedist[k][j] = sqrt(sum([pow(loc[k][x]-loc[j][x], 2)
                                           for x in range(len(loc[k]))]))
        #print("fakedist= ", fakedist)

        # Move points
        grad = [[0.0, 0.0] for i in range(n)]

        totalerror = 0
        for k in range(n):
            for j in range(n):
                if j == k:
                    continue
                # The error is percent difference between the distances
                if realdist[j][k] == 0:
                    errorterm = (fakedist[j][k]-realdist[j][k])*.1
                else:
                    errorterm = (fakedist[j][k]-realdist[j][k])/realdist[j][k]

                # Each point needs to be moved away from or towards the other
                # point in proportion to how much error it has
                if fakedist[j][k] != 0:
                    grad[k][0] += ((loc[k][0]-loc[j][0])/fakedist[j][k])*errorterm
                    grad[k][1] += ((loc[k][1]-loc[j][1])/fakedist[j][k])*errorterm

                # Keep track of the total error
                totalerror += abs(errorterm)
        print("totalerror= ", totalerror)

        # If the answer got worse by moving the points, we are done
        if lasterror and lasterror < totalerror:
            break
        lasterror = totalerror

        # Move each of the points by the learning rate times teh gradient
        for k in range(n):
            loc[k][0] -= rate*grad[k][0]
            loc[k][1] -= rate*grad[k][1]

    return loc, data_keys

def plot_legs(coords, legs, data_keys):
    # Organize data for plot
    plot_input = {'data':[]}
    for i in enumerate(data_keys):
        curr_data = {'x':coords[i[0]][0],
                     'y':coords[i[0]][1],
                     'name':legs[i[1]][0],
                     'color':legs[i[1]][1]}
        plot_input['data'].append(curr_data)

    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))
    file = open(os.path.join(__location__, 'graph.json'), 'w')
    json.dump(plot_input, file)

def get_data(testcase):
    if testcase == 0:
        legislator_votes, legislator_names = get_data_()
    else:
        legislator_names = {'1': ['Al Bundy', 'purple'],
                            '2': ['Budha', 'purple'],
                            '3': ['China', 'orange'],
                            '4': ['Dr. Pepper', 'orange']}
        if testcase == 1:
            # A and B are similar; C = D
            legislator_votes = {'1': {'Water Bill':1, 'Tax Bill':0, 'Health Care Bill':1},
                                '2': {'Water Bill':0, 'Tax Bill':0, 'Health Care Bill':1},
                                '3': {'Water Bill':0, 'Tax Bill':1, 'Health Care Bill':0},
                                '4' :{'Water Bill':0, 'Tax Bill':1, 'Health Care Bill':0}}
        elif testcase == 2:
            # C = D
            legislator_votes = {'3': {'Water Bill':0, 'Tax Bill':1, 'Health Care Bill':0},
                                '4' :{'Water Bill':0, 'Tax Bill':1, 'Health Care Bill':0}}
        elif testcase == 3:
            # A and B share no bills
            legislator_votes = {'1': {'Water Bill':1, 'Tax Bill':0},
                                '2': {'Health Care Bill':1}}
    return legislator_votes, legislator_names

def main():
    # Get data
    legislator_votes, legislator_names = get_data(0)
    print("Done getting data.")
    #print(legislator_votes)

    # Get x-y coordinates for legislators
    coords, data_keys = scaledown(legislator_votes)
    #print("coords= ", coords)
    #print("data_keys= ", data_keys)

    # Plot legislators
    plot_legs(coords, legislator_names, data_keys)

if __name__ == '__main__':
    main()
