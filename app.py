# import config
import flask
from flask import Flask, request, render_template
import json
from transformers import pipeline
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# create the extension
db = SQLAlchemy()
# create the app
app = Flask(__name__)
# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///summarization.db"
# initialize the app with the extension
db.init_app(app)


class Summary(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    input = db.Column(db.String)
    summary = db.Column(db.String)
    model_name = db.Column(db.String)

with app.app_context():
    db.create_all()

small_summarizer = pipeline("summarization", model="lucadiliello/bart-small")
large_summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def bart_summarize(input_text, model):
    input_text = str(input_text)
    input_text = ' '.join(input_text.split())

    if model == "bart_small":
        return small_summarizer(input_text, max_length=130, min_length=30, do_sample=False)[0]["summary_text"]
    
    if model == "bart_large":
        return large_summarizer(input_text, max_length=130, min_length=30, do_sample=False)[0]["summary_text"]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    try:
        sentence = request.json['input_text']                 
        model = request.json['model']
        if sentence != '':  
            if Summary.query.filter_by(input=sentence, model_name=model).first():                
                output = Summary.query.filter_by(input=sentence, model_name=model).first().summary
            else:
                output = bart_summarize(sentence, model)  
                user = Summary(
                    input=sentence,
                    summary=str(output),
                    model_name=str(model)
                )

                db.session.add(user)
                db.session.commit()  

            response = {}          
            response['response'] = {
                'summary': str(output),
                'model': model.lower()
            }

            return flask.jsonify(response)
        else:
            res = dict({'message': 'Empty input'})
            return app.response_class(response=json.dumps(res), status=500, mimetype='application/json')
    except Exception as ex:
        res = dict({'message': str(ex)})
        return app.response_class(response=json.dumps(res), status=500, mimetype='application/json')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8000, use_reloader=False)
