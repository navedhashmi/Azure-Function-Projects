import datetime
import logging
from jinja2 import Template
from email.message import EmailMessage
import requests, smtplib
import azure.functions as func
import os
from dotenv import load_dotenv
from email_validator import validate_email, EmailNotValidError

# Get environment variables from .env file
load_dotenv() # Load the .env file
api_key = os.getenv('API_KEY')
email = os.getenv('EMAIL')
passw = os.getenv('PASSWORD')


# Function to parse the json data and convert it to a list of dictionaries to further use in email templating
def json_parsing(json_data):
    news_data_list = []
    for i in json_data['articles']:
        email_data = {}
        email_data.update({'title' : i['title']})
        email_data.update({'url' : i['url']})
        email_data.update({'urlToImage' : i['urlToImage']})
        news_data_list.append(email_data)
    return news_data_list

# Function to template the html email
def html_templating(data_list):
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="ie=edge">
        <title>News Time</title>
        <style>
            table, th, td {
                border: 1px solid black;
                border-collapse: collapse;
            }
            th, td {
                padding: 5px;
                text-align: left;
            }
        </style>
    </head>
    <body>
        <h1>News Time</h1>
        <table>
            <tr>
                <th>Title</th>
                <th>URL</th>
                <th>Image</th>
            </tr>
            {% for i in data_list %}
            <tr>
                <td>{{ i.title }}</td>
                <td><a href="{{ i.url }}">{{ i.url }}</a></td>
                <td><img src="{{ i.urlToImage }}" alt="{{ i.title }}"></td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    html_template_object = Template(html_template)
    html_message = html_template_object.render(data_list=data_list)
    return html_message

# Function to get the news data from the API and send it to parse the json data & return a list of dictionaries
def get_news_data():
    url = f'https://newsapi.org/v2/top-headlines?country=in&apiKey={api_key}'
    try: # Try catch block to handle the error if the API is not working
        response = requests.get(url)
    except requests.exceptions.RequestException as errMsg:
        print(errMsg)
        return None

    news_data_json = response.json()

    try: # Try catch block to handle the error if the API is changed to return a different format than expected
        news_data = json_parsing(json_data=news_data_json)
    except KeyError as errMsg:
        print(errMsg)
        return None
    return news_data

# Function to format the email
def email_format(reciever_email: str, message: str):
    msg = EmailMessage()
    msg['Subject'] = 'News Time'
    msg['From'] = email
    try: # Try catch block to handle the error if the reciever email is not valid
        msg['To'] = validate_email(reciever_email).email
    except EmailNotValidError as errMsg:
        print(errMsg)
        return None
    msg.set_content(message, subtype='html')
    return msg


# Function to send & setup the email | GEt the Message object from email format and send it to the SMTP server
def send_mail(message_object):
    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(email, passw)
        smtp.send_message(message_object)

# Main Time Triggered Azure Function to get the news data and send the email
def main(mytimer: func.TimerRequest) -> None:
    news_data = get_news_data()
    if news_data == None: # If there is any problem with the API or Json Parsing, return None
        logging.info('No data found as news data is not available because of above reason')
        return None

    html_message = html_templating(data_list=news_data)

    message_to_send = email_format(reciever_email="navedhashmi33@gmail.com", message=html_message)
    if message_to_send == None: # If there is any problem with the reciever email, return None
        logging.info('No data found as message is not available because of above reason')
        return None

    send_mail(message_to_send)
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()
    logging.info('Python timer trigger function ran at %s', utc_timestamp)
