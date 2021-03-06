#!/usr/bin/env python3

# This file can be run to update the data from the source.
# The data is scraped from the website and written to a .json file.

import urllib.request
import json
import datetime
import os
import sys

from lxml import etree


def get_time_json():
    # Return the time in JSON format with timezond in it.
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()


def get_data():
    """
    Gets all data from multiple online XML schemes and put necessary data in dictionary
    :return: the raw data in python dictionary
    """
    # this is where all data is going to be stored, this will be dumped to json at the end
    data = {}

    data_url = 'http://miv.opendata.belfla.be/miv/verkeersdata'
    try:
        data_xml = urllib.request.urlopen(data_url)
    except urllib.error.URLError as e:
        print('[*] Error: downloading data failed with reason: ', e.reason)
        sys.exit(1)
    print('[*] Info: fetching data appeared to be succesfull.')
    root = etree.parse(data_xml).getroot()

    for measure_point in root.iter('meetpunt'):
        unique_id = int(measure_point.attrib['unieke_id'])
        e_data = {}
        for elt in measure_point:
            if not elt.tag == 'meetdata':
                e_data[elt.tag] = elt.text
            elif elt.attrib['klasse_id'] == '2':
                for measure_data in elt:
                    e_data[measure_data.tag] = measure_data.text
        data[unique_id] = e_data

    return data


def get_measure_points_data():
    """
    Gets all data from measure points
    :return: dictionary with keys measure points and their attributes in a dict
    """
    measure_point_data_url = 'http://miv.opendata.belfla.be/miv/configuratie/xml'
    try:
        measure_point_xml = urllib.request.urlopen(measure_point_data_url)
    except urllib.error.URLError as e:
        print('[*] Error: downloading measure points data failed with reason: ', e.reason)
        sys.exit(1)
    print('[*] Info: fetching measure point data appeared to be succesfull.')
    measure_point_root = etree.parse(measure_point_xml).getroot()

    measure_point_data = {}

    for mp in measure_point_root.iter('meetpunt'):
        unique_id = int(mp.attrib['unieke_id'])
        e_data = {}
        for child in mp:
            e_data[child.tag] = child.text
        measure_point_data[int(unique_id)] = e_data

    return measure_point_data


def clean_data(raw_data):
    """
    Takes in raw_data with useless values and wrong type in dutch. Outputs translated clean dictionary.
    :param raw_data: python dictionary with dutch keynames and wrong types
    :return: the data in python dict with english translated data in correct type
    """
    cleaned_data = {}

    for key, key_data in raw_data.items():
        working = False
        if not key_data['defect'] \
                and key_data['beschikbaar'] <= 1 \
                and key_data['geldig'] <=1:
            working = True
        speed = int(key_data['voertuigsnelheid_rekenkundig'])
        cleaned_data[key] = {
            'speed': speed,
            'working': working
        }

    return cleaned_data


def combine_data_measure_point(data, measure_point_data):
    """
    combines two datasets using the id's
    :param data: clean data about
    :param measure_point_data: uncleaned measure point data
    :return: combined clean dict, ready to be converted to JSON
    """
    to_delete_keys = [] # keep track of everything to delete
    for key, key_data in data.items():
        try:
            key_data['longitude'] = float(measure_point_data[key]['lengtegraad_EPSG_4326'].replace(',', '.'))
            key_data['latitude'] = float(measure_point_data[key]['breedtegraad_EPSG_4326'].replace(',', '.'))
            key_data['location'] = measure_point_data[key]['volledige_naam']
            key_data['lane'] = measure_point_data[key]['Rijstrook']
        except KeyError:
            to_delete_keys.append(key)
    for key in to_delete_keys:
        del data[key]
    return data


def process_data(data):
    """
    Add metadata and write to .json file

    :param data: python dict with clean data scraped from API
    """
    final_data = {
        "time": get_time_json(),
        "measure_points": data
    }

    basedir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(basedir, 'most_recent_data.json'), 'w') as f:
        json.dump(final_data, f)

    old_data_dir = os.path.join(basedir, 'old_data')
    # Create directory if it doesn't exist
    if not os.path.exists(old_data_dir):
        os.makedirs(old_data_dir)
    with open(os.path.join(old_data_dir, '{}.json'.format(get_time_json())), 'w') as f:
        json.dump(final_data, f)


def main():
    raw_data = get_data()
    data = clean_data(raw_data)
    measure_data = get_measure_points_data()
    combined_data = combine_data_measure_point(data, measure_data)
    process_data(combined_data)
    print("[*] Info: program appeared to ran succesfully.")


if __name__ == '__main__':
    main()
