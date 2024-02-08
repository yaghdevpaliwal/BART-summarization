# import config
import flask
from flask import Flask, request, render_template
import json, os
from transformers import pipeline
from flask import Flask, Response
from flask_sqlalchemy import SQLAlchemy
from flask import send_file

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

class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    input = db.Column(db.String)
    summary = db.Column(db.String)


with app.app_context():
    db.create_all()

small_summarizer = pipeline("summarization", model="lucadiliello/bart-small")
large_summarizer = pipeline("summarization", model="facebook/bart-large-cnn")


def bart_summarize(input_text, model, chunk_size=1000):
    input_text = str(input_text)
    input_text = ' '.join(input_text.split())

    # Split the input text into chunks
    chunks = [input_text[i:i + chunk_size] for i in range(0, len(input_text), chunk_size)]

    # Summarize each chunk and collect the summaries
    summaries = []
    for chunk in chunks:
        if model == "bart_small":
            summary =  small_summarizer(chunk, max_length=130, min_length=30, do_sample=False)[0]["summary_text"]
        if model == "bart_large":
            summary = large_summarizer(chunk, max_length=130, min_length=30, do_sample=False)[0]["summary_text"]
        summaries.append(summary)

    # Combine the summaries into a single summary
    combined_summary = " ".join(summaries)
    return combined_summary


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dataset_download')
def dataset_download():     
    datasets = Dataset.query.all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Input', 'Summary'])
    for dataset in datasets:
        writer.writerow([dataset.input, dataset.summary])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition":
                "attachment; filename=dataset.csv"})
      
    
import csv
from io import StringIO
import pandas as pd

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file and file.filename.endswith('.csv'):
        try:
            # Read CSV file using pandas
            df = pd.read_csv(file)
            for index, row in df.iterrows():
                input_text = row['Input']
                if not Dataset.query.filter_by(input=input_text).first():   
                    try:
                        summary = bart_summarize(input_text, 'bart_large')
                    except Exception as e:
                        summary = "Unable to parse text: "         
                    data = Dataset(input=input_text, summary=summary)
                    db.session.add(data)
            db.session.commit()
            return 'File uploaded and data saved successfully'
        except Exception as e:
            db.session.rollback()
            return 'Invalid file format: ' + str(e), 400
    else:
        return 'Invalid file format', 400
    

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
