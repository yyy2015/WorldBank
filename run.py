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
    'creation_time': fields.DateTime(dt_format='ISO 8601'),
    'indicator': {
        'id': fields.String,
        'value': fields.String
    }
})


@api.route('/collections')
class IndicatorCollectionController(Resource):
    def get(self):
        return {'hello': 'world'}

    def post(self):
        args = id_parser.parse_args()
        indicator_id = request.form['indicator_id']
        url = "http://api.worldbank.org/v2/countries/all/indicators/" + indicator_id + "?date=2012:2017&format=json"
        response = requests.get(url)

        data = response.json()
        ic = IndicatorCollection()
        print(data[1][0])
        ic.indicator = data[1][0].indicator.id
        ic.indicator_value = data[1][0].indicator.value

        for item in data[1]:
            entry = Entry()
            entry.country = item.country.value
            entry.date = item.date
            entry.value = item.value
            ic.entries.append(entry)

        return ic.save()


if __name__ == '__main__':
    app.run(debug=True)
