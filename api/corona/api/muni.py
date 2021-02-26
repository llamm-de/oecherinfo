
from flask_restful import Resource, abort, request

from corona.config import ALLOWED_MUNI_FIELDS, API_TO_MUNI_DATABASE_MAPPING
from corona.db import mongo


class Municipality(Resource):
    """return data for a municipality
    """

    def get(self, muni):
        """return data

        the following filters are allowed:

        `fields`: can be a list of fields to return. Will return all the fields if not specified
        `format`: can be `json`, `csv`, defaults to `json`

        """

        # check which fields we should return
        fields = [f.strip() for f in request.args.get('fields', '').split(",")]
        if fields == ['']:
            fields = ALLOWED_MUNI_FIELDS
        else:
            if not set(fields).issubset(set(ALLOWED_MUNI_FIELDS)):
                abort(400, message="wrong list of fields")

        # check if fields are ok
        output = request.args.get('format', 'json').lower().strip()
        if output not in ['json', 'csv']:
            abort(400, message="wrong output format, should be 'json' or 'csv'")

        # get the general header information with trends etc.

        data = list(mongo.db.data.find(
            {'municipality': muni}).sort("date", -1))
        first = data[0]
        resp = {
            'date': first['date'],
            'dateFormatted': first['date'].strftime("%d. %B %Y"),
            'fields': fields,
            'format': output,
            'dates': list(reversed([d['date'] for d in data]))
        }        
    
        today={}
        yesterday={}
        trend={}
        for f in fields:
            db_field = API_TO_MUNI_DATABASE_MAPPING[f]
            if data[0][db_field]:
                today[f] = round(data[0][db_field],0 if f=='rollingRate' else 2)
            else:
                today[f] = None
            if data[1][db_field]:
                yesterday[f] = round(data[1][db_field],0 if f=='rollingRate' else 2)
            else:
                yesterday[f] = None

            # add the series to the response
            if f == "rollingRate":
                series = resp[f] = [round(d[db_field] or 0,0) for d in data]
            else:
                series = resp[f] = [round(d[db_field] or 0,2) for d in data]
            resp[f].reverse()

            # compute the trends
            if f=="rollingRate":
                diff = trend['rollingRate7DayChange'] = round(data[0]['incidence'] - data[7]['incidence'],2)
                trend['rollingRate7DayChangePercent'] = round(diff / data[7]['incidence'],2)
            else:
                diff = trend['%s7DayChange' %f] = sum(series[0:7]) - sum(series[8:14])
                trend['%s7DayChangePercent' %f] = round(diff / max(sum(series[8:14]),0.0001),2)
                
        resp['today'] = today
        resp['yesterday'] = yesterday
        resp['trend'] = trend
        
        return resp
