#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

from flask import render_template, request
from flask_compress import Compress
from datetime import datetime
from s2sphere import LatLng

from pogom.app import Pogom

from .models import Pokemon

log = logging.getLogger(__name__)
compress = Compress()


class MyPogom(Pogom):
    def __init__(self, import_name, **kwargs):
        super(MyPogom, self).__init__(import_name, **kwargs)
        self.route("/mobile2", methods=['GET'])(self.my_list_pokemon)
        self.route("/home_mode", methods=['GET'])(self.home_mode)
        self.route("/my_locations", methods=['GET'])(self.get_saved_locations)
        self.ignore_list = []
        self.location_list = []

    def get_saved_locations(self):
        formatted_list = []
        for location in self.location_list:
            entry = {'latitude': location.split(',')[0], 'longitude': location.split(',')[1],
                     'name': location.split(',')[2]}
            formatted_list.append(entry)
        return render_template('locations.html', locations=formatted_list)

    def set_my_params(self, ignore_list, location_list):
        self.ignore_list = ignore_list
        self.location_list = location_list

    def home_mode(self):
        return render_template('home_mode.html')

    def my_list_pokemon(self):
        # todo: check if client is android/iOS/Desktop for geolink, currently
        # only supports android
        pokemon_list = []
        pokemon_list_low = []
        max_distance = 500

        # Allow client to specify location
        lat = request.args.get('lat', self.current_location[0], type=float)
        lon = request.args.get('lon', self.current_location[1], type=float)
        origin_point = LatLng.from_degrees(lat, lon)

        # settings for 'home_mode'
        auto_reload = request.args.get('auto_reload', False, type=bool)
        home_mode = request.args.get('home_mode', False, type=bool)

        for pokemon in Pokemon.get_active(None, None, None, None):
            pokemon_point = LatLng.from_degrees(pokemon['latitude'],
                                                pokemon['longitude'])
            diff = pokemon_point - origin_point
            diff_lat = diff.lat().degrees
            diff_lng = diff.lng().degrees
            direction = (('N' if diff_lat >= 0 else 'S')
                         if abs(diff_lat) > 1e-3 else '') + \
                        (('E' if diff_lng >= 0 else 'W')
                         if abs(diff_lng) > 1e-3 else '')
            if direction is '':
                direction = (('N' if diff_lat >= 0 else 'S')
                             if abs(diff_lat) > 1e-4 else '') + \
                            (('E' if diff_lng >= 0 else 'W')
                             if abs(diff_lng) > 1e-4 else '')
            entry = {
                'id': pokemon['pokemon_id'],
                'name': pokemon['pokemon_name'],
                'card_dir': direction,
                'distance': int(origin_point.get_distance(
                    pokemon_point).radians * 6366468.241830914),
                'time_to_disappear': (
                    '%02dm %02ds' % (divmod((pokemon['disappear_time'] - datetime.utcnow()).seconds, 60))).replace(
                    '00m ', ''),
                'disappear_time': pokemon['disappear_time'],
                'disappear_sec': (pokemon['disappear_time'] - datetime.utcnow()).seconds,
                'latitude': pokemon['latitude'],
                'longitude': pokemon['longitude']
            }
            if entry['id'] in self.ignore_list:
                pokemon_list_low.append(entry)
            else:
                pokemon_list.append(entry)
        if home_mode:
            pokemon_list = sorted(pokemon_list, key=lambda x: x['disappear_time'], reverse=True)
            pokemon_list_low = sorted(pokemon_list_low, key=lambda x: x['distance'])
        else:
            pokemon_list = sorted(pokemon_list, key=lambda x: x['distance'])
            pokemon_list_low = sorted(pokemon_list_low, key=lambda x: x['distance'])

        return render_template('mobile_list2.html',
                               pokemon_list=pokemon_list,
                               pokemon_list_low=pokemon_list_low,
                               auto_reload=auto_reload,
                               home_mode=home_mode,
                               max_distance=max_distance,
                               origin_lat=lat,
                               origin_lng=lon)
