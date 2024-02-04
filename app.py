# import config
import flask
from flask import Flask, request, render_template
import json
from transformers import pipeline

BART_PATH = 'bart-large'

app = Flask(__name__)

summarizer = pipeline("summarization", model="lucadiliello/bart-small")

def bart_summarize(input_text):
    input_text = str(input_text)
    input_text = ' '.join(input_text.split())
    
    return summarizer(input_text, max_length=130, min_length=30, do_sample=False)[0]["summary_text"]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    try:
        sentence = request.json['input_text']
                 
        model = request.json['model']
        if sentence != '':            
            output = bart_summarize(sentence)            
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
