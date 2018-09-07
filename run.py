from flask import Flask
from flask_restplus import Resource, Api
from flask_mongoengine import MongoEngine


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


class Indicator(db.Document):
    meta = {
        'collection': 'todo',
        'ordering': ['-create_at'],
        'strict': False,
    }

    task = db.StringField()
    is_completed = db.BooleanField(default=False)

    def to_dict(self):
        return {
            'id': str(self.id),
            'task': self.task,
            'create_at': self.create_at.strftime("%Y-%m-%d %H:%M:%S"),
            'is_completed': self.is_completed
        }


@api.route('/hello')
class HelloWorld(Resource):
    def get(self):
        devices = Indicator.objects().all()
        if not devices:
            return "<p>No todos exist! <a href='/addtodo'>Add todo first.</a></p>"
        return {'hello': 'world'}

    def post(self):
        todo1 = Indicator(task='task 1', is_completed=False)
        todo2 = Indicator(task='task 2', is_completed=False)
        todo3 = Indicator(task='task 3', is_completed=False)
        todo1.save()
        todo2.save()
        todo3.save()
        return "<p>add succssfully! <a href='/'>Home</a></p>"


if __name__ == '__main__':
    app.run(debug=True)
