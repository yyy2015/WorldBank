from flask import Flask, request, jsonify
from flask_restplus import Resource, Api, reqparse, fields
from flask_mongoengine import MongoEngine
from datetime import datetime
import requests
import heapq

app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {
    'db': 'world-bank',
    'host': 'ds149252.mlab.com',
    'port': 49252,
    'username': 'world',
    'password': '1234qwer'
}
db = MongoEngine(app)
api = Api(app)


class Entry(db.Document):
    country = db.StringField()
    date = db.StringField()
    value = db.DecimalField()


class IndicatorCollection(db.Document):
    meta = {
        'collection': 'indicator_collection',
        'ordering': ['-create_at'],
        'strict': False,
    }

    collection_id = db.SequenceField()
    indicator = db.StringField()
    indicator_value = db.StringField()
    creation_time = db.DateTimeField(default=datetime.now)
    entries = db.ListField(db.EmbeddedDocumentField('Entry'))

    def to_dict(self):
        return {
            'id': str(self.id),
            'task': self.task,
            'create_at': self.create_at.strftime("%Y-%m-%d %H:%M:%S"),
            'is_completed': self.is_completed
        }


id_parser = reqparse.RequestParser()
id_parser.add_argument('indicator_id', type=str, required=True, help='Indicator id')
query_parser = reqparse.RequestParser()
query_parser.add_argument('query', type=str, required=True, help='Query condition')



@api.route('/collections')
class CollectionImportController(Resource):
    # get collection list
    def get(self):
        collection_list = IndicatorCollection.objects().all()
        collections = []
        for item in collection_list:
            collection = {
                'location': '/collections/' + str(item.collection_id),
                'collection_id': item.collection_id,
                'creation_time': item.creation_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'indicator': item.indicator
            }
            collections.append(collection)

        return jsonify(collections)

    # import collection with indicator_id
    def post(self):
        args = id_parser.parse_args()
        indicator_id = request.form['indicator_id']
        # return
        return_obj = {}
        status = 201

        # if exist
        exist = IndicatorCollection.objects(indicator=indicator_id).first()
        if exist:
            return_obj = exist
            status = 200
        else:
            temp_url = "http://api.worldbank.org/v2/countries/all/indicators/" + indicator_id + "?date=2012:2017&format=json"
            temp_res = requests.get(temp_url)
            # judge if the indicator_id illegal
            if temp_res.status_code != requests.codes.ok or len(temp_res.json()) < 2:
                temp_response = jsonify({"message": "The input indicator id doesn't exist."})
                temp_response.status_code = 400
                return temp_response
            # get total data size
            total = temp_res.json()[0]['total']

            # get all data related with indicator_id
            url = "http://api.worldbank.org/v2/countries/all/indicators/" + indicator_id + "?date=2012:2017&format=json&per_page="+str(total)
            response = requests.get(url)
            data = response.json()

            ic = IndicatorCollection()
            ic.indicator = data[1][0]['indicator']['id']
            ic.indicator_value = data[1][0]['indicator']['value']

            for item in data[1]:
                entry = Entry()
                entry.country = item['country']['value']
                entry.date = item['date']
                entry.value = item['value']
                ic.entries.append(entry)

            return_obj = ic.save()

        result = {
            'location': '/collections/'+str(return_obj.collection_id),
            'collection_id': return_obj.collection_id,
            'creation_time': return_obj.creation_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'indicator': return_obj.indicator_value
        }
        response = jsonify(result)
        response.status_code = status
        return response


@api.route('/collections/<int:collection_id>')
class CollectionDeleteController(Resource):
    # get collection by indicator_id
    def get(self, collection_id):
        collection = IndicatorCollection.objects(collection_id=collection_id).first()
        if collection:
            ic = {
                'collection_id': collection.collection_id,
                'indicator': collection.indicator,
                'indicator_value': collection.indicator_value,
                'creation_time': collection.creation_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'entries': collection.entries
            }
            return jsonify(ic)
        else:
            return {'error':'the collection not exist'}, 400

    # delete collection by indicator_id
    def delete(self, collection_id):
        # if exist
        exist = IndicatorCollection.objects(collection_id=collection_id).first()
        if not exist:
            return jsonify({"message": "The collection doesn't exist!"})
        exist.delete()
        return jsonify({"message": "Collection = " + str(collection_id) + " is removed from the database!"})


@api.route('/collections/<string:collection_id>/<string:year>/<string:country>')
class RetrieveIndicatorCountryAndYear(Resource):
    # get indicator value with collection_id,year and country
    def get(self,collection_id,year,country):

        collection = IndicatorCollection.objects(collection_id=collection_id).first()
        if collection:
            for item in collection.entries:
                if item['country'] == country and item['date'] == str(year):
                    result = {
                        'collection_id':collection.collection_id,
                        'indicator':collection.indicator,
                        'country':country,
                        'year':year,
                        'value':str(item['value'])
                    }
                    return jsonify(result)

        return {'error':'no such data'}, 400


@api.route('/collections/<string:collection_id>/<string:year>')
class IndicatorQueryController(Resource):

    def get(self, collection_id, year):
        # get query param
        args = query_parser.parse_args()
        query = request.args['query']
        type = 0
        num = 10
        if query.startswith('top'):
            type = 1
            num = query[3:]
        elif query.startswith('bottom'):
            type = 2
            num = query[6:]
        else:
            return {"message": "Wrong query param!"}
        try:
            num = int(num)
        except ValueError:
            return {"message": "Wrong query param!"}
        collection = IndicatorCollection.objects.filter(collection_id=collection_id).first()
        compare_list = []
        for item in collection.entries:
            if item.date == year and item.value is not None:
                compare_list.append(item)
        if type == 1:
            entries = heapq.nlargest(num, compare_list, key=lambda s: s['value'])
        else:
            entries = heapq.nsmallest(num, compare_list, key=lambda s: s['value'])

        return jsonify({
            "indicator": collection.indicator,
            "indicator_value": collection.indicator_value,
            "entries": entries
        })


if __name__ == '__main__':
    app.run(debug=True)
