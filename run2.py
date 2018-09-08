from flask import Flask, request, jsonify
from flask_restplus import Resource, Api, reqparse, fields
from flask_mongoengine import MongoEngine
from datetime import datetime
import requests

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

collection_model = api.model('Model', {
    'location': fields.String,
    'collection_id': fields.String,
    'creation_time': fields.DateTime,
    'indicator': fields.String
})


@api.route('/collections')
class CollectionListController(Resource):
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


@api.route('/collections/<string:collection_id>')
class CollectionItemController(Resource):
    def get(self, collection_id):
        collection = IndicatorCollection.objects(collection_id=collection_id).first()
        ic = trans_collection(collection)
        return jsonify(ic)


@api.route('/collections/<string:collection_id>/<string:year>/<string:country>')
class RetrieveIndicatorCountryAndYear(Resource):
    def get(self,collection_id,year,country):

        entry = Entry()
        entry.date = year
        entry.country = country

        collection = IndicatorCollection.objects(collection_id=collection_id,entries=[entry]).first()
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

def trans_collection(collection):
    ic = {
        'collection_id':collection.collection_id,
        'indicator':collection.indicator,
        'indicator_value':collection.indicator_value,
        'creation_time':collection.creation_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        'entries':collection.entries
    }
    return ic


if __name__ == '__main__':
    app.run(debug=True)
